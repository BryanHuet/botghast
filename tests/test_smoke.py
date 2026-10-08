"""
Smoke tests: the test setup itself works (isolated config, bot importable, fakes usable).
"""

import config
import texts
from fakes import FakeCtx

EXPECTED_COMMANDS = {'aide', 'donneavis', 'citation', 'cherchecitation',
                     'joue', 'viking', 'suivant', 'file', 'stop'}


def test_config_uses_test_environment():
    assert config.DISCORD_TOKEN == 'test-token'
    assert config.QUOTES_FILE.endswith('tests/fixtures/quotes.json')
    assert config.GIFS_FILE.endswith('tests/fixtures/gifs.json')
    assert not config.SPOTIFY_CLIENT_ID


def test_bot_imports_and_registers_all_commands():
    import bot

    # discord.py adds its own "help" command
    assert {command.name for command in bot.bot.commands} - {'help'} == EXPECTED_COMMANDS


def test_real_messages_file_loads():
    assert texts.load_messages()['style']['colors']


async def test_command_runs_with_fake_context():
    import bot

    ctx = FakeCtx()
    await bot.bot.get_command('citation').callback(ctx)

    ctx.reply.assert_not_awaited()
    ctx.send.assert_awaited_once()
    assert ' ~ ' in ctx.send.await_args.args[0]


async def test_data_files_fixture_redirects_commands(data_files):
    import bot

    data_files(quotes=[{'citation': 'Connais-toi toi-même.', 'author': 'Socrate'}])
    ctx = FakeCtx()
    await bot.bot.get_command('citation').callback(ctx)

    ctx.send.assert_awaited_once_with(texts.t('common.quote', citation='Connais-toi toi-même.', author='Socrate'))
