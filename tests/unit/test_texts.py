"""
Unit tests of texts.py: messages.json validation, hot reload, and the t/get/style/colour helpers.
"""

import json
import logging
import os

import discord
import pytest

import texts

MESSAGES = {
    'style': {'colors': {'music': '#5865F2', 'error': '#ED4245'}, 'queue_preview_size': 10},
    'joue': {'no_url': 'Donne-moi un lien : `{prefix}joue <lien>`'},
    'cherchecitation': {'no_result': "Aucune citation trouvée pour '{keyword}'."},
    'aide': {'commands': [{'usage': 'aide', 'description': 'Aide'}]},
}


@pytest.fixture
def messages_file(tmp_path, monkeypatch):
    """
    Point texts.py to a temporary messages.json.

    Returns:
        callable: write(data) writing parsed JSON data or a raw string, with a new mtime on each call
    """
    path = tmp_path / 'messages.json'
    monkeypatch.setattr(texts, 'MESSAGES_FILE', str(path))
    mtime = [1_700_000_000]

    def write(data):
        path.write_text(data if isinstance(data, str) else json.dumps(data), encoding='utf-8')
        # Explicit mtimes: two writes in the same filesystem tick would otherwise look unchanged
        mtime[0] += 10
        os.utime(path, (mtime[0], mtime[0]))
        return path

    return write


class TestValidateMessagesJson:
    def test_accepts_valid_structure(self):
        texts.validate_messages_json(MESSAGES)

    @pytest.mark.parametrize('data', [
        None,
        [],
        {},
        {'style': {}},
        {'style': 'x'},
        {'style': None},
        {'style': {'colors': ['#5865F2']}},
        {'style': {'colors': {'music': 5865}}},
        {'style': {'colors': {'music': '5865F2'}}},
        {'style': {'colors': {'music': '#GGGGGG'}}},
    ])
    def test_rejects_invalid_structure(self, data):
        # load_messages only catches ValueError (and OSError) to keep the previous version
        with pytest.raises(ValueError):
            texts.validate_messages_json(data)


class TestLoadMessages:
    def test_loads_file(self, messages_file):
        messages_file(MESSAGES)
        assert texts.load_messages() == MESSAGES

    def test_uses_cache_while_file_is_unchanged(self, messages_file, monkeypatch):
        messages_file(MESSAGES)
        texts.load_messages()

        def fail_open(*args, **kwargs):
            raise AssertionError('messages.json should not be read again')

        monkeypatch.setattr('builtins.open', fail_open)
        assert texts.load_messages() == MESSAGES

    def test_reloads_when_file_changes(self, messages_file):
        messages_file(MESSAGES)
        texts.load_messages()
        changed = {**MESSAGES, 'joue': {'no_url': 'Nouveau texte'}}
        messages_file(changed)
        assert texts.load_messages() == changed

    @pytest.mark.parametrize('broken', ['{"style": ', json.dumps({'style': {}}), json.dumps({'style': 'x'})])
    def test_keeps_previous_version_if_new_one_is_invalid(self, messages_file, caplog, broken):
        messages_file(MESSAGES)
        texts.load_messages()
        messages_file(broken)
        with caplog.at_level(logging.ERROR, logger='botghast'):
            assert texts.load_messages() == MESSAGES
        assert 'keeping the previous version' in caplog.text

    def test_keeps_previous_version_if_file_is_deleted(self, messages_file):
        path = messages_file(MESSAGES)
        texts.load_messages()
        path.unlink()
        assert texts.load_messages() == MESSAGES

    def test_missing_file_without_previous_version_raises(self, messages_file):
        with pytest.raises(RuntimeError):
            texts.load_messages()

    def test_invalid_file_without_previous_version_raises(self, messages_file):
        messages_file('{"style": ')
        with pytest.raises(RuntimeError):
            texts.load_messages()


class TestGet:
    def test_returns_nested_value(self, messages_file):
        messages_file(MESSAGES)
        assert texts.get('style.colors.music') == '#5865F2'
        assert texts.get('aide.commands') == MESSAGES['aide']['commands']

    @pytest.mark.parametrize('key', ['missing', 'joue.missing', 'joue.no_url.deeper'])
    def test_missing_key_raises(self, messages_file, key):
        messages_file(MESSAGES)
        with pytest.raises(KeyError):
            texts.get(key)


class TestT:
    def test_fills_placeholders(self, messages_file):
        messages_file(MESSAGES)
        assert texts.t('cherchecitation.no_result', keyword='kant') == "Aucune citation trouvée pour 'kant'."

    def test_prefix_is_always_available(self, messages_file):
        messages_file(MESSAGES)
        assert texts.t('joue.no_url') == 'Donne-moi un lien : `?joue <lien>`'

    def test_missing_key_returns_key_and_logs(self, messages_file, caplog):
        messages_file(MESSAGES)
        with caplog.at_level(logging.ERROR, logger='botghast'):
            assert texts.t('joue.unknown') == 'joue.unknown'
        assert "Missing key 'joue.unknown'" in caplog.text

    def test_missing_placeholder_returns_template_and_logs(self, messages_file, caplog):
        messages_file(MESSAGES)
        with caplog.at_level(logging.ERROR, logger='botghast'):
            assert texts.t('cherchecitation.no_result') == MESSAGES['cherchecitation']['no_result']
        assert "Cannot format text 'cherchecitation.no_result'" in caplog.text

    def test_broken_template_returns_template(self, messages_file):
        messages_file({**MESSAGES, 'joue': {'no_url': 'Accolade non fermée {'}})
        assert texts.t('joue.no_url') == 'Accolade non fermée {'


class TestStyleAndColour:
    def test_style_reads_under_style_section(self, messages_file):
        messages_file(MESSAGES)
        assert texts.style('queue_preview_size') == 10

    def test_colour_returns_discord_colour(self, messages_file):
        messages_file(MESSAGES)
        assert texts.colour('music') == discord.Colour(0x5865F2)
        assert texts.colour('error') == discord.Colour(0xED4245)
