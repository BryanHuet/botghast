"""
Functional tests of the text commands (aide, citation, cherchecitation, donneavis).

Each command is run through its registered callback with fake discord objects, and the
test checks what the bot replied or sent. Expected texts are computed with t() and the
views helpers rather than hard-coded, so rewording a message does not break these tests.
"""

from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

import bot
from fakes import FakeCtx, FakeTextChannel
from texts import style, t
from views import format_quote, help_text

QUOTES = [
    {"citation": "Penser, c'est dire non.", "author": "Alain"},
    {"citation": "Je pense, donc je suis.", "author": "René Descartes"},
    {"citation": "L'enfer, c'est les autres.", "author": "Jean-Paul Sartre"},
]
GIFS = {"gifs": ["https://tenor.com/view/test-gif-1"]}


async def run(name, ctx, *args, **kwargs):
    """Run a registered command as discord.py would, without the parsing step."""
    await bot.bot.get_command(name).callback(ctx, *args, **kwargs)


def http_error(cls, status):
    """Build a discord.HTTPException subclass as raised by the API client."""
    return cls(MagicMock(status=status, reason='error'), 'error')


def only_message(mock):
    """Text of the single message sent through an AsyncMock (ctx.reply, ctx.send...)."""
    mock.assert_awaited_once()
    return mock.await_args.args[0]


@pytest.fixture(params=['guild', 'dm'])
def ctx(request):
    """A command context, on a server and in a direct message."""
    return FakeCtx() if request.param == 'guild' else FakeCtx(guild=None)


class TestAide:
    async def test_sends_help_text(self, ctx):
        await run('aide', ctx)

        assert only_message(ctx.send) == help_text()
        ctx.reply.assert_not_awaited()

    async def test_help_lists_every_text_command(self, ctx):
        await run('aide', ctx)

        text = only_message(ctx.send)
        for usage in ('donneavis', 'citation', 'cherchecitation'):
            assert usage in text


class TestCitation:
    async def test_sends_a_quote_of_the_file(self, ctx, data_files):
        data_files(quotes=QUOTES)

        await run('citation', ctx)

        assert only_message(ctx.send) in [format_quote(quote) for quote in QUOTES]
        ctx.reply.assert_not_awaited()

    async def test_picks_randomly(self, ctx, data_files, monkeypatch):
        data_files(quotes=QUOTES)
        monkeypatch.setattr(bot.random, 'choice', lambda items: items[-1])

        await run('citation', ctx)

        assert only_message(ctx.send) == format_quote(QUOTES[-1])

    async def test_file_missing(self, ctx, data_files):
        data_files()  # paths set, nothing written

        await run('citation', ctx)

        assert only_message(ctx.reply) == t('common.quotes_file_missing')
        ctx.send.assert_not_awaited()

    async def test_empty_file(self, ctx, data_files):
        data_files(quotes=[])

        await run('citation', ctx)

        assert only_message(ctx.reply) == t('common.no_quotes')

    @pytest.mark.parametrize('content', ['{not json', '{"citation": "x"}', '[{"citation": "sans auteur"}]'])
    async def test_invalid_file(self, ctx, data_files, content):
        data_files(quotes=content)

        await run('citation', ctx)

        assert only_message(ctx.reply) == t('citation.json_error')
        ctx.send.assert_not_awaited()

    async def test_unexpected_error(self, ctx, data_files, monkeypatch):
        data_files(quotes=QUOTES)

        def broken():
            raise OSError('disk error')
        monkeypatch.setattr(bot, 'load_quotes', broken)

        await run('citation', ctx)

        assert only_message(ctx.reply) == t('citation.error')

    async def test_silent_when_bot_cannot_send(self, data_files):
        data_files(quotes=QUOTES)
        ctx = FakeCtx(channel=FakeTextChannel(can_send=False))

        await run('citation', ctx)

        ctx.send.assert_not_awaited()
        ctx.reply.assert_not_awaited()


class TestChercheCitation:
    @pytest.mark.parametrize('keyword', [None, ''])
    async def test_no_keyword(self, ctx, data_files, keyword):
        data_files(quotes=QUOTES)

        await run('cherchecitation', ctx, keyword=keyword)

        assert only_message(ctx.reply) == t('cherchecitation.no_keyword')
        ctx.send.assert_not_awaited()

    async def test_no_result(self, ctx, data_files):
        data_files(quotes=QUOTES)

        await run('cherchecitation', ctx, keyword='Nietzsche')

        assert only_message(ctx.reply) == t('cherchecitation.no_result', keyword='Nietzsche')
        ctx.send.assert_not_awaited()

    async def test_match_in_citation_is_case_insensitive(self, ctx, data_files):
        data_files(quotes=QUOTES)

        await run('cherchecitation', ctx, keyword='ENFER')

        text = only_message(ctx.send)
        assert text.splitlines() == [
            t('cherchecitation.header', keyword='ENFER'),
            t('cherchecitation.result', index=1, quote=format_quote(QUOTES[2])),
        ]

    async def test_match_on_author(self, ctx, data_files):
        data_files(quotes=QUOTES)

        await run('cherchecitation', ctx, keyword='descartes')

        text = only_message(ctx.send)
        assert t('cherchecitation.result', index=1, quote=format_quote(QUOTES[1])) in text
        assert format_quote(QUOTES[0]) not in text

    async def test_results_are_limited(self, ctx, data_files):
        shown = style('search_results')
        quotes = [{"citation": f"Sagesse numéro {i}", "author": f"Auteur {i}"} for i in range(shown + 2)]
        data_files(quotes=quotes)

        await run('cherchecitation', ctx, keyword='sagesse')

        lines = only_message(ctx.send).splitlines()
        assert lines == (
            [t('cherchecitation.header', keyword='sagesse')]
            + [t('cherchecitation.result', index=i + 1, quote=format_quote(quotes[i])) for i in range(shown)]
            + [t('cherchecitation.more', count=2)]
        )

    async def test_exactly_the_limit_has_no_more_line(self, ctx, data_files):
        shown = style('search_results')
        quotes = [{"citation": f"Sagesse numéro {i}", "author": "X"} for i in range(shown)]
        data_files(quotes=quotes)

        await run('cherchecitation', ctx, keyword='sagesse')

        assert len(only_message(ctx.send).splitlines()) == shown + 1

    async def test_file_missing(self, ctx, data_files):
        data_files()

        await run('cherchecitation', ctx, keyword='pense')

        assert only_message(ctx.reply) == t('common.quotes_file_missing')

    async def test_empty_file(self, ctx, data_files):
        data_files(quotes=[])

        await run('cherchecitation', ctx, keyword='pense')

        assert only_message(ctx.reply) == t('common.no_quotes')

    async def test_invalid_file(self, ctx, data_files):
        data_files(quotes='{not json')

        await run('cherchecitation', ctx, keyword='pense')

        assert only_message(ctx.reply) == t('cherchecitation.error')
        ctx.send.assert_not_awaited()


class TestDonneAvis:
    REFERENCE_ID = 1234

    @pytest.fixture(params=['guild', 'dm'])
    def ctx(self, request):
        """A context replying to message REFERENCE_ID, on a server and in a direct message."""
        guild = {} if request.param == 'guild' else {'guild': None}
        return FakeCtx(reference_id=self.REFERENCE_ID, **guild)

    @pytest.fixture
    def referenced(self, ctx):
        """The message the command replies to, as returned by channel.fetch_message."""
        message = MagicMock()
        message.reply = AsyncMock()
        ctx.channel.fetch_message.return_value = message
        return message

    async def test_replies_to_referenced_message_with_a_gif(self, ctx, data_files, referenced):
        data_files(gifs=GIFS)

        await run('donneavis', ctx)

        ctx.channel.fetch_message.assert_awaited_once_with(self.REFERENCE_ID)
        assert only_message(referenced.reply) == t('donneavis.response', gif=GIFS['gifs'][0])
        ctx.reply.assert_not_awaited()
        ctx.send.assert_not_awaited()

    async def test_no_reference(self, data_files):
        data_files(gifs=GIFS)
        ctx = FakeCtx()

        await run('donneavis', ctx)

        assert only_message(ctx.reply) == t('donneavis.no_reference')
        ctx.channel.fetch_message.assert_not_awaited()

    async def test_gifs_file_missing(self, ctx, data_files, referenced):
        data_files()

        await run('donneavis', ctx)

        assert only_message(ctx.reply) == t('donneavis.gifs_file_missing')
        referenced.reply.assert_not_awaited()

    @pytest.mark.parametrize('error, key', [
        (http_error(discord.NotFound, 404), 'donneavis.reference_not_found'),
        (http_error(discord.Forbidden, 403), 'donneavis.reference_forbidden'),
        (http_error(discord.HTTPException, 500), 'donneavis.reference_error'),
        (RuntimeError('boom'), 'donneavis.reference_error'),
    ])
    async def test_fetch_errors(self, ctx, data_files, error, key):
        data_files(gifs=GIFS)
        ctx.channel.fetch_message.side_effect = error

        await run('donneavis', ctx)

        assert only_message(ctx.reply) == t(key)
        ctx.send.assert_not_awaited()

    async def test_referenced_message_inaccessible(self, ctx, data_files):
        data_files(gifs=GIFS)
        ctx.channel.fetch_message.return_value = None

        await run('donneavis', ctx)

        assert only_message(ctx.reply) == t('donneavis.reference_inaccessible')

    @pytest.mark.parametrize('gifs', [{'gifs': []}, '{not json', '{"gifs": "pas une liste"}'])
    async def test_unusable_gifs_file(self, ctx, data_files, referenced, gifs):
        data_files(gifs=gifs)

        await run('donneavis', ctx)

        assert only_message(ctx.send) == t('donneavis.error')
        referenced.reply.assert_not_awaited()

    async def test_reply_fails(self, ctx, data_files, referenced):
        data_files(gifs=GIFS)
        referenced.reply.side_effect = http_error(discord.Forbidden, 403)

        await run('donneavis', ctx)

        assert only_message(ctx.send) == t('donneavis.error')
