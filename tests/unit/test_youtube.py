"""
Unit tests of youtube.py.
"""

import pytest

from youtube import is_youtube_playlist


class TestIsYoutubePlaylist:
    @pytest.mark.parametrize('url', [
        'https://www.youtube.com/playlist?list=PL1234567890',
        'https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL1234567890',
        'https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=RDdQw4w9WgXcQ&start_radio=1',
        'https://music.youtube.com/playlist?list=OLAK5uy_x',
        'https://youtu.be/dQw4w9WgXcQ?list=PL1234567890',
    ])
    def test_playlist_urls(self, url):
        assert is_youtube_playlist(url)

    @pytest.mark.parametrize('url', [
        'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        'https://youtu.be/dQw4w9WgXcQ?t=42',
        'https://www.youtube.com/watch?v=dQw4w9WgXcQ&playlist=PL1234567890',
        'https://www.youtube.com/watch?v=dQw4w9WgXcQ&blacklist=1',
        'ytsearch1:list=chanson',
        '',
    ])
    def test_other_urls(self, url):
        assert not is_youtube_playlist(url)
