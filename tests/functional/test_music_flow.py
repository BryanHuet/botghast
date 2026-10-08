"""
Functional tests of the music flow across commands and voice events: chaining of the
queue when a track ends, unplayable tracks, end of queue and idle disconnection.
"""

import asyncio

import pytest

import bot
import music
from fakes import make_voice_ctx, wait_until
from texts import t
from views import format_track_line

pytestmark = pytest.mark.usefixtures('fake_audio')


async def run(name, ctx, *args, **kwargs):
    await bot.bot.get_command(name).callback(ctx, *args, **kwargs)


def embeds(mock):
    return [call.kwargs['embed'] for call in mock.await_args_list]


def title(ctx):
    track = music.now_playing.get(ctx.guild.id)
    return track and track['title']


@pytest.fixture
def ctx():
    return make_voice_ctx(listeners=1)


async def finish_and_wait(ctx, expected_title):
    """End the current track and wait for play_next to start the next one (or to stop)."""
    ctx.guild.voice_client.finish()
    await wait_until(lambda: title(ctx) == expected_title)


class TestChaining:
    async def test_queue_plays_in_order_then_stops(self, ctx, fake_audio):
        for name in 'ABC':
            await run('joue', ctx, url=fake_audio.add(f'https://youtu.be/{name}', title=f'Titre {name}'))

        await finish_and_wait(ctx, 'Titre B')
        await finish_and_wait(ctx, 'Titre C')
        await finish_and_wait(ctx, None)

        assert [e.title for e in embeds(ctx.channel.send)] == ['Titre B', 'Titre C']
        voice_client = ctx.guild.voice_client
        assert voice_client.is_connected() and not voice_client.is_playing()
        assert not music.get_queue(ctx.guild.id)

    async def test_playback_error_still_chains(self, ctx, fake_audio):
        await run('joue', ctx, url=fake_audio.add('https://youtu.be/A', title='Titre A'))
        await run('joue', ctx, url=fake_audio.add('https://youtu.be/B', title='Titre B'))

        ctx.guild.voice_client.finish(error=RuntimeError('ffmpeg crashed'))
        await wait_until(lambda: title(ctx) == 'Titre B')

    async def test_unplayable_track_is_skipped_with_message(self, ctx, fake_audio):
        await run('joue', ctx, url=fake_audio.add('https://youtu.be/A', title='Titre A'))
        await run('joue', ctx, url=fake_audio.add('https://youtu.be/B', title='Titre B'))
        await run('joue', ctx, url=fake_audio.add('https://youtu.be/C', title='Titre C'))
        # Video B became unavailable between ?joue and its turn
        del fake_audio.tracks['https://youtu.be/B']

        await finish_and_wait(ctx, 'Titre C')

        error, playing = embeds(ctx.channel.send)
        assert error.description == t('voice.track_error', track=format_track_line('Titre B', 'https://youtu.be/B'))
        assert playing.title == 'Titre C'

    async def test_queue_of_unplayable_tracks_ends_cleanly(self, ctx, fake_audio):
        await run('joue', ctx, url=fake_audio.add('https://youtu.be/A', title='Titre A'))
        await run('joue', ctx, url=fake_audio.add('https://youtu.be/B', title='Titre B'))
        del fake_audio.tracks['https://youtu.be/B']

        await finish_and_wait(ctx, None)

        assert len(embeds(ctx.channel.send)) == 1
        assert not music.get_queue(ctx.guild.id)

    async def test_end_of_track_after_stop_does_nothing(self, ctx, fake_audio):
        await run('joue', ctx, url=fake_audio.add('https://youtu.be/A', title='Titre A'))
        await run('joue', ctx, url=fake_audio.add('https://youtu.be/B', title='Titre B'))
        voice_client = ctx.guild.voice_client
        await run('stop', ctx)

        # A late after callback, once disconnected, must not restart anything
        voice_client.after(None)
        await asyncio.sleep(0.01)

        assert fake_audio.calls == ['https://youtu.be/A', 'https://youtu.be/B']
        ctx.channel.send.assert_not_awaited()

    async def test_joue_after_end_of_queue_plays_now(self, ctx, fake_audio):
        await run('joue', ctx, url=fake_audio.add('https://youtu.be/A', title='Titre A'))
        await finish_and_wait(ctx, None)

        await run('joue', ctx, url=fake_audio.add('https://youtu.be/B', title='Titre B'))

        assert title(ctx) == 'Titre B'


class TestIdleDisconnect:
    @pytest.fixture
    def playing(self, ctx, fake_audio):
        """The bot is playing a track with one queued track; returns a 'leave' helper."""
        async def start():
            await run('joue', ctx, url=fake_audio.add('https://youtu.be/A', title='Titre A'))
            await run('joue', ctx, url=fake_audio.add('https://youtu.be/B', title='Titre B'))
            return ctx.guild.voice_client
        return start

    async def leave_all(self, ctx):
        """Every human leaves the voice channel, each one triggering a voice state update."""
        channel = ctx.guild.voice_client.channel
        for member in [m for m in channel.members if not m.bot]:
            channel.members.remove(member)
            member.guild = ctx.guild
            await bot.on_voice_state_update(member, None, None)

    async def test_leaves_when_alone(self, ctx, playing, monkeypatch):
        monkeypatch.setattr(music, 'VOICE_IDLE_TIMEOUT', 0)
        voice_client = await playing()

        await self.leave_all(ctx)
        task = music.idle_disconnects[ctx.guild.id]
        await task

        voice_client.disconnect.assert_awaited_once()
        assert ctx.guild.voice_client is None
        assert not music.get_queue(ctx.guild.id)
        assert ctx.guild.id not in music.now_playing
        assert ctx.guild.id not in music.idle_disconnects
        assert embeds(ctx.channel.send)[-1].description == t('voice.left_empty')

    async def test_one_listener_left_keeps_playing(self, ctx, playing):
        voice_client = await playing()
        channel = voice_client.channel
        member = channel.members.pop()  # one of the two humans leaves
        member.guild = ctx.guild

        await bot.on_voice_state_update(member, None, None)

        assert ctx.guild.id not in music.idle_disconnects
        assert voice_client.is_playing()

    async def test_listener_back_cancels_disconnect(self, ctx, playing, monkeypatch):
        monkeypatch.setattr(music, 'VOICE_IDLE_TIMEOUT', 60)
        voice_client = await playing()
        await self.leave_all(ctx)
        task = music.idle_disconnects[ctx.guild.id]

        voice_client.channel.members.append(ctx.author)
        await bot.on_voice_state_update(ctx.author, None, None)
        with pytest.raises(asyncio.CancelledError):
            await task

        assert ctx.guild.id not in music.idle_disconnects
        voice_client.disconnect.assert_not_awaited()
        assert voice_client.is_playing()

    async def test_several_updates_schedule_one_disconnect(self, ctx, playing, monkeypatch):
        monkeypatch.setattr(music, 'VOICE_IDLE_TIMEOUT', 60)
        await playing()
        await self.leave_all(ctx)
        task = music.idle_disconnects[ctx.guild.id]

        await bot.on_voice_state_update(ctx.author, None, None)

        assert music.idle_disconnects[ctx.guild.id] is task

    async def test_stop_before_timeout(self, ctx, playing, monkeypatch):
        monkeypatch.setattr(music, 'VOICE_IDLE_TIMEOUT', 0.01)
        voice_client = await playing()
        await self.leave_all(ctx)
        task = music.idle_disconnects[ctx.guild.id]

        await run('stop', ctx)
        await task

        voice_client.disconnect.assert_awaited_once()
        assert ctx.guild.id not in music.idle_disconnects

    async def test_update_when_not_connected_is_ignored(self, ctx):
        ctx.author.guild = ctx.guild

        await bot.on_voice_state_update(ctx.author, None, None)

        assert not music.idle_disconnects
