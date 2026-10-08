"""
Functional tests of the music commands (joue, viking, suivant, file, stop).

Commands are run through their registered callback with fake discord objects; the
fake_audio fixture stands in for yt-dlp and ffmpeg. Expected texts and embeds are
computed with t() and the views helpers rather than hard-coded.
"""

import discord
import pytest
import yt_dlp

import bot
import music
from fakes import FakeCtx, FakeVoiceClient, make_voice_ctx, wait_until
from texts import t
from views import format_track_line

PLAYLIST_ID = '37i9dQZF1DXcBWIGoYBM5M'
PLAYLIST_URL = f'https://open.spotify.com/playlist/{PLAYLIST_ID}'
YT_PLAYLIST_URL = 'https://www.youtube.com/playlist?list=PLtest'


async def run(name, ctx, *args, **kwargs):
    """Run a registered command as discord.py would, without the parsing step."""
    await bot.bot.get_command(name).callback(ctx, *args, **kwargs)


def only_message(mock):
    """Text of the single message sent through an AsyncMock (ctx.reply...)."""
    mock.assert_awaited_once()
    return mock.await_args.args[0]


def only_embed(mock):
    """Embed of the single message sent through an AsyncMock (ctx.send, channel.send...)."""
    mock.assert_awaited_once()
    return mock.await_args.kwargs['embed']


def embeds(mock):
    """Embeds of every message sent through an AsyncMock, in order."""
    return [call.kwargs['embed'] for call in mock.await_args_list]


def field(embed, name_key):
    """Value of the embed field named by the text key, or None."""
    return next((f.value for f in embed.fields if f.name == t(name_key)), None)


def connect(ctx):
    """Connect the bot to the author's voice channel, as a previous command would have."""
    voice_client = FakeVoiceClient(ctx.author.voice.channel)
    ctx.guild.voice_client = voice_client
    music.music_channels[ctx.guild.id] = ctx.channel
    return voice_client


def entry(label, **extra):
    return {'query': label, 'label': label, 'url': None, 'duration': None, **extra}


@pytest.fixture
def voice_ctx():
    """Context of a member connected to a voice channel, the bot not connected yet."""
    return make_voice_ctx(listeners=1)


class TestCommonChecks:
    """Checks of music.ensure_voice, shared by joue and viking."""

    @pytest.mark.parametrize('name, arg', [('joue', {'url': 'https://youtu.be/a'}), ('viking', {'playlist': PLAYLIST_URL})])
    async def test_direct_message(self, fake_audio, name, arg):
        ctx = FakeCtx(guild=None)

        await run(name, ctx, **arg)

        assert only_message(ctx.reply) == t('common.server_only')

    @pytest.mark.parametrize('name, arg', [('joue', {'url': 'https://youtu.be/a'}), ('viking', {'playlist': PLAYLIST_URL})])
    async def test_author_not_in_voice(self, fake_audio, name, arg):
        ctx = FakeCtx()

        await run(name, ctx, **arg)

        assert only_message(ctx.reply) == t('voice.not_in_voice')
        assert ctx.guild.voice_client is None


class TestJoue:
    @pytest.mark.parametrize('url', [None, ''])
    async def test_no_url(self, voice_ctx, fake_audio, url):
        await run('joue', voice_ctx, url=url)

        assert only_message(voice_ctx.reply) == t('joue.no_url')
        assert voice_ctx.guild.voice_client is None

    async def test_idle_plays_now(self, voice_ctx, fake_audio):
        url = fake_audio.add('https://youtu.be/a', title='Titre A', duration=65, uploader='Chaîne A')

        await run('joue', voice_ctx, url=url)

        voice_client = voice_ctx.guild.voice_client
        voice_ctx.author.voice.channel.connect.assert_awaited_once()
        assert voice_client.is_playing()
        assert music.now_playing[voice_ctx.guild.id]['title'] == 'Titre A'
        assert music.now_playing[voice_ctx.guild.id]['requester'] is voice_ctx.author
        embed = only_embed(voice_ctx.send)
        assert embed.author.name == t('embeds.now_playing')
        assert embed.title == 'Titre A'
        assert field(embed, 'embeds.duration') == '1:05'
        voice_ctx.reply.assert_not_awaited()

    async def test_busy_queues_with_position(self, voice_ctx, fake_audio):
        first = fake_audio.add('https://youtu.be/a', title='Titre A')
        second = fake_audio.add('https://youtu.be/b', title='Titre B', duration=200)
        third = fake_audio.add('https://youtu.be/c', title='Titre C')

        for url in (first, second, third):
            await run('joue', voice_ctx, url=url)

        queue = music.get_queue(voice_ctx.guild.id)
        assert [e['label'] for e in queue] == ['Titre B', 'Titre C']
        assert all(e['requester'] is voice_ctx.author for e in queue)
        assert music.now_playing[voice_ctx.guild.id]['title'] == 'Titre A'
        queued = embeds(voice_ctx.send)[1:]
        assert [e.author.name for e in queued] == [t('embeds.queued')] * 2
        assert [e.title for e in queued] == ['Titre B', 'Titre C']
        assert [field(e, 'embeds.position') for e in queued] == ['1', '2']
        assert field(queued[0], 'embeds.duration') == '3:20'

    async def test_queued_track_plays_after_current(self, voice_ctx, fake_audio):
        first = fake_audio.add('https://youtu.be/a', title='Titre A')
        second = fake_audio.add('https://youtu.be/b', title='Titre B')
        await run('joue', voice_ctx, url=first)
        await run('joue', voice_ctx, url=second)

        voice_ctx.guild.voice_client.finish()
        await wait_until(lambda: music.now_playing[voice_ctx.guild.id]['title'] == 'Titre B')

        assert not music.get_queue(voice_ctx.guild.id)
        assert only_embed(voice_ctx.channel.send).title == 'Titre B'

    async def test_invalid_link_when_idle(self, voice_ctx, fake_audio):
        await run('joue', voice_ctx, url='https://youtu.be/introuvable')

        assert only_message(voice_ctx.reply) == t('joue.download_error')
        assert not voice_ctx.guild.voice_client.is_playing()
        assert voice_ctx.guild.id not in music.now_playing

    async def test_invalid_link_when_busy_is_not_queued(self, voice_ctx, fake_audio):
        await run('joue', voice_ctx, url=fake_audio.add('https://youtu.be/a'))

        await run('joue', voice_ctx, url='https://youtu.be/introuvable')

        assert only_message(voice_ctx.reply) == t('joue.download_error')
        assert not music.get_queue(voice_ctx.guild.id)

    async def test_client_exception(self, voice_ctx, fake_audio):
        voice_client = connect(voice_ctx)

        def play(*args, **kwargs):
            raise discord.ClientException('Already playing audio.')
        voice_client.play = play

        await run('joue', voice_ctx, url=fake_audio.add('https://youtu.be/a'))

        assert only_message(voice_ctx.reply) == t('joue.client_error')

    async def test_unexpected_error(self, voice_ctx, fake_audio, monkeypatch):
        def broken(url):
            raise KeyError('title')
        monkeypatch.setattr(bot, 'is_youtube_playlist', broken)

        await run('joue', voice_ctx, url='https://youtu.be/a')

        assert only_message(voice_ctx.reply) == t('joue.error')

    async def test_youtube_playlist_when_idle(self, voice_ctx, fake_audio, monkeypatch):
        tracks = [entry(fake_audio.add(f'https://youtu.be/{i}', title=f'Vidéo {i}'), duration=60) for i in range(3)]
        monkeypatch.setattr(music, 'extract_youtube_playlist',
                            lambda url: ({'name': 'Ma playlist', 'url': url, 'thumbnail': None}, tracks))

        await run('joue', voice_ctx, url=YT_PLAYLIST_URL)

        embed = only_embed(voice_ctx.send)
        assert embed.author.name == t('embeds.playlist_added', source='YouTube')
        assert embed.title == 'Ma playlist'
        assert embed.description == t('embeds.playlist_tracks', count=3)
        assert field(embed, 'embeds.total_duration') == '3:00'
        # Played in order: the first one starts, the others wait
        assert music.now_playing[voice_ctx.guild.id]['title'] == 'Vidéo 0'
        assert [e['query'] for e in music.get_queue(voice_ctx.guild.id)] == ['https://youtu.be/1', 'https://youtu.be/2']

    async def test_youtube_playlist_when_busy_goes_after_queue(self, voice_ctx, fake_audio, monkeypatch):
        await run('joue', voice_ctx, url=fake_audio.add('https://youtu.be/a', title='Titre A'))
        await run('joue', voice_ctx, url=fake_audio.add('https://youtu.be/b', title='Titre B'))
        tracks = [entry('https://youtu.be/p1'), entry('https://youtu.be/p2')]
        monkeypatch.setattr(music, 'extract_youtube_playlist', lambda url: ({'name': 'P', 'url': url}, tracks))

        await run('joue', voice_ctx, url=YT_PLAYLIST_URL)

        assert music.now_playing[voice_ctx.guild.id]['title'] == 'Titre A'
        assert [e['label'] for e in music.get_queue(voice_ctx.guild.id)] == \
            ['Titre B', 'https://youtu.be/p1', 'https://youtu.be/p2']

    async def test_empty_youtube_playlist(self, voice_ctx, fake_audio, monkeypatch):
        monkeypatch.setattr(music, 'extract_youtube_playlist', lambda url: ({'name': 'Vide'}, []))

        await run('joue', voice_ctx, url=YT_PLAYLIST_URL)

        assert only_message(voice_ctx.reply) == t('joue.empty_playlist')
        voice_ctx.send.assert_not_awaited()

    async def test_unreadable_youtube_playlist(self, voice_ctx, fake_audio, monkeypatch):
        def private(url):
            raise yt_dlp.utils.DownloadError('private playlist')
        monkeypatch.setattr(music, 'extract_youtube_playlist', private)

        await run('joue', voice_ctx, url=YT_PLAYLIST_URL)

        assert only_message(voice_ctx.reply) == t('joue.download_error')


class TestViking:
    @pytest.fixture
    def spotify(self, monkeypatch, fake_audio):
        """
        Fake Spotify API: set .tracks (labels, each playable) or .error before running the command.
        """
        class FakeSpotify:
            tracks = ['Titre 1', 'Titre 2', 'Titre 3']
            error = None
            calls = []

            async def fetch(self, playlist_id):
                self.calls.append(playlist_id)
                if self.error:
                    raise self.error
                return ({'name': 'Viking', 'url': PLAYLIST_URL, 'thumbnail': None},
                        [entry(fake_audio.add(label)) for label in self.tracks])

        fake = FakeSpotify()
        monkeypatch.setattr(bot, 'fetch_spotify_playlist', fake.fetch)
        # Deterministic "shuffle": reverse the order
        monkeypatch.setattr(bot.random, 'shuffle', lambda items: items.reverse())
        return fake

    @pytest.mark.parametrize('playlist', [None, 'pas une playlist'])
    async def test_no_playlist(self, voice_ctx, spotify, playlist):
        await run('viking', voice_ctx, playlist=playlist)

        assert only_message(voice_ctx.reply) == t('viking.no_playlist')
        assert not spotify.calls

    async def test_default_playlist(self, voice_ctx, spotify, monkeypatch):
        monkeypatch.setattr(bot, 'SPOTIFY_PLAYLIST', PLAYLIST_URL)

        await run('viking', voice_ctx)

        assert spotify.calls == [PLAYLIST_ID]

    async def test_idle_queues_shuffled_and_plays(self, voice_ctx, spotify):
        await run('viking', voice_ctx, playlist=PLAYLIST_URL)

        assert spotify.calls == [PLAYLIST_ID]
        embed = only_embed(voice_ctx.send)
        assert embed.author.name == t('embeds.playlist_added', source='Spotify')
        assert embed.description == t('embeds.playlist_tracks_shuffled', count=3)
        assert music.now_playing[voice_ctx.guild.id]['title'] == 'Titre 3'
        assert music.now_playing[voice_ctx.guild.id]['requester'] is voice_ctx.author
        assert [e['label'] for e in music.get_queue(voice_ctx.guild.id)] == ['Titre 2', 'Titre 1']
        assert only_embed(voice_ctx.channel.send).title == 'Titre 3'

    async def test_busy_replaces_queue_and_skips_current(self, voice_ctx, spotify, fake_audio):
        await run('joue', voice_ctx, url=fake_audio.add('https://youtu.be/a', title='Titre A'))
        await run('joue', voice_ctx, url=fake_audio.add('https://youtu.be/b', title='Titre B'))

        await run('viking', voice_ctx, playlist=PLAYLIST_ID)
        await wait_until(lambda: music.now_playing[voice_ctx.guild.id]['title'] == 'Titre 3')

        assert [e['label'] for e in music.get_queue(voice_ctx.guild.id)] == ['Titre 2', 'Titre 1']

    async def test_empty_playlist(self, voice_ctx, spotify):
        spotify.tracks = []

        await run('viking', voice_ctx, playlist=PLAYLIST_URL)

        assert only_message(voice_ctx.reply) == t('viking.empty_playlist')
        voice_ctx.send.assert_not_awaited()

    async def test_api_error(self, voice_ctx, spotify):
        spotify.error = RuntimeError('Spotify API error 401')

        await run('viking', voice_ctx, playlist=PLAYLIST_URL)

        assert only_message(voice_ctx.reply) == t('viking.api_error')

    async def test_unexpected_error(self, voice_ctx, spotify):
        spotify.error = KeyError('items')

        await run('viking', voice_ctx, playlist=PLAYLIST_URL)

        assert only_message(voice_ctx.reply) == t('viking.error')


class TestSuivant:
    @pytest.mark.parametrize('setup', ['dm', 'not_connected', 'idle'])
    async def test_nothing_playing(self, voice_ctx, setup):
        ctx = FakeCtx(guild=None) if setup == 'dm' else voice_ctx
        if setup == 'idle':
            connect(ctx)

        await run('suivant', ctx)

        assert only_message(ctx.reply) == t('suivant.nothing_playing')

    async def test_skips_to_next(self, voice_ctx, fake_audio):
        await run('joue', voice_ctx, url=fake_audio.add('https://youtu.be/a', title='Titre A'))
        await run('joue', voice_ctx, url=fake_audio.add('https://youtu.be/b', title='Titre B'))
        voice_ctx.send.reset_mock()

        await run('suivant', voice_ctx)
        await wait_until(lambda: music.now_playing[voice_ctx.guild.id]['title'] == 'Titre B')

        embed = only_embed(voice_ctx.send)
        assert embed.description == t('suivant.skipped_track', track=format_track_line('Titre A', 'https://youtu.be/a'))
        assert only_embed(voice_ctx.channel.send).title == 'Titre B'

    async def test_skips_last_track(self, voice_ctx, fake_audio):
        await run('joue', voice_ctx, url=fake_audio.add('https://youtu.be/a', title='Titre A'))
        voice_ctx.send.reset_mock()

        await run('suivant', voice_ctx)
        await wait_until(lambda: voice_ctx.guild.id not in music.now_playing)

        skipped = t('suivant.skipped_track', track=format_track_line('Titre A', 'https://youtu.be/a'))
        assert only_embed(voice_ctx.send).description == skipped + '\n' + t('suivant.queue_empty')
        assert voice_ctx.guild.voice_client.is_connected()

    async def test_without_now_playing_metadata(self, voice_ctx):
        voice_client = connect(voice_ctx)
        voice_client.play(object())

        await run('suivant', voice_ctx)

        assert only_embed(voice_ctx.send).description == t('suivant.skipped') + '\n' + t('suivant.queue_empty')

    async def test_error(self, voice_ctx):
        voice_client = connect(voice_ctx)
        voice_client.play(object())

        def broken():
            raise RuntimeError('boom')
        voice_client.stop = broken

        await run('suivant', voice_ctx)

        assert only_message(voice_ctx.reply) == t('suivant.error')


class TestFile:
    async def test_direct_message(self):
        ctx = FakeCtx(guild=None)

        await run('file', ctx)

        assert only_message(ctx.reply) == t('common.server_only')

    async def test_empty(self, voice_ctx):
        await run('file', voice_ctx)

        assert only_embed(voice_ctx.send).description == t('file.empty')

    async def test_current_and_queue(self, voice_ctx, fake_audio):
        await run('joue', voice_ctx, url=fake_audio.add('https://youtu.be/a', title='Titre A', duration=90))
        await run('joue', voice_ctx, url=fake_audio.add('https://youtu.be/b', title='Titre B'))
        voice_ctx.send.reset_mock()

        await run('file', voice_ctx)

        embed = only_embed(voice_ctx.send)
        assert embed.title == t('embeds.queue_title')
        assert 'Titre A' in field(embed, 'embeds.queue_current')
        assert 'Titre B' in embed.description

    async def test_queue_without_current_track(self, voice_ctx):
        music.get_queue(voice_ctx.guild.id).append(entry('En attente'))

        await run('file', voice_ctx)

        embed = only_embed(voice_ctx.send)
        assert field(embed, 'embeds.queue_current') is None
        assert 'En attente' in embed.description

    async def test_error(self, voice_ctx, monkeypatch):
        music.get_queue(voice_ctx.guild.id).append(entry('En attente'))

        def broken(*args):
            raise RuntimeError('boom')
        monkeypatch.setattr(bot, 'queue_embed', broken)

        await run('file', voice_ctx)

        assert only_message(voice_ctx.reply) == t('file.error')


class TestStop:
    @pytest.mark.parametrize('dm', [True, False])
    async def test_not_connected(self, voice_ctx, dm):
        ctx = FakeCtx(guild=None) if dm else voice_ctx

        await run('stop', ctx)

        assert only_message(ctx.reply) == t('stop.not_connected')

    async def test_stops_clears_and_leaves(self, voice_ctx, fake_audio):
        await run('joue', voice_ctx, url=fake_audio.add('https://youtu.be/a'))
        await run('joue', voice_ctx, url=fake_audio.add('https://youtu.be/b'))
        voice_client = voice_ctx.guild.voice_client
        voice_ctx.send.reset_mock()

        await run('stop', voice_ctx)

        voice_client.disconnect.assert_awaited_once()
        assert voice_ctx.guild.voice_client is None
        assert not music.get_queue(voice_ctx.guild.id)
        assert voice_ctx.guild.id not in music.now_playing
        assert only_embed(voice_ctx.send).description == t('stop.stopped')

    async def test_error(self, voice_ctx):
        voice_client = connect(voice_ctx)
        voice_client.disconnect.side_effect = RuntimeError('boom')

        await run('stop', voice_ctx)

        assert only_message(voice_ctx.reply) == t('stop.error')
