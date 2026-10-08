"""
Unit tests of views.py: text formatting and embeds, built from the real bot/data/messages.json.

Expected texts are computed with t() rather than hard-coded, so rewording a message
does not break these tests.
"""

from collections import deque
from unittest.mock import MagicMock

import discord
import pytest

import views
from fakes import FakeGuild, FakeMember
from texts import colour, get, style, t


def entry(label='Titre', url=None, duration=None):
    return {'query': label, 'label': label, 'url': url, 'duration': duration}


def field(embed, name_key):
    """Value of the embed field named by the text key, or None."""
    name = t(name_key)
    return next((f.value for f in embed.fields if f.name == name), None)


class TestFormatDuration:
    @pytest.mark.parametrize('seconds, expected', [
        (None, None),
        (0, None),
        (5, '0:05'),
        (65, '1:05'),
        (599, '9:59'),
        (3600, '1:00:00'),
        (3725.9, '1:02:05'),
        (36000, '10:00:00'),
    ])
    def test_formats(self, seconds, expected):
        assert views.format_duration(seconds) == expected


class TestFormatTrackLine:
    def test_plain_label(self):
        assert views.format_track_line('Titre') == 'Titre'

    def test_masked_link(self):
        assert views.format_track_line('Titre', 'https://youtu.be/x') == '[Titre](https://youtu.be/x)'

    def test_duration(self):
        assert views.format_track_line('Titre', 'https://youtu.be/x', 185) == '[Titre](https://youtu.be/x) `3:05`'

    def test_escapes_markdown_and_brackets(self):
        line = views.format_track_line('*Live* [HD]', 'https://youtu.be/x')
        assert line == r'[\*Live\* \[HD\]](https://youtu.be/x)'

    def test_truncates_long_label(self):
        max_length = style('max_label_length')
        line = views.format_track_line('a' * (max_length + 20))
        assert line == 'a' * (max_length - 3) + '...'

    def test_keeps_label_at_max_length(self):
        max_length = style('max_label_length')
        assert views.format_track_line('a' * max_length) == 'a' * max_length


def test_format_quote():
    quote = {'citation': 'Je pense, donc je suis.', 'author': 'René Descartes'}
    assert views.format_quote(quote) == t('common.quote', citation=quote['citation'], author=quote['author'])


def test_help_text_lists_every_command():
    lines = views.help_text().split('\n')
    assert lines[0] == t('aide.title')
    assert lines[-1] == t('aide.footer')
    for command in get('aide.commands'):
        assert t('aide.line', usage=command['usage'], description=command['description']) in lines


class TestSearchResultsText:
    QUOTES = [{'citation': f'Citation {i}', 'author': 'Auteur'} for i in range(1, 6)]

    def test_shows_all_results_under_the_limit(self):
        shown = style('search_results')
        text = views.search_results_text('auteur', self.QUOTES[:shown])
        lines = text.split('\n')
        assert lines[0] == t('cherchecitation.header', keyword='auteur')
        assert len(lines) == 1 + shown
        assert lines[1] == t('cherchecitation.result', index=1, quote=views.format_quote(self.QUOTES[0]))

    def test_announces_hidden_results(self):
        shown = style('search_results')
        lines = views.search_results_text('auteur', self.QUOTES).split('\n')
        assert len(lines) == 1 + shown + 1
        assert lines[-1] == t('cherchecitation.more', count=len(self.QUOTES) - shown)


class TestMessageEmbed:
    def test_music_colour_without_footer(self):
        embed = views.message_embed('Titre passé')
        assert embed.description == 'Titre passé'
        assert embed.colour == colour('music')
        assert embed.footer.text is None

    def test_error_colour(self):
        assert views.message_embed('Erreur', error=True).colour == colour('error')

    def test_author_footer(self):
        author = FakeMember('alice')
        embed = views.message_embed('Arrêté', author=author)
        assert embed.footer.text == t('embeds.done_by', name='alice')
        assert embed.footer.icon_url == author.display_avatar.url


class TestNowPlayingEmbed:
    TRACK = {'title': 'Titre', 'url': 'https://youtu.be/x', 'thumbnail': 'https://i.ytimg.com/x.jpg',
             'duration': 185, 'uploader': 'Chaîne_officielle'}

    def test_full_track(self):
        requester = FakeMember('alice')
        embed = views.now_playing_embed({**self.TRACK, 'requester': requester}, deque())
        assert embed.title == 'Titre'
        assert embed.url == 'https://youtu.be/x'
        assert embed.author.name == t('embeds.now_playing')
        assert embed.thumbnail.url == self.TRACK['thumbnail']
        assert field(embed, 'embeds.duration') == '3:05'
        assert field(embed, 'embeds.channel') == discord.utils.escape_markdown('Chaîne_officielle')
        assert field(embed, 'embeds.up_next') is None
        assert embed.footer.text == t('embeds.requested_by', name='alice')

    def test_minimal_track(self):
        embed = views.now_playing_embed({'title': 'x' * 300}, deque())
        assert len(embed.title) == 256
        assert field(embed, 'embeds.duration') == t('embeds.unknown_duration')
        assert field(embed, 'embeds.channel') is None
        assert embed.thumbnail.url is None
        assert embed.footer.text is None

    def test_next_track(self):
        embed = views.now_playing_embed(self.TRACK, deque([entry('Suivant', 'https://youtu.be/y')]))
        assert field(embed, 'embeds.up_next') == '[Suivant](https://youtu.be/y)'

    def test_next_tracks_count(self):
        queue = deque([entry('Suivant'), entry('Autre'), entry('Encore')])
        embed = views.now_playing_embed(self.TRACK, queue)
        assert field(embed, 'embeds.up_next') == 'Suivant\n' + t('embeds.up_next_more', count=2)


def test_queued_embed():
    track = {**entry('Titre', 'https://youtu.be/x', 65), 'thumbnail': 'https://i.ytimg.com/x.jpg'}
    embed = views.queued_embed(track, 3)
    assert embed.title == 'Titre'
    assert embed.author.name == t('embeds.queued')
    assert field(embed, 'embeds.duration') == '1:05'
    assert field(embed, 'embeds.position') == '3'


class TestPlaylistEmbed:
    PLAYLIST = {'name': 'Viking', 'url': 'https://open.spotify.com/playlist/x', 'thumbnail': None}

    def test_in_order(self):
        tracks = [entry(duration=60), entry(duration=90)]
        playlist = {**self.PLAYLIST, 'thumbnail': 'https://i.scdn.co/image/x'}
        embed = views.playlist_embed(playlist, tracks, 'YouTube', FakeMember('alice'))
        assert embed.title == 'Viking'
        assert embed.thumbnail.url == 'https://i.scdn.co/image/x'
        assert embed.author.name == t('embeds.playlist_added', source='YouTube')
        assert embed.description == t('embeds.playlist_tracks', count=2)
        assert field(embed, 'embeds.total_duration') == '2:30'
        assert embed.footer.text == t('embeds.requested_by', name='alice')

    def test_shuffled_without_durations(self):
        embed = views.playlist_embed(self.PLAYLIST, [entry(), entry()], 'Spotify', None, shuffled=True)
        assert embed.description == t('embeds.playlist_tracks_shuffled', count=2)
        assert field(embed, 'embeds.total_duration') is None


class TestQueueEmbed:
    def test_nothing_playing(self):
        embed = views.queue_embed(FakeGuild(), None, deque())
        assert embed.title == t('embeds.queue_title')
        assert embed.description == t('embeds.queue_empty')
        assert field(embed, 'embeds.queue_current') is None
        assert embed.footer.text == t('embeds.queue_footer', count=0)

    def test_current_and_next_tracks(self):
        current = {'title': 'En cours', 'url': 'https://youtu.be/x', 'duration': 60,
                   'thumbnail': 'https://i.ytimg.com/x.jpg'}
        queue = deque([entry('Un', duration=60), entry('Deux', duration=120)])
        embed = views.queue_embed(FakeGuild(), current, queue)
        assert field(embed, 'embeds.queue_current') == '[En cours](https://youtu.be/x) `1:00`'
        assert embed.thumbnail.url == current['thumbnail']
        assert embed.description.split('\n') == [
            t('embeds.queue_next_header'),
            t('embeds.queue_line', index=1, track='Un `1:00`'),
            t('embeds.queue_line', index=2, track='Deux `2:00`'),
        ]
        assert embed.footer.text == t('embeds.queue_footer_duration', count=2, duration='3:00')

    def test_long_queue_is_truncated(self):
        preview_size = style('queue_preview_size')
        queue = deque(entry(f'Titre {i}') for i in range(preview_size + 5))
        lines = views.queue_embed(FakeGuild(), None, queue).description.split('\n')
        assert len(lines) == 1 + preview_size + 1
        assert lines[-1] == t('embeds.queue_more', count=5)

    def test_guild_icon_as_author(self):
        guild = FakeGuild('Mon serveur')
        guild.icon = MagicMock(url='https://cdn.discordapp.com/icons/1.png')
        embed = views.queue_embed(guild, None, deque())
        assert embed.author.name == 'Mon serveur'
        assert embed.author.icon_url == 'https://cdn.discordapp.com/icons/1.png'
