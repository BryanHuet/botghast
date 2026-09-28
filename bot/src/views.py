"""
Presentation layer: builds what is shown on Discord (texts and embeds).

Wording and style come from data/messages.json through texts.py; this module only
assembles them. Commands should not build user-visible strings themselves.
"""

import discord

from texts import colour, get, style, t


def format_duration(seconds):
    """
    Format a duration in seconds as "m:ss" or "h:mm:ss".

    Args:
        seconds: Duration in seconds, or None

    Returns:
        str: Formatted duration, or None if unknown
    """
    if not seconds:
        return None
    hours, rest = divmod(int(seconds), 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02}:{secs:02}" if hours else f"{minutes}:{secs:02}"


def format_track_line(label, url=None, duration=None):
    """
    Format a track as a Markdown line for an embed: masked link and duration.

    Args:
        label: Track name
        url: Optional link to the track
        duration: Optional duration in seconds

    Returns:
        str: e.g. "[Title](https://...) `3:45`"
    """
    max_length = style('max_label_length')
    if len(label) > max_length:
        label = label[:max_length - 3] + '...'
    text = discord.utils.escape_markdown(label).replace('[', '\\[').replace(']', '\\]')
    if url:
        text = f"[{text}]({url})"
    duration_text = format_duration(duration)
    return f"{text} `{duration_text}`" if duration_text else text


def format_quote(quote):
    """
    Format a quote for Discord.

    Args:
        quote: {'citation', 'author'} dict

    Returns:
        str: e.g. "quote text ~ author name"
    """
    return t('common.quote', citation=quote['citation'], author=quote['author'])


def help_text():
    """
    Build the text of the aide command from the command list of messages.json.

    Returns:
        str
    """
    lines = [t('aide.title'), '']
    for command in get('aide.commands'):
        lines.append(t('aide.line', usage=command['usage'], description=command['description']))
    lines += ['', t('aide.footer')]
    return '\n'.join(lines)


def search_results_text(keyword, results):
    """
    Build the reply of the cherchecitation command.

    Args:
        keyword: Searched keyword
        results: Matching quotes (non-empty)

    Returns:
        str
    """
    shown = style('search_results')
    lines = [t('cherchecitation.header', keyword=keyword)]
    for i, quote in enumerate(results[:shown], 1):
        lines.append(t('cherchecitation.result', index=i, quote=format_quote(quote)))
    if len(results) > shown:
        lines.append(t('cherchecitation.more', count=len(results) - shown))
    return '\n'.join(lines)


def set_requester_footer(embed, requester, key='embeds.requested_by'):
    """
    Show who requested a track (or ran a command) in the footer of an embed, with their avatar.

    Args:
        embed: discord.Embed to update
        requester: discord.Member or discord.User, or None
        key: Text of messages.json used for the footer, with a {name} placeholder

    Returns:
        discord.Embed: The same embed
    """
    if requester is not None:
        embed.set_footer(text=t(key, name=requester.display_name),
                         icon_url=requester.display_avatar.url)
    return embed


def message_embed(text, error=False, author=None):
    """
    Build a short one-line music embed (skip, stop, playback error).

    Args:
        text: Message in French (Markdown allowed)
        error: Use the error color
        author: Optional discord.Member shown in the footer as the one who ran the command

    Returns:
        discord.Embed
    """
    embed = discord.Embed(description=text, colour=colour('error' if error else 'music'))
    return set_requester_footer(embed, author, key='embeds.done_by')


def now_playing_embed(track, queue):
    """
    Build the "now playing" embed of a track.

    Args:
        track: now_playing metadata dict (see youtube.extract_audio_info), with an optional 'requester'
        queue: Pending entries of the guild queue

    Returns:
        discord.Embed
    """
    embed = discord.Embed(title=track['title'][:256], url=track.get('url'), colour=colour('music'))
    embed.set_author(name=t('embeds.now_playing'))
    if track.get('thumbnail'):
        embed.set_thumbnail(url=track['thumbnail'])
    embed.add_field(name=t('embeds.duration'),
                    value=format_duration(track.get('duration')) or t('embeds.unknown_duration'))
    if track.get('uploader'):
        embed.add_field(name=t('embeds.channel'), value=discord.utils.escape_markdown(track['uploader'])[:1024])
    if queue:
        following = format_track_line(queue[0]['label'], queue[0].get('url'))
        if len(queue) > 1:
            following += '\n' + t('embeds.up_next_more', count=len(queue) - 1)
        embed.add_field(name=t('embeds.up_next'), value=following[:1024], inline=False)
    return set_requester_footer(embed, track.get('requester'))


def queued_embed(track, position):
    """
    Build the embed confirming that a track was added to the queue.

    Args:
        track: Queue entry, with the metadata of youtube.extract_audio_info
        position: Position of the track in the queue (1 = next)

    Returns:
        discord.Embed
    """
    embed = discord.Embed(title=track['label'][:256], url=track.get('url'), colour=colour('music'))
    embed.set_author(name=t('embeds.queued'))
    if track.get('thumbnail'):
        embed.set_thumbnail(url=track['thumbnail'])
    embed.add_field(name=t('embeds.duration'),
                    value=format_duration(track.get('duration')) or t('embeds.unknown_duration'))
    embed.add_field(name=t('embeds.position'), value=str(position))
    return set_requester_footer(embed, track.get('requester'))


def playlist_embed(playlist, tracks, source, requester, shuffled=False):
    """
    Build the embed confirming that a playlist was added to the queue.

    Args:
        playlist: {'name', 'url', 'thumbnail'} dict
        tracks: Queued entries of the playlist
        source: "YouTube" or "Spotify"
        requester: discord.Member who asked for the playlist
        shuffled: Whether the tracks were shuffled

    Returns:
        discord.Embed
    """
    key = 'embeds.playlist_tracks_shuffled' if shuffled else 'embeds.playlist_tracks'
    embed = discord.Embed(title=playlist['name'][:256], url=playlist.get('url'),
                          description=t(key, count=len(tracks)), colour=colour('music'))
    embed.set_author(name=t('embeds.playlist_added', source=source))
    if playlist.get('thumbnail'):
        embed.set_thumbnail(url=playlist['thumbnail'])
    total = format_duration(sum(track.get('duration') or 0 for track in tracks))
    if total:
        embed.add_field(name=t('embeds.total_duration'), value=total)
    return set_requester_footer(embed, requester)


def queue_embed(guild, current, queue):
    """
    Build the embed of the file command: current track and next entries.

    Args:
        guild: discord.Guild
        current: now_playing metadata dict, or None
        queue: Pending entries of the guild queue

    Returns:
        discord.Embed
    """
    embed = discord.Embed(title=t('embeds.queue_title'), colour=colour('music'))
    if guild.icon:
        embed.set_author(name=guild.name, icon_url=guild.icon.url)
    if current:
        embed.add_field(name=t('embeds.queue_current'),
                        value=format_track_line(current['title'], current.get('url'), current.get('duration')),
                        inline=False)
        if current.get('thumbnail'):
            embed.set_thumbnail(url=current['thumbnail'])

    if queue:
        preview_size = style('queue_preview_size')
        lines = [t('embeds.queue_line', index=i,
                   track=format_track_line(entry['label'], entry.get('url'), entry.get('duration')))
                 for i, entry in enumerate(list(queue)[:preview_size], 1)]
        if len(queue) > preview_size:
            lines.append(t('embeds.queue_more', count=len(queue) - preview_size))
        embed.description = t('embeds.queue_next_header') + '\n' + '\n'.join(lines)
    else:
        embed.description = t('embeds.queue_empty')

    total = format_duration(sum(entry.get('duration') or 0 for entry in queue))
    if total:
        embed.set_footer(text=t('embeds.queue_footer_duration', count=len(queue), duration=total))
    else:
        embed.set_footer(text=t('embeds.queue_footer', count=len(queue)))
    return embed
