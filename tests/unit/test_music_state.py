"""
Unit tests of music.py building blocks: per-guild state, voice checks and track start.

Queue chaining (play_next), playlists and idle disconnection are covered by the
functional tests of the music commands.
"""

import asyncio
import logging
from collections import deque
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

import music
from config import FFMPEG_OPTIONS, PLAYBACK_VOLUME
from fakes import FakeCtx, FakeGuild, FakeMember, FakeVoiceChannel, FakeVoiceClient, make_voice_ctx
from texts import t


def http_error(cls):
    return cls(MagicMock(status=403, reason='Forbidden'), 'Missing Permissions')


class TestGuildState:
    def test_queue_is_created_once_per_guild(self):
        queue = music.get_queue(1)
        assert isinstance(queue, deque) and not queue
        assert music.get_queue(1) is queue
        assert music.get_queue(2) is not queue

    def test_lock_is_created_once_per_guild(self):
        lock = music.get_lock(1)
        assert isinstance(lock, asyncio.Lock)
        assert music.get_lock(1) is lock
        assert music.get_lock(2) is not lock

    def test_clear_guild(self):
        music.get_queue(1).extend([{'label': 'a'}, {'label': 'b'}])
        music.get_queue(2).append({'label': 'other guild'})
        music.now_playing[1] = {'title': 'a'}

        music.clear_guild(1)

        assert not music.get_queue(1)
        assert 1 not in music.now_playing
        assert len(music.get_queue(2)) == 1

    def test_clear_unknown_guild(self):
        music.clear_guild(42)
        assert not music.get_queue(42)


class TestIsBusy:
    def test_idle(self):
        assert not music.is_busy(FakeVoiceClient(FakeVoiceChannel()))

    def test_playing(self):
        voice_client = FakeVoiceClient(FakeVoiceChannel())
        voice_client.play(MagicMock())
        assert music.is_busy(voice_client)

    def test_paused(self):
        voice_client = FakeVoiceClient(FakeVoiceChannel())
        voice_client._paused = True
        assert music.is_busy(voice_client)


class TestHasListeners:
    @pytest.mark.parametrize('members, expected', [
        ([], False),
        ([FakeMember('BotGhast', bot=True)], False),
        ([FakeMember('BotGhast', bot=True), FakeMember('Autre bot', bot=True)], False),
        ([FakeMember('alice')], True),
        ([FakeMember('BotGhast', bot=True), FakeMember('alice')], True),
    ])
    def test_has_listeners(self, members, expected):
        assert music.has_listeners(FakeVoiceChannel(members=members)) is expected


class TestEnsureVoice:
    @pytest.fixture(autouse=True)
    def ffmpeg_installed(self, monkeypatch):
        monkeypatch.setattr(music.shutil, 'which', lambda name: f'/usr/bin/{name}')

    async def test_direct_message(self):
        ctx = FakeCtx(guild=None)
        assert await music.ensure_voice(ctx) is None
        ctx.reply.assert_awaited_once_with(t('common.server_only'))

    async def test_author_not_in_voice(self):
        ctx = FakeCtx()
        assert await music.ensure_voice(ctx) is None
        ctx.reply.assert_awaited_once_with(t('voice.not_in_voice'))

    async def test_ffmpeg_missing(self, monkeypatch, caplog):
        monkeypatch.setattr(music.shutil, 'which', lambda name: None)
        ctx = make_voice_ctx()
        with caplog.at_level(logging.ERROR, logger='botghast'):
            assert await music.ensure_voice(ctx) is None
        ctx.reply.assert_awaited_once_with(t('voice.no_ffmpeg'))
        assert 'ffmpeg executable not found' in caplog.text
        ctx.author.voice.channel.connect.assert_not_awaited()

    async def test_connects_to_author_channel(self):
        ctx = make_voice_ctx()
        voice_client = await music.ensure_voice(ctx)

        channel = ctx.author.voice.channel
        channel.connect.assert_awaited_once()
        assert voice_client is ctx.voice_client
        assert voice_client.channel is channel
        assert music.music_channels[ctx.guild.id] is ctx.channel
        ctx.reply.assert_not_awaited()

    async def test_stays_in_same_channel(self):
        ctx = make_voice_ctx()
        existing = await ctx.author.voice.channel.connect()
        ctx.author.voice.channel.connect.reset_mock()

        assert await music.ensure_voice(ctx) is existing
        ctx.author.voice.channel.connect.assert_not_awaited()
        existing.move_to.assert_not_awaited()

    async def test_moves_to_author_channel(self):
        guild = FakeGuild()
        other_channel = guild.add_voice_channel('Autre salon')
        existing = await other_channel.connect()
        ctx = make_voice_ctx(guild=guild)

        assert await music.ensure_voice(ctx) is existing
        existing.move_to.assert_awaited_once_with(ctx.author.voice.channel)
        assert existing.channel is ctx.author.voice.channel

    async def test_join_forbidden(self):
        ctx = make_voice_ctx()
        ctx.author.voice.channel.connect = AsyncMock(side_effect=http_error(discord.Forbidden))

        assert await music.ensure_voice(ctx) is None
        ctx.reply.assert_awaited_once_with(t('voice.join_forbidden'))
        assert ctx.guild.id not in music.music_channels

    async def test_join_error(self):
        ctx = make_voice_ctx()
        ctx.author.voice.channel.connect = AsyncMock(side_effect=asyncio.TimeoutError())

        assert await music.ensure_voice(ctx) is None
        ctx.reply.assert_awaited_once_with(t('voice.join_error'))


class TestStartTrack:
    async def test_starts_playback(self, fake_audio):
        guild = FakeGuild()
        voice_client = await guild.add_voice_channel().connect()
        requester = FakeMember('alice')
        query = fake_audio.add('https://youtu.be/x', title='Titre', duration=185)

        meta = await music.start_track(guild, voice_client,
                                       {'query': query, 'label': query, 'requester': requester})

        assert meta['title'] == 'Titre'
        assert meta['requester'] is requester
        assert music.now_playing[guild.id] is meta
        assert fake_audio.calls == [query]
        music.discord.FFmpegPCMAudio.assert_called_once_with('https://stream.example/1', **FFMPEG_OPTIONS)
        music.discord.PCMVolumeTransformer.assert_called_once_with(
            music.discord.FFmpegPCMAudio.return_value, volume=PLAYBACK_VOLUME)
        assert voice_client.is_playing()
        assert voice_client.source is music.discord.PCMVolumeTransformer.return_value

    async def test_entry_without_requester(self, fake_audio):
        guild = FakeGuild()
        voice_client = await guild.add_voice_channel().connect()
        query = fake_audio.add('ytsearch1:chanson')

        meta = await music.start_track(guild, voice_client, {'query': query, 'label': 'chanson'})

        assert meta['requester'] is None

    async def test_unresolvable_track_raises_without_playing(self, fake_audio):
        guild = FakeGuild()
        voice_client = await guild.add_voice_channel().connect()

        with pytest.raises(Exception):
            await music.start_track(guild, voice_client, {'query': 'https://youtu.be/invalide', 'label': 'x'})

        assert not voice_client.is_playing()
        assert guild.id not in music.now_playing

    async def test_end_of_track_triggers_play_next(self, fake_audio, monkeypatch, caplog):
        guild = FakeGuild()
        voice_client = await guild.add_voice_channel().connect()
        called = asyncio.Event()
        play_next = AsyncMock(side_effect=lambda guild: called.set())
        monkeypatch.setattr(music, 'play_next', play_next)
        query = fake_audio.add('https://youtu.be/x', title='Titre')
        await music.start_track(guild, voice_client, {'query': query, 'label': query})

        with caplog.at_level(logging.INFO, logger='botghast'):
            # In production the after callback runs in the audio thread and hands over to the event loop
            voice_client.finish(error=RuntimeError('stream cut'))
            await asyncio.wait_for(called.wait(), timeout=1)

        play_next.assert_awaited_once_with(guild)
        assert 'Playback error' in caplog.text and 'stream cut' in caplog.text
