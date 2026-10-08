"""
Unit tests of spotify_client.py.
"""

import pytest

from spotify_client import parse_spotify_playlist_id

PLAYLIST_ID = '37i9dQZF1DXcBWIGoYBM5M'


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
