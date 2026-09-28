"""
YouTube extraction with yt-dlp: audio stream of a video, and videos of a playlist.

The functions of this module are blocking and must be run in an executor.
"""

import re

import yt_dlp

from config import YOUTUBE_UNAVAILABLE_TITLES, YTDL_OPTIONS, YTDL_PLAYLIST_OPTIONS
from log import logger


def extract_audio_info(query):
    """
    Resolve a YouTube URL or search query to a direct audio stream URL with yt-dlp.

    This call is blocking and must be run in an executor.

    Args:
        query: YouTube video URL, or a yt-dlp search query (e.g. "ytsearch1:...")

    Returns:
        tuple: (stream_url, meta) where meta is a {'title', 'url', 'thumbnail', 'duration', 'uploader'} dict
    """
    with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
        info = ydl.extract_info(query, download=False)
    # Search queries return a playlist-like result: keep the first entry
    if 'entries' in info:
        if not info['entries']:
            raise yt_dlp.utils.DownloadError(f"No result for {query}")
        info = info['entries'][0]
    meta = {
        'title': info.get('title', query),
        'url': info.get('webpage_url'),
        'thumbnail': info.get('thumbnail'),
        'duration': info.get('duration'),
        'uploader': info.get('uploader') or info.get('channel'),
    }
    return info['url'], meta


def is_youtube_playlist(url):
    """
    Tell whether a URL points to a YouTube playlist (it has a "list" parameter).

    Args:
        url: URL given to the joue command

    Returns:
        bool: True for "...playlist?list=..." and "...watch?v=...&list=..." URLs
    """
    return re.search(r'[?&]list=', url) is not None


def extract_youtube_playlist(url):
    """
    List the videos of a YouTube playlist with yt-dlp, without resolving their audio streams.

    This call is blocking and must be run in an executor.

    Args:
        url: YouTube playlist URL (or video URL with a "list" parameter)

    Returns:
        tuple: (playlist, tracks) where playlist is a {'name', 'url', 'thumbnail'} dict
        and tracks is a list of {'query', 'label', 'url', 'duration'} dicts

    Raises:
        yt_dlp.utils.DownloadError: If the playlist cannot be read
    """
    with yt_dlp.YoutubeDL(YTDL_PLAYLIST_OPTIONS) as ydl:
        info = ydl.extract_info(url, download=False)

    tracks = []
    for entry in info.get('entries') or []:
        if not entry or entry.get('title') in YOUTUBE_UNAVAILABLE_TITLES:
            continue
        video_url = entry.get('url')
        if not video_url and entry.get('id'):
            video_url = f"https://www.youtube.com/watch?v={entry['id']}"
        if not video_url:
            continue
        tracks.append({'query': video_url, 'label': entry.get('title') or video_url,
                       'url': video_url, 'duration': entry.get('duration')})

    thumbnails = info.get('thumbnails') or []
    playlist = {
        'name': info.get('title') or url,
        'url': info.get('webpage_url') or url,
        'thumbnail': thumbnails[-1].get('url') if thumbnails else None,
    }
    logger.info(f"Fetched {len(tracks)} videos from YouTube playlist '{playlist['name']}'")
    return playlist, tracks
