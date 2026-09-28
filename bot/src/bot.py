"""
BotGhast - A Discord bot for sharing random GIFs and quotes, and playing music.

Commands:
- aide: Show the list of commands
- donneavis: Reply to a referenced message with a random GIF
- citation / cherchecitation: Send a random quote, or search quotes by keyword
- joue / viking / suivant / file / stop: Play YouTube videos or a Spotify playlist in a voice channel

This file only holds the commands. The rest lives in dedicated modules:
- config.py: environment variables and technical constants
- log.py: the 'botghast' logger
- texts.py + data/messages.json: every user-visible text and the style (colors, limits)
- views.py: builds the texts and embeds shown on Discord
- datastore.py: loading and validation of the GIFs and quotes files
- youtube.py / spotify_client.py: audio sources
- music.py: per-guild queues and voice playback
"""

import asyncio
import os
import random

import discord
import yt_dlp
from discord.ext import commands
from setproctitle import setproctitle

import music
import texts
from config import DISCORD_TOKEN, GIFS_FILE, MESSAGES_FILE, PREFIX, QUOTES_FILE, SPOTIFY_PLAYLIST
from datastore import load_gifs, load_quotes
from log import logger
from spotify_client import fetch_spotify_playlist, parse_spotify_playlist_id
from texts import t
from views import (format_quote, format_track_line, help_text, message_embed, now_playing_embed,
                   playlist_embed, queue_embed, queued_embed, search_results_text)
from youtube import extract_audio_info, is_youtube_playlist

setproctitle("BotGhast")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Log bot initialization
logger.info(f"BotGhast initializing with prefix: {PREFIX}")
logger.info(f"GIFs file path: {GIFS_FILE}")
logger.info(f"Quotes file path: {QUOTES_FILE}")
logger.info(f"Messages file path: {MESSAGES_FILE}")


def guild_name(ctx):
    """
    Name of the server a command was run on, safe in direct messages.

    Args:
        ctx: discord.ext.commands.Context object

    Returns:
        str: The server name, or "DM"
    """
    return ctx.guild.name if ctx.guild else "DM"


@bot.command()
async def donneavis(ctx):
    """
    Reply to a referenced message with a random GIF.

    This command requires a message reference (reply to another message).
    It will reply to the referenced message with a random GIF from the gifs.json file.

    Args:
        ctx: discord.ext.commands.Context object containing message information

    Returns:
        None

    Usage:
        Reply to any message with: ?donneavis
    """
    server = guild_name(ctx)
    logger.info(f"Command 'donneavis' invoked by {ctx.author} in channel {ctx.channel} on server {server}")

    if not os.path.exists(GIFS_FILE):
        logger.error(f"GIFs file not found: {GIFS_FILE}")
        await ctx.reply(t('donneavis.gifs_file_missing'))
        return

    if not ctx.message.reference:
        logger.warning(f"No message reference found in donneavis command from {ctx.author} on server {server}")
        await ctx.reply(t('donneavis.no_reference'))
        return

    try:
        logger.debug(f"Fetching referenced message: {ctx.message.reference.message_id}")
        referenced_message = await ctx.message.channel.fetch_message(ctx.message.reference.message_id)
        # Validate message exists and is accessible
        if not referenced_message:
            logger.warning(f"Referenced message not found or not accessible on server {server}")
            await ctx.reply(t('donneavis.reference_inaccessible'))
            return
    except discord.NotFound:
        logger.warning(f"Referenced message not found: {ctx.message.reference.message_id} on server {server}")
        await ctx.reply(t('donneavis.reference_not_found'))
        return
    except discord.Forbidden:
        logger.warning(f"Permission denied accessing message: {ctx.message.reference.message_id} on server {server}")
        await ctx.reply(t('donneavis.reference_forbidden'))
        return
    except Exception as e:
        logger.error(f"Error fetching referenced message: {e} on server {server}")
        await ctx.reply(t('donneavis.reference_error'))
        return

    try:
        gif = random.choice(load_gifs())
        logger.info(f"Selected GIF: {gif}")
        await referenced_message.reply(t('donneavis.response', gif=gif))
    except Exception as e:
        logger.error(f"Error in donneavis command: {e} on server {server}")
        await ctx.send(t('donneavis.error'))


@bot.command()
async def citation(ctx):
    """
    Send a random quote from the quotes collection.

    This command selects a random quote from the quotes.json file and sends it
    to the channel where the command was invoked.

    Args:
        ctx: discord.ext.commands.Context object containing message information

    Returns:
        None

    Usage:
        ?citation
    """
    server = guild_name(ctx)
    logger.info(f"Command 'citation' invoked by {ctx.author} in channel {ctx.channel} on server {server}")

    if not os.path.exists(QUOTES_FILE):
        logger.error(f"Quotes file not found: {QUOTES_FILE}")
        await ctx.reply(t('common.quotes_file_missing'))
        return

    if not ctx.channel.permissions_for(ctx.me).send_messages:
        logger.error(f"Bot does not have permission to send messages in this channel on server {server}")
        return

    try:
        quotes = load_quotes()
        if not quotes:
            logger.warning(f"No quotes available in the database on server {server}")
            await ctx.reply(t('common.no_quotes'))
            return

        quote = random.choice(quotes)
        logger.info(f"Selected quote: {quote['citation']} by {quote['author']}")
        await ctx.send(format_quote(quote))

    except ValueError as e:
        # Also catches json.JSONDecodeError
        logger.error(f"Invalid quotes file: {e}")
        await ctx.reply(t('citation.json_error'))
    except Exception as e:
        logger.error(f"Error in citation command: {e} on server {server}")
        await ctx.reply(t('citation.error'))


@bot.command(name='aide', help='Show available commands and usage')
async def help_command(ctx):
    """
    Display help information about available commands (list maintained in data/messages.json).

    Args:
        ctx: discord.ext.commands.Context object

    Returns:
        None

    Usage:
        ?aide
    """
    logger.info(f"Command 'aide' invoked by {ctx.author} in channel {ctx.channel} on server {guild_name(ctx)}")
    await ctx.send(help_text())


@bot.command(name='cherchecitation', help='Search quotes by keyword')
async def search_quote(ctx, *, keyword: str = None):
    """
    Search quotes by keyword in citation text or author name.

    Args:
        ctx: discord.ext.commands.Context object
        keyword: Search term to look for in quotes

    Returns:
        None

    Usage:
        ?cherchecitation <mot-clé>
    """
    server = guild_name(ctx)
    logger.info(f"Command 'cherchecitation' invoked by {ctx.author} with keyword: '{keyword}' on server {server}")

    if not keyword:
        logger.warning(f"Empty keyword provided in cherchecitation command on server {server}")
        await ctx.reply(t('cherchecitation.no_keyword'))
        return

    if not os.path.exists(QUOTES_FILE):
        logger.error("Quotes file not found during search")
        await ctx.reply(t('common.quotes_file_missing'))
        return

    try:
        quotes = load_quotes()
        if not quotes:
            logger.warning("No quotes available for search")
            await ctx.reply(t('common.no_quotes'))
            return

        # Search in both citation text and author
        keyword_lower = keyword.lower()
        results = [quote for quote in quotes
                   if keyword_lower in quote['citation'].lower() or keyword_lower in quote['author'].lower()]
        logger.info(f"Found {len(results)} results for keyword '{keyword}'")

        if not results:
            await ctx.reply(t('cherchecitation.no_result', keyword=keyword))
            return

        await ctx.send(search_results_text(keyword, results))

    except Exception as e:
        logger.error(f"Error in cherchecitation command: {e}")
        await ctx.reply(t('cherchecitation.error'))


@bot.event
async def on_voice_state_update(member, before, after):
    """
    Leave the voice channel when the bot is left alone in it (see music.watch_listeners).

    Args:
        member: discord.Member whose voice state changed
        before: discord.VoiceState before the change
        after: discord.VoiceState after the change

    Returns:
        None
    """
    music.watch_listeners(member.guild)


@bot.command(name='joue', help='Play a YouTube video audio in your voice channel')
async def play(ctx, *, url: str = None):
    """
    Play the audio of a YouTube video in the author's voice channel, or queue it.

    The bot joins (or moves to) the author's voice channel. If nothing is playing,
    the video starts right away; otherwise it is added at the end of the queue
    and played by music.play_next, like the tracks of a Spotify playlist.
    A URL with a "list" parameter queues every video of the playlist, in order.

    Args:
        ctx: discord.ext.commands.Context object
        url: YouTube video or playlist URL

    Returns:
        None

    Usage:
        ?joue https://www.youtube.com/watch?v=...
        ?joue https://www.youtube.com/playlist?list=...
    """
    server = guild_name(ctx)
    logger.info(f"Command 'joue' invoked by {ctx.author} in channel {ctx.channel} on server {server} with url: {url}")

    if not url:
        logger.warning(f"No URL provided in joue command on server {server}")
        await ctx.reply(t('joue.no_url'))
        return

    voice_client = await music.ensure_voice(ctx)
    if voice_client is None:
        return

    try:
        if is_youtube_playlist(url):
            async with ctx.typing():
                await music.queue_youtube_playlist(ctx, url)
            return

        async with ctx.typing():
            # Same lock as play_next, so two ?joue cannot both see the player idle
            async with music.get_lock(ctx.guild.id):
                queue = music.get_queue(ctx.guild.id)
                if not music.is_busy(voice_client):
                    track = await music.start_track(ctx.guild, voice_client,
                                                    {'query': url, 'label': url, 'requester': ctx.author})
                    await ctx.send(embed=now_playing_embed(track, queue))
                    return

                # Resolve now to reject invalid links and get a readable label;
                # the stream URL expires, so it is resolved again when played
                loop = asyncio.get_running_loop()
                _, meta = await loop.run_in_executor(None, extract_audio_info, url)
                entry = {'query': url, 'label': meta['title'], 'url': meta['url'], 'duration': meta['duration'],
                         'thumbnail': meta['thumbnail'], 'requester': ctx.author}
                queue.append(entry)
                logger.info(f"Queued '{meta['title']}' at position {len(queue)} on server {server}")

        await ctx.send(embed=queued_embed(entry, len(queue)))

    except yt_dlp.utils.DownloadError as e:
        logger.error(f"yt-dlp error in joue command: {e} on server {server}")
        await ctx.reply(t('joue.download_error'))
    except discord.ClientException as e:
        logger.error(f"Voice client error in joue command: {e} on server {server}")
        await ctx.reply(t('joue.client_error'))
    except Exception as e:
        logger.error(f"Error in joue command: {e} on server {server}")
        await ctx.reply(t('joue.error'))


@bot.command(name='viking', help='Play a Spotify playlist (default: Viking playlist)')
async def spotify(ctx, *, playlist: str = None):
    """
    Queue every track of a Spotify playlist and play them from YouTube.

    Track names are read with the Spotify Web API (only playlists owned by the
    authorized account return their tracks), then each track is searched on
    YouTube when its turn comes. Tracks are shuffled.

    Args:
        ctx: discord.ext.commands.Context object
        playlist: Optional playlist URL or ID, defaults to the SPOTIFY_PLAYLIST environment variable

    Returns:
        None

    Usage:
        ?viking
        ?viking https://open.spotify.com/playlist/...
    """
    server = guild_name(ctx)
    logger.info(f"Command 'viking' invoked by {ctx.author} in channel {ctx.channel} on server {server} "
                f"with playlist: {playlist}")

    playlist_id = parse_spotify_playlist_id(playlist or SPOTIFY_PLAYLIST or '')
    if not playlist_id:
        logger.warning(f"No valid Spotify playlist provided on server {server}")
        await ctx.reply(t('viking.no_playlist'))
        return

    voice_client = await music.ensure_voice(ctx)
    if voice_client is None:
        return

    try:
        async with ctx.typing():
            playlist, tracks = await fetch_spotify_playlist(playlist_id)
            if not tracks:
                logger.warning(f"Spotify playlist {playlist_id} returned no playable track on server {server}")
                await ctx.reply(t('viking.empty_playlist'))
                return

            random.shuffle(tracks)
            for track in tracks:
                track['requester'] = ctx.author
            queue = music.get_queue(ctx.guild.id)
            queue.clear()
            queue.extend(tracks)
            await ctx.send(embed=playlist_embed(playlist, tracks, "Spotify", ctx.author, shuffled=True))

            if music.is_busy(voice_client):
                # The after callback of the stopped track starts the queue
                voice_client.stop()
            else:
                await music.play_next(ctx.guild)

    except RuntimeError as e:
        logger.error(f"Spotify API error in viking command: {e} on server {server}")
        await ctx.reply(t('viking.api_error'))
    except Exception as e:
        logger.error(f"Error in viking command: {e} on server {server}")
        await ctx.reply(t('viking.error'))


@bot.command(name='suivant', help='Skip to the next track of the queue')
async def skip(ctx):
    """
    Skip the current track; the next one of the queue starts automatically.

    Args:
        ctx: discord.ext.commands.Context object

    Returns:
        None

    Usage:
        ?suivant
    """
    server = guild_name(ctx)
    logger.info(f"Command 'suivant' invoked by {ctx.author} in channel {ctx.channel} on server {server}")

    voice_client = ctx.voice_client if ctx.guild else None
    if voice_client is None or not music.is_busy(voice_client):
        logger.warning(f"Command 'suivant' used while nothing is playing on server {server}")
        await ctx.reply(t('suivant.nothing_playing'))
        return

    try:
        current = music.now_playing.get(ctx.guild.id)
        voice_client.stop()
        if current:
            text = t('suivant.skipped_track', track=format_track_line(current['title'], current.get('url')))
        else:
            text = t('suivant.skipped')
        if not music.get_queue(ctx.guild.id):
            text += '\n' + t('suivant.queue_empty')
        await ctx.send(embed=message_embed(text, author=ctx.author))
    except Exception as e:
        logger.error(f"Error in suivant command: {e} on server {server}")
        await ctx.reply(t('suivant.error'))


@bot.command(name='file', help='Show the current track and the next ones')
async def show_queue(ctx):
    """
    Show the track being played and the next entries of the queue.

    Args:
        ctx: discord.ext.commands.Context object

    Returns:
        None

    Usage:
        ?file
    """
    server = guild_name(ctx)
    logger.info(f"Command 'file' invoked by {ctx.author} in channel {ctx.channel} on server {server}")

    if not ctx.guild:
        await ctx.reply(t('common.server_only'))
        return

    try:
        queue = music.get_queue(ctx.guild.id)
        current = music.now_playing.get(ctx.guild.id)
        if not current and not queue:
            await ctx.send(embed=message_embed(t('file.empty')))
            return

        await ctx.send(embed=queue_embed(ctx.guild, current, queue))
    except Exception as e:
        logger.error(f"Error in file command: {e} on server {server}")
        await ctx.reply(t('file.error'))


@bot.command(name='stop', help='Stop playback and leave the voice channel')
async def stop(ctx):
    """
    Stop the current playback, clear the queue and disconnect from the voice channel.

    Args:
        ctx: discord.ext.commands.Context object

    Returns:
        None

    Usage:
        ?stop
    """
    server = guild_name(ctx)
    logger.info(f"Command 'stop' invoked by {ctx.author} in channel {ctx.channel} on server {server}")

    if not ctx.guild or ctx.voice_client is None:
        logger.warning(f"Command 'stop' used while not connected to voice on server {server}")
        await ctx.reply(t('stop.not_connected'))
        return

    try:
        music.clear_guild(ctx.guild.id)
        await ctx.voice_client.disconnect()
        logger.info(f"Disconnected from voice on server {server}")
        await ctx.send(embed=message_embed(t('stop.stopped'), author=ctx.author))
    except Exception as e:
        logger.error(f"Error in stop command: {e} on server {server}")
        await ctx.reply(t('stop.error'))


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN environment variable not set")
        raise ValueError("DISCORD_TOKEN environment variable is required")

    # Fail fast on a missing or invalid messages file rather than on the first command
    texts.load_messages()

    logger.info("Starting BotGhast...")
    logger.info(f"Using Discord token: {'*' * (len(DISCORD_TOKEN) - 4) + DISCORD_TOKEN[-4:]}")

    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Bot failed to start: {e}")
        raise
