"""
Lightweight stand-ins for the discord.py objects used by the commands.

Only what the bot actually reads or calls is implemented. Coroutine methods are
AsyncMock objects, so tests can assert on what the bot replied or sent:

    ctx = FakeCtx()
    await bot.get_command('citation').callback(ctx)
    ctx.send.assert_awaited_once()
"""

import itertools
from unittest.mock import AsyncMock, MagicMock

_ids = itertools.count(1)


class FakeMember:
    def __init__(self, name='alice', bot=False, voice_channel=None):
        self.id = next(_ids)
        self.name = name
        self.display_name = name
        self.mention = f'<@{self.id}>'
        self.bot = bot
        self.display_avatar = MagicMock(url=f'https://cdn.discordapp.com/avatars/{self.id}.png')
        self.voice = FakeVoiceState(voice_channel) if voice_channel else None

    def __str__(self):
        return self.name


class FakeVoiceState:
    def __init__(self, channel):
        self.channel = channel


class FakeVoiceChannel:
    def __init__(self, name='Général', members=None):
        self.id = next(_ids)
        self.name = name
        self.members = members if members is not None else []
        self.guild = None
        self.connect = AsyncMock(side_effect=self._connect)

    async def _connect(self):
        voice_client = FakeVoiceClient(self)
        if self.guild:
            self.guild.voice_client = voice_client
        return voice_client

    def __str__(self):
        return self.name


class FakeTextChannel:
    def __init__(self, name='général', can_send=True):
        self.id = next(_ids)
        self.name = name
        self.send = AsyncMock()
        self.fetch_message = AsyncMock()
        self._can_send = can_send

    def permissions_for(self, member):
        return MagicMock(send_messages=self._can_send)

    def __str__(self):
        return self.name


class FakeVoiceClient:
    """
    Voice client that plays nothing: play() keeps the after callback so a test can
    end the track with finish().
    """

    def __init__(self, channel):
        self.channel = channel
        self.source = None
        self.after = None
        self._playing = False
        self._paused = False
        self._connected = True
        self.disconnect = AsyncMock(side_effect=self._disconnect)
        self.move_to = AsyncMock(side_effect=self._move_to)

    def play(self, source, after=None):
        self.source, self.after = source, after
        self._playing = True

    def stop(self):
        self.finish()

    def finish(self, error=None):
        """Simulate the end of the current track, as the audio thread does."""
        was_playing, self._playing, self._paused = self._playing, False, False
        if was_playing and self.after:
            self.after(error)

    def is_playing(self):
        return self._playing

    def is_paused(self):
        return self._paused

    def is_connected(self):
        return self._connected

    async def _disconnect(self, force=False):
        self._connected = False
        self._playing = False
        if self.channel.guild:
            self.channel.guild.voice_client = None

    async def _move_to(self, channel):
        self.channel = channel


class FakeGuild:
    def __init__(self, name='Serveur de test'):
        self.id = next(_ids)
        self.name = name
        self.icon = None
        self.voice_client = None

    def add_voice_channel(self, name='Général', members=None):
        channel = FakeVoiceChannel(name, members)
        channel.guild = self
        return channel

    def __str__(self):
        return self.name


class _Typing:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeCtx:
    """
    Command context. Pass guild=None to simulate a direct message.

    Args:
        author: FakeMember invoking the command (default: a new member, not in voice)
        guild: FakeGuild, or None for a direct message (default: a new guild)
        channel: FakeTextChannel where the command was sent
        reference_id: ID of the message the command replies to, if any
    """

    _NO_GUILD = object()

    def __init__(self, author=None, guild=_NO_GUILD, channel=None, reference_id=None, command=None):
        self.author = author or FakeMember()
        self.guild = FakeGuild() if guild is FakeCtx._NO_GUILD else guild
        self.channel = channel or FakeTextChannel()
        self.me = FakeMember('BotGhast', bot=True)
        self.command = command
        self.message = MagicMock()
        self.message.channel = self.channel
        self.message.reference = MagicMock(message_id=reference_id) if reference_id else None
        self.reply = AsyncMock()
        self.send = AsyncMock()

    @property
    def voice_client(self):
        return self.guild.voice_client if self.guild else None

    def typing(self):
        return _Typing()
