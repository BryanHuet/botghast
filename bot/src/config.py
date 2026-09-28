"""
Configuration of BotGhast: environment variables and technical constants.

User-visible texts and style live in data/messages.json (see texts.py), not here.
"""

import os

from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = os.getenv('BOT_PREFIX', '?')

# Data files: defaults point to bot/data whatever the working directory
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
GIFS_FILE = os.getenv('GIFS_FILE') or os.path.join(DATA_DIR, 'gifs.json')
QUOTES_FILE = os.getenv('QUOTES_FILE') or os.path.join(DATA_DIR, 'quotes.json')
MESSAGES_FILE = os.getenv('MESSAGES_FILE') or os.path.join(DATA_DIR, 'messages.json')

# yt-dlp: fetch only the best audio stream URL, never download the file
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
}
# yt-dlp for playlists: only list the videos (id, title), without resolving their streams
YTDL_PLAYLIST_OPTIONS = {
    'extract_flat': 'in_playlist',
    'quiet': True,
    'no_warnings': True,
}
# Titles YouTube gives to unavailable videos in a playlist
YOUTUBE_UNAVAILABLE_TITLES = {'[Private video]', '[Deleted video]'}
# Reconnect options so ffmpeg survives short network drops on the stream
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}
PLAYBACK_VOLUME = 0.5

# Spotify Web API (only used to read track names, audio comes from YouTube)
SPOTIFY_API = 'https://api.spotify.com/v1'
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REFRESH_TOKEN = os.getenv('SPOTIFY_REFRESH_TOKEN')
SPOTIFY_PLAYLIST = os.getenv('SPOTIFY_PLAYLIST')

# Seconds to wait before leaving a voice channel with no listener, in case someone comes back
VOICE_IDLE_TIMEOUT = 30
