"""
Shared pytest setup of BotGhast.

config.py loads the .env file and freezes its constants at import time, so the test
environment is set here, before any bot module is imported. Setting a variable (even
empty) prevents python-dotenv from filling it from the developer's .env file.
"""

import os

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')

os.environ.update({
    'DISCORD_TOKEN': 'test-token',
    'BOT_PREFIX': '?',
    'GIFS_FILE': os.path.join(FIXTURES_DIR, 'gifs.json'),
    'QUOTES_FILE': os.path.join(FIXTURES_DIR, 'quotes.json'),
    # MESSAGES_FILE is left to its default: tests use the real bot/data/messages.json
    'SPOTIFY_CLIENT_ID': '',
    'SPOTIFY_CLIENT_SECRET': '',
    'SPOTIFY_REFRESH_TOKEN': '',
    'SPOTIFY_PLAYLIST': '',
})
os.environ.pop('MESSAGES_FILE', None)

from unittest.mock import MagicMock  # noqa: E402

import pytest  # noqa: E402

import music  # noqa: E402
import spotify_client  # noqa: E402
import texts  # noqa: E402


@pytest.fixture(autouse=True)
def reset_global_state():
    """
    Reset the module-level state shared between commands, so tests cannot leak into each other.
    """
    yield
    for task in music.idle_disconnects.values():
        task.cancel()
    for state in (music.music_queues, music.music_channels, music.music_locks,
                  music.now_playing, music.idle_disconnects):
        state.clear()
    spotify_client.spotify_token.update({'access_token': None, 'expires_at': 0,
                                         'refresh_token': spotify_client.SPOTIFY_REFRESH_TOKEN})
    texts._cache.update({'mtime': None, 'data': None})


@pytest.fixture
def data_files(tmp_path, monkeypatch):
    """
    Point the GIFs and quotes files to temporary files written by the test.

    The paths are imported by value in several modules, so each copy is patched.

    Returns:
        callable: write(gifs=..., quotes=...) taking parsed JSON data or raw strings,
        returning the {'gifs', 'quotes'} paths
    """
    import json

    import bot
    import datastore

    def write(gifs=None, quotes=None):
        paths = {}
        for name, content, attribute in (('gifs', gifs, 'GIFS_FILE'), ('quotes', quotes, 'QUOTES_FILE')):
            path = tmp_path / f'{name}.json'
            if content is not None:
                path.write_text(content if isinstance(content, str) else json.dumps(content), encoding='utf-8')
            for module in (bot, datastore):
                monkeypatch.setattr(module, attribute, str(path))
            paths[name] = path
        return paths

    return write


@pytest.fixture
def fake_audio(monkeypatch):
    """
    Replace everything that would touch the network or spawn ffmpeg in the audio pipeline.

    - youtube.extract_audio_info (as imported by music and bot) resolves queries from
      fake_audio.tracks, and raises yt_dlp DownloadError for unknown queries
    - discord.FFmpegPCMAudio and discord.PCMVolumeTransformer are mocks
    - ffmpeg is reported as installed

    Returns:
        FakeAudio: .tracks (query -> meta overrides), .calls (resolved queries)
    """
    import yt_dlp

    import bot
    import music

    class FakeAudio:
        def __init__(self):
            self.tracks = {}
            self.calls = []

        def add(self, query, **meta):
            self.tracks[query] = meta
            return query

        def extract_audio_info(self, query):
            self.calls.append(query)
            if query not in self.tracks:
                raise yt_dlp.utils.DownloadError(f"No result for {query}")
            meta = {'title': query, 'url': query, 'thumbnail': None, 'duration': None, 'uploader': None}
            meta.update(self.tracks[query])
            return f'https://stream.example/{len(self.calls)}', meta

    audio = FakeAudio()
    for module in (music, bot):
        monkeypatch.setattr(module, 'extract_audio_info', audio.extract_audio_info)
    monkeypatch.setattr(music.discord, 'FFmpegPCMAudio', MagicMock(name='FFmpegPCMAudio'))
    monkeypatch.setattr(music.discord, 'PCMVolumeTransformer', MagicMock(name='PCMVolumeTransformer'))
    monkeypatch.setattr(music.shutil, 'which', lambda name: f'/usr/bin/{name}')
    return audio
