"""
Music player: per-guild queues, playback with ffmpeg, voice connection and idle disconnection.
"""

import asyncio
import shutil
from collections import deque

import discord

from config import FFMPEG_OPTIONS, PLAYBACK_VOLUME, VOICE_IDLE_TIMEOUT
from log import logger
from texts import t
from views import format_track_line, message_embed, now_playing_embed, playlist_embed
from youtube import extract_audio_info, extract_youtube_playlist

# Per-guild music state, keyed by guild ID
music_queues = {}    # deque of {'query', 'label', 'url', 'duration', 'requester'} entries waiting to be played
music_channels = {}  # text channel where "now playing" messages are sent
music_locks = {}     # asyncio.Lock serializing play_next
now_playing = {}     # metadata dict of the track being played (see youtube.extract_audio_info)
idle_disconnects = {}  # asyncio.Task waiting to leave a voice channel left without listeners


def get_queue(guild_id):
    """
    Get (and create if needed) the music queue of a guild.

    Args:
        guild_id: Discord guild ID

    Returns:
        collections.deque: Pending {'query', 'label'} entries
    """
    return music_queues.setdefault(guild_id, deque())


def get_lock(guild_id):
    """
    Get (and create if needed) the lock serializing track starts in a guild.

    Args:
        guild_id: Discord guild ID

    Returns:
        asyncio.Lock
    """
    return music_locks.setdefault(guild_id, asyncio.Lock())


def is_busy(voice_client):
    """
    Tell whether a voice client is playing or paused.

    Args:
        voice_client: discord.VoiceClient

    Returns:
        bool
    """
    return voice_client.is_playing() or voice_client.is_paused()


def clear_guild(guild_id):
    """
    Empty the queue and forget the current track of a guild.

    Args:
        guild_id: Discord guild ID

    Returns:
        None
    """
    get_queue(guild_id).clear()
    now_playing.pop(guild_id, None)


async def start_track(guild, voice_client, entry):
    """
    Resolve a queue entry with yt-dlp and start playing it.

    When the track ends, the next entry of the guild queue is played automatically.

    Args:
        guild: discord.Guild being played in
        voice_client: Connected discord.VoiceClient
        entry: Queue entry ({'query', 'label'} plus optional 'requester')

    Returns:
        dict: now_playing metadata of the track (see youtube.extract_audio_info), with its 'requester'
    """
    loop = asyncio.get_running_loop()
    stream_url, meta = await loop.run_in_executor(None, extract_audio_info, entry['query'])
    meta['requester'] = entry.get('requester')
    title = meta['title']

    def after_playing(error):
        if error:
            logger.error(f"Playback error on server {guild.name}: {error}")
        else:
            logger.info(f"Finished playing '{title}' on server {guild.name}")
        # Called from the audio thread: hand over to the bot event loop
        asyncio.run_coroutine_threadsafe(play_next(guild), loop)

    source = discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTIONS)
    voice_client.play(discord.PCMVolumeTransformer(source, volume=PLAYBACK_VOLUME), after=after_playing)
    now_playing[guild.id] = meta
    logger.info(f"Now playing '{title}' on server {guild.name}")
    return meta


async def play_next(guild):
    """
    Play the next entry of the guild queue, skipping entries that cannot be resolved.

    Args:
        guild: discord.Guild

    Returns:
        None
    """
    voice_client = guild.voice_client
    if voice_client is None or not voice_client.is_connected():
        music_queues.pop(guild.id, None)
        now_playing.pop(guild.id, None)
        return
    # A new track may already have been started by a command (e.g. ?joue)
    if is_busy(voice_client):
        return

    async with get_lock(guild.id):
        await _play_next_locked(guild, voice_client)


async def _play_next_locked(guild, voice_client):
    """
    Body of play_next, run while holding the guild music lock.

    Args:
        guild: discord.Guild
        voice_client: Connected discord.VoiceClient

    Returns:
        None
    """
    if is_busy(voice_client):
        return

    queue = get_queue(guild.id)
    channel = music_channels.get(guild.id)
    while queue:
        entry = queue.popleft()
        try:
            track = await start_track(guild, voice_client, entry)
            if channel:
                await channel.send(embed=now_playing_embed(track, queue))
            return
        except Exception as e:
            logger.error(f"Could not play '{entry['label']}' on server {guild.name}: {e}")
            if channel:
                line = format_track_line(entry['label'], entry.get('url'))
                await channel.send(embed=message_embed(t('voice.track_error', track=line), error=True))

    now_playing.pop(guild.id, None)
    logger.info(f"Queue finished on server {guild.name}")


async def ensure_voice(ctx):
    """
    Run the common checks of music commands and connect to the author's voice channel.

    Replies to the author with a French message when a check fails.

    Args:
        ctx: discord.ext.commands.Context object

    Returns:
        discord.VoiceClient: The connected voice client, or None if a check failed
    """
    if not ctx.guild:
        logger.warning(f"Command '{ctx.command}' used outside of a server")
        await ctx.reply(t('common.server_only'))
        return None

    if not ctx.author.voice or not ctx.author.voice.channel:
        logger.warning(f"{ctx.author} is not in a voice channel on server {ctx.guild.name}")
        await ctx.reply(t('voice.not_in_voice'))
        return None

    if shutil.which('ffmpeg') is None:
        logger.error(f"ffmpeg executable not found in PATH on server {ctx.guild.name}")
        await ctx.reply(t('voice.no_ffmpeg'))
        return None

    channel = ctx.author.voice.channel
    try:
        voice_client = ctx.voice_client
        if voice_client is None:
            voice_client = await channel.connect()
        elif voice_client.channel != channel:
            await voice_client.move_to(channel)
    except discord.Forbidden:
        logger.error(f"Missing permission to join voice channel {channel} on server {ctx.guild.name}")
        await ctx.reply(t('voice.join_forbidden'))
        return None
    except Exception as e:
        logger.error(f"Could not join voice channel {channel} on server {ctx.guild.name}: {e}")
        await ctx.reply(t('voice.join_error'))
        return None

    music_channels[ctx.guild.id] = ctx.channel
    return voice_client


async def queue_youtube_playlist(ctx, url):
    """
    Add every video of a YouTube playlist at the end of the queue, and start it if idle.

    Args:
        ctx: discord.ext.commands.Context object
        url: YouTube URL with a "list" parameter

    Returns:
        None

    Raises:
        yt_dlp.utils.DownloadError: If the playlist cannot be read
    """
    loop = asyncio.get_running_loop()
    playlist, tracks = await loop.run_in_executor(None, extract_youtube_playlist, url)
    if not tracks:
        logger.warning(f"YouTube playlist {url} returned no playable video on server {ctx.guild.name}")
        await ctx.reply(t('joue.empty_playlist'))
        return

    for track in tracks:
        track['requester'] = ctx.author
    get_queue(ctx.guild.id).extend(tracks)
    await ctx.send(embed=playlist_embed(playlist, tracks, "YouTube", ctx.author))
    # No-op if a track is already playing: the playlist follows the current queue
    await play_next(ctx.guild)


def has_listeners(voice_channel):
    """
    Tell whether a voice channel contains at least one human member.

    Args:
        voice_channel: discord.VoiceChannel or discord.StageChannel

    Returns:
        bool: True if a non-bot member is connected to the channel
    """
    return any(not member.bot for member in voice_channel.members)


async def disconnect_if_alone(guild):
    """
    Wait VOICE_IDLE_TIMEOUT seconds, then leave the voice channel if still no human is in it.

    Clears the queue like the stop command and warns the music text channel.

    Args:
        guild: discord.Guild

    Returns:
        None
    """
    try:
        await asyncio.sleep(VOICE_IDLE_TIMEOUT)
        voice_client = guild.voice_client
        if voice_client is None or not voice_client.is_connected() or has_listeners(voice_client.channel):
            return

        clear_guild(guild.id)
        await voice_client.disconnect()
        logger.info(f"Left empty voice channel {voice_client.channel} on server {guild.name}")

        channel = music_channels.get(guild.id)
        if channel:
            await channel.send(embed=message_embed(t('voice.left_empty')))
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"Error while leaving empty voice channel on server {guild.name}: {e}")
    finally:
        if idle_disconnects.get(guild.id) is asyncio.current_task():
            idle_disconnects.pop(guild.id, None)


def watch_listeners(guild):
    """
    Schedule a disconnection when the bot is left alone in its voice channel,
    and cancel it when someone joins again.

    Args:
        guild: discord.Guild whose voice states changed

    Returns:
        None
    """
    voice_client = guild.voice_client
    if voice_client is None or voice_client.channel is None:
        return

    pending = idle_disconnects.get(guild.id)
    if has_listeners(voice_client.channel):
        if pending:
            pending.cancel()
            idle_disconnects.pop(guild.id, None)
            logger.info(f"Listener back in {voice_client.channel} on server {guild.name}, staying connected")
        return

    if pending is None:
        logger.info(f"No listener left in {voice_client.channel} on server {guild.name}, "
                    f"leaving in {VOICE_IDLE_TIMEOUT}s")
        idle_disconnects[guild.id] = asyncio.create_task(disconnect_if_alone(guild))
