"""
Unit tests of youtube.py. yt-dlp is replaced by a fake YoutubeDL: no network.
"""

import pytest
import yt_dlp

import youtube
from config import YTDL_OPTIONS, YTDL_PLAYLIST_OPTIONS
from youtube import extract_audio_info, extract_youtube_playlist, is_youtube_playlist


@pytest.fixture
def fake_ytdl(monkeypatch):
    """
    Replace yt_dlp.YoutubeDL with a fake returning fake_ytdl.info.

    Returns:
        FakeYoutubeDL class: set .info before the call, read .options and .queries after
    """
    class FakeYoutubeDL:
        info = {}
        options = None
        queries = []

        def __init__(self, options):
            FakeYoutubeDL.options = options

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def extract_info(self, query, download=True):
            assert download is False, 'the bot must never download files'
            FakeYoutubeDL.queries.append(query)
            return FakeYoutubeDL.info

    FakeYoutubeDL.queries = []
    monkeypatch.setattr(youtube.yt_dlp, 'YoutubeDL', FakeYoutubeDL)
    return FakeYoutubeDL


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


VIDEO_INFO = {
    'url': 'https://rr1.googlevideo.com/stream',
    'title': 'Titre',
    'webpage_url': 'https://www.youtube.com/watch?v=abc',
    'thumbnail': 'https://i.ytimg.com/vi/abc/hq.jpg',
    'duration': 185,
    'uploader': 'Chaîne',
}


class TestExtractAudioInfo:
    def test_video(self, fake_ytdl):
        fake_ytdl.info = VIDEO_INFO
        stream_url, meta = extract_audio_info('https://www.youtube.com/watch?v=abc')
        assert stream_url == VIDEO_INFO['url']
        assert meta == {'title': 'Titre', 'url': VIDEO_INFO['webpage_url'], 'thumbnail': VIDEO_INFO['thumbnail'],
                        'duration': 185, 'uploader': 'Chaîne'}
        assert fake_ytdl.options is YTDL_OPTIONS
        assert fake_ytdl.queries == ['https://www.youtube.com/watch?v=abc']

    def test_missing_metadata(self, fake_ytdl):
        fake_ytdl.info = {'url': 'https://rr1.googlevideo.com/stream', 'channel': 'Chaîne'}
        _, meta = extract_audio_info('ytsearch1:chanson')
        assert meta == {'title': 'ytsearch1:chanson', 'url': None, 'thumbnail': None,
                        'duration': None, 'uploader': 'Chaîne'}

    def test_search_keeps_first_result(self, fake_ytdl):
        fake_ytdl.info = {'entries': [VIDEO_INFO, {**VIDEO_INFO, 'title': 'Second'}]}
        _, meta = extract_audio_info('ytsearch1:chanson')
        assert meta['title'] == 'Titre'

    def test_search_without_result_raises(self, fake_ytdl):
        fake_ytdl.info = {'entries': []}
        with pytest.raises(yt_dlp.utils.DownloadError):
            extract_audio_info('ytsearch1:introuvable')


class TestExtractYoutubePlaylist:
    URL = 'https://www.youtube.com/playlist?list=PL123'

    def test_lists_playable_videos(self, fake_ytdl):
        fake_ytdl.info = {
            'title': 'Ma playlist',
            'webpage_url': self.URL,
            'thumbnails': [{'url': 'https://i.ytimg.com/small.jpg'}, {'url': 'https://i.ytimg.com/big.jpg'}],
            'entries': [
                {'url': 'https://www.youtube.com/watch?v=a', 'title': 'A', 'duration': 60},
                None,
                {'url': 'https://www.youtube.com/watch?v=p', 'title': '[Private video]'},
                {'url': 'https://www.youtube.com/watch?v=d', 'title': '[Deleted video]'},
                {'id': 'b', 'title': 'B'},
                {'title': 'Sans URL ni id'},
                {'url': 'https://www.youtube.com/watch?v=c'},
            ],
        }
        playlist, tracks = extract_youtube_playlist(self.URL)
        assert fake_ytdl.options is YTDL_PLAYLIST_OPTIONS
        assert playlist == {'name': 'Ma playlist', 'url': self.URL, 'thumbnail': 'https://i.ytimg.com/big.jpg'}
        assert tracks == [
            {'query': 'https://www.youtube.com/watch?v=a', 'label': 'A',
             'url': 'https://www.youtube.com/watch?v=a', 'duration': 60},
            {'query': 'https://www.youtube.com/watch?v=b', 'label': 'B',
             'url': 'https://www.youtube.com/watch?v=b', 'duration': None},
            {'query': 'https://www.youtube.com/watch?v=c', 'label': 'https://www.youtube.com/watch?v=c',
             'url': 'https://www.youtube.com/watch?v=c', 'duration': None},
        ]

    @pytest.mark.parametrize('info', [{}, {'entries': None}, {'entries': []}])
    def test_empty_playlist(self, fake_ytdl, info):
        fake_ytdl.info = info
        playlist, tracks = extract_youtube_playlist(self.URL)
        assert tracks == []
        assert playlist == {'name': self.URL, 'url': self.URL, 'thumbnail': None}
