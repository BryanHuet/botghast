"""
Contract tests: the code, the texts of bot/data/messages.json, the README and the real
data files stay consistent with each other.

The source code is read with ast rather than run, so a text used in a branch no test
reaches is checked as well.
"""

import ast
import json
import re
import string
from pathlib import Path

import pytest

import bot
import datastore
import texts

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / 'bot' / 'src'
DATA_DIR = ROOT / 'bot' / 'data'
README = ROOT / 'README.md'

# discord.py adds its own "help" command, replaced by "aide" for the users
BUILTIN_COMMANDS = {'help'}


def load_json(name):
    with open(DATA_DIR / name, encoding='utf-8') as file:
        return json.load(file)


MESSAGES = load_json('messages.json')


def lookup(key):
    """Value of a dotted key of messages.json, or None if it does not exist."""
    value = MESSAGES
    for part in key.split('.'):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def placeholders(text):
    """Names of the {placeholders} of a text."""
    return {name.split('.')[0].split('[')[0]
            for _, name, _, _ in string.Formatter().parse(text) if name}


def literal_values(node):
    """String values an expression can take: a literal, or a conditional between literals."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.IfExp):
        return literal_values(node.body) + literal_values(node.orelse)
    return []


def text_calls():
    """
    Every call to texts.t / get / style / colour with a literal key (or a choice of literals) in bot/src.

    Returns:
        list: (location, function name, key, keyword argument names or None if **kwargs is used)
    """
    calls = []
    for path in sorted(SRC_DIR.glob('*.py')):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id in ('t', 'get', 'style', 'colour') and node.args):
                continue
            names = {kw.arg for kw in node.keywords}
            for key in literal_values(node.args[0]):
                calls.append((f'{path.name}:{node.lineno}', node.func.id, key,
                              None if None in names else names))
    return calls


def text_key_literals():
    """
    Every string literal of bot/src shaped like a key of a messages.json section ("section.key").

    Catches keys chosen in a variable before being passed to t(), e.g.
    key = 'embeds.playlist_tracks_shuffled' if shuffled else 'embeds.playlist_tracks'.
    """
    sections = {name for name, value in MESSAGES.items() if isinstance(value, dict)}
    literals = []
    for path in sorted(SRC_DIR.glob('*.py')):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and re.fullmatch(r'[a-z_]+\.[a-z_.]+', node.value)
                    and node.value.split('.')[0] in sections):
                literals.append((f'{path.name}:{node.lineno}', node.value))
    return literals


CALLS = text_calls()


def call_id(call):
    return f'{call[0]} {call[1]}({call[2]!r})'


class TestTexts:
    def test_calls_are_found(self):
        # Guard against an ast walk that silently finds nothing
        assert len([c for c in CALLS if c[1] == 't']) > 50

    @pytest.mark.parametrize('call', CALLS, ids=call_id)
    def test_key_exists(self, call):
        _, function, key, _ = call
        full_key = {'style': f'style.{key}', 'colour': f'style.colors.{key}'}.get(function, key)

        assert lookup(full_key) is not None, f'{full_key!r} is missing from messages.json'

    @pytest.mark.parametrize('location, key', text_key_literals(), ids=lambda v: str(v))
    def test_indirect_key_exists(self, location, key):
        assert lookup(key) is not None, f'{key!r} ({location}) is missing from messages.json'

    @pytest.mark.parametrize('call', [c for c in CALLS if c[1] == 't' and c[3] is not None], ids=call_id)
    def test_placeholders_are_provided(self, call):
        _, _, key, given = call
        text = lookup(key)
        if not isinstance(text, str):
            pytest.skip(f'{key!r} is missing (reported by test_key_exists)')

        assert placeholders(text) - {'prefix'} == given

    def test_every_text_is_used(self):
        texts_in_file = {f'{section}.{name}'
                         for section, values in MESSAGES.items() if section != 'style'
                         for name, value in values.items() if isinstance(value, str)}
        used = {key for _, function, key, _ in CALLS if function == 't'}
        used |= {key for _, key in text_key_literals()}

        assert texts_in_file - used == set()

    def test_every_style_value_is_used(self):
        in_file = {f'style.{name}' for name in MESSAGES['style'] if name != 'colors'}
        in_file |= {f'style.colors.{name}' for name in MESSAGES['style']['colors']}
        used = {f'style.{key}' for _, function, key, _ in CALLS if function == 'style'}
        used |= {f'style.colors.{key}' for _, function, key, _ in CALLS if function == 'colour'}

        assert in_file - used == set()


def registered_commands():
    return {command.name for command in bot.bot.commands} - BUILTIN_COMMANDS


class TestCommands:
    def test_aide_lists_exactly_the_registered_commands(self):
        listed = {command['usage'].split()[0] for command in MESSAGES['aide']['commands']}

        assert listed == registered_commands()

    def test_readme_lists_exactly_the_registered_commands(self):
        documented = set(re.findall(r'^\| `\?(\w+)', README.read_text(encoding='utf-8'), re.MULTILINE))

        assert documented == registered_commands()

    def test_aliases_do_not_clash(self):
        names = [name for command in bot.bot.commands for name in (command.name, *command.aliases)]

        assert len(names) == len(set(names))


class TestDataFiles:
    def test_messages_file_is_valid(self):
        texts.validate_messages_json(MESSAGES)

    def test_gifs_file_is_valid(self):
        data = load_json('gifs.json')
        datastore.validate_gifs_json(data)

        assert data['gifs'], 'gifs.json is empty: donneavis would always fail'
        assert all(isinstance(gif, str) and gif.startswith('https://') for gif in data['gifs'])
        assert len(data['gifs']) == len(set(data['gifs'])), 'duplicate GIFs'

    def test_quotes_file_is_valid(self):
        data = load_json('quotes.json')
        datastore.validate_quotes_json(data)

        assert data, 'quotes.json is empty: citation would always fail'
        assert all(isinstance(q['citation'], str) and q['citation'].strip()
                   and isinstance(q['author'], str) and q['author'].strip() for q in data)
        citations = [q['citation'].strip().lower() for q in data]
        assert len(citations) == len(set(citations)), 'duplicate quotes'
