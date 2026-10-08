"""
Unit tests of spotify_client.py. HTTP calls to Spotify are mocked with aioresponses.
"""

import logging
import re
import time

import aiohttp
import pytest
from aioresponses import aioresponses

import spotify_client
from config import SPOTIFY_API
from spotify_client import fetch_spotify_playlist, get_spotify_access_token, parse_spotify_playlist_id

PLAYLIST_ID = '37i9dQZF1DXcBWIGoYBM5M'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
PLAYLIST_URL = re.compile(rf'^{re.escape(SPOTIFY_API)}/playlists/{PLAYLIST_ID}(\?.*)?$')
ITEMS_URL = re.compile(rf'^{re.escape(SPOTIFY_API)}/playlists/{PLAYLIST_ID}/items(\?.*)?$')


@pytest.fixture
def credentials(monkeypatch):
    """Configure Spotify credentials (the test environment has none)."""
    monkeypatch.setattr(spotify_client, 'SPOTIFY_CLIENT_ID', 'client-id')
    monkeypatch.setattr(spotify_client, 'SPOTIFY_CLIENT_SECRET', 'client-secret')
    spotify_client.spotify_token['refresh_token'] = 'refresh-token'


@pytest.fixture
def http():
    with aioresponses() as mocked:
        yield mocked


def requests_to(http, method, url_prefix):
    """Calls recorded by aioresponses whose URL starts with url_prefix."""
    return [call for (m, url), calls in http.requests.items() if m == method and str(url).startswith(url_prefix)
            for call in calls]


def spotify_track(name, artists=('Artiste',), duration_ms=180000, kind='track'):
    return {'type': kind, 'name': name, 'duration_ms': duration_ms,
            'artists': [{'name': artist} for artist in artists],
            'external_urls': {'spotify': f'https://open.spotify.com/track/{name}'}}


class TestParseSpotifyPlaylistId:
    @pytest.mark.parametrize('value', [
        f'https://open.spotify.com/playlist/{PLAYLIST_ID}',
        f'https://open.spotify.com/playlist/{PLAYLIST_ID}?si=abc123',
        f'https://open.spotify.com/intl-fr/playlist/{PLAYLIST_ID}',
        f'spotify:playlist:{PLAYLIST_ID}',
        PLAYLIST_ID,
    ])
    def test_recognized_values(self, value):
        assert parse_spotify_playlist_id(value) == PLAYLIST_ID

    @pytest.mark.parametrize('value', [
        '',
        'viking',
        PLAYLIST_ID[:-1],
        PLAYLIST_ID + 'X',
        f'https://open.spotify.com/album/{PLAYLIST_ID}',
        f'spotify:track:{PLAYLIST_ID}',
        'https://www.youtube.com/playlist?list=PL1234567890',
    ])
    def test_unrecognized_values(self, value):
        assert parse_spotify_playlist_id(value) is None


class TestGetSpotifyAccessToken:
    async def test_missing_credentials_raise(self, http):
        async with aiohttp.ClientSession() as session:
            with pytest.raises(RuntimeError, match='must be set'):
                await get_spotify_access_token(session)
        assert not http.requests

    async def test_valid_cached_token_is_reused(self, http):
        spotify_client.spotify_token.update({'access_token': 'cached', 'expires_at': time.time() + 600})
        async with aiohttp.ClientSession() as session:
            assert await get_spotify_access_token(session) == 'cached'
        assert not http.requests

    async def test_expired_token_is_refreshed(self, http, credentials):
        spotify_client.spotify_token.update({'access_token': 'old', 'expires_at': time.time() - 1})
        http.post(TOKEN_URL, payload={'access_token': 'new', 'expires_in': 3600})
        async with aiohttp.ClientSession() as session:
            assert await get_spotify_access_token(session) == 'new'

        [call] = requests_to(http, 'POST', TOKEN_URL)
        assert call.kwargs['data'] == {'grant_type': 'refresh_token', 'refresh_token': 'refresh-token'}
        assert call.kwargs['auth'] == aiohttp.BasicAuth('client-id', 'client-secret')
        # Refreshed one minute before the real expiry
        assert spotify_client.spotify_token['expires_at'] == pytest.approx(time.time() + 3600 - 60, abs=5)
        assert spotify_client.spotify_token['refresh_token'] == 'refresh-token'

    async def test_new_refresh_token_is_kept(self, http, credentials, caplog):
        http.post(TOKEN_URL, payload={'access_token': 'new', 'refresh_token': 'rotated'})
        async with aiohttp.ClientSession() as session:
            with caplog.at_level(logging.WARNING, logger='botghast'):
                await get_spotify_access_token(session)
        assert spotify_client.spotify_token['refresh_token'] == 'rotated'
        assert 'new refresh token' in caplog.text

    async def test_refused_refresh_raises(self, http, credentials):
        http.post(TOKEN_URL, status=400, payload={'error': 'invalid_grant'})
        async with aiohttp.ClientSession() as session:
            with pytest.raises(RuntimeError, match='400'):
                await get_spotify_access_token(session)
        assert spotify_client.spotify_token['access_token'] is None


class TestFetchSpotifyPlaylist:
    @pytest.fixture(autouse=True)
    def valid_token(self):
        spotify_client.spotify_token.update({'access_token': 'token', 'expires_at': time.time() + 600})

    def mock_playlist(self, http, **data):
        data = {'name': 'Viking', 'images': [{'url': 'https://i.scdn.co/big'}, {'url': 'https://i.scdn.co/small'}],
                'external_urls': {'spotify': f'https://open.spotify.com/playlist/{PLAYLIST_ID}'}, **data}
        http.get(PLAYLIST_URL, payload=data)

    async def test_playlist_and_tracks(self, http):
        self.mock_playlist(http)
        http.get(ITEMS_URL, payload={'items': [
            {'item': spotify_track('Skål', artists=('Wardruna', 'Einar Selvik'))},
            # 'track' is the deprecated name of 'item'
            {'track': spotify_track('Helvegen', artists=())},
        ], 'next': None})

        playlist, tracks = await fetch_spotify_playlist(PLAYLIST_ID)

        assert playlist == {'name': 'Viking', 'url': f'https://open.spotify.com/playlist/{PLAYLIST_ID}',
                            'thumbnail': 'https://i.scdn.co/big'}
        assert tracks == [
            {'query': 'ytsearch1:Skål Wardruna, Einar Selvik', 'label': 'Skål - Wardruna, Einar Selvik',
             'url': 'https://open.spotify.com/track/Skål', 'duration': 180.0},
            {'query': 'ytsearch1:Helvegen ', 'label': 'Helvegen',
             'url': 'https://open.spotify.com/track/Helvegen', 'duration': 180.0},
        ]
        for call in requests_to(http, 'GET', SPOTIFY_API):
            assert call.kwargs['headers'] == {'Authorization': 'Bearer token'}

    async def test_skips_non_playable_items(self, http):
        self.mock_playlist(http)
        http.get(ITEMS_URL, payload={'items': [
            {'item': None},
            {},
            {'item': spotify_track('Podcast', kind='episode')},
            {'item': spotify_track('')},
            {'item': spotify_track('Sans durée', duration_ms=None)},
        ]})

        _, tracks = await fetch_spotify_playlist(PLAYLIST_ID)

        assert [track['label'] for track in tracks] == ['Sans durée - Artiste']
        assert tracks[0]['duration'] is None

    async def test_follows_pagination(self, http):
        self.mock_playlist(http)
        next_page = f'{SPOTIFY_API}/playlists/{PLAYLIST_ID}/items?offset=50&limit=50'
        http.get(ITEMS_URL, payload={'items': [{'item': spotify_track('Un')}], 'next': next_page})
        http.get(ITEMS_URL, payload={'items': [{'item': spotify_track('Deux')}], 'next': None})

        _, tracks = await fetch_spotify_playlist(PLAYLIST_ID)

        assert [track['label'] for track in tracks] == ['Un - Artiste', 'Deux - Artiste']
        first, second = requests_to(http, 'GET', f'{SPOTIFY_API}/playlists/{PLAYLIST_ID}/items')
        assert first.kwargs['params'] == {'limit': 50, 'additional_types': 'track'}
        # 'next' already contains the query parameters
        assert second.kwargs['params'] is None

    async def test_minimal_playlist(self, http):
        http.get(PLAYLIST_URL, payload={})
        http.get(ITEMS_URL, payload={})

        playlist, tracks = await fetch_spotify_playlist(PLAYLIST_ID)

        assert playlist == {'name': PLAYLIST_ID, 'url': None, 'thumbnail': None}
        assert tracks == []

    async def test_playlist_error_raises(self, http):
        http.get(PLAYLIST_URL, status=404, body='Not found')
        with pytest.raises(RuntimeError, match='404'):
            await fetch_spotify_playlist(PLAYLIST_ID)

    async def test_items_error_raises(self, http):
        self.mock_playlist(http)
        http.get(ITEMS_URL, status=403, body='Forbidden')
        with pytest.raises(RuntimeError, match='403'):
            await fetch_spotify_playlist(PLAYLIST_ID)
