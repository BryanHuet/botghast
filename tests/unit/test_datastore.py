"""
Unit tests of datastore.py: structure validation and loading of the GIFs and quotes files.
"""

import json

import pytest

import datastore

VALID_QUOTES = [
    {'citation': "Penser, c'est dire non.", 'author': 'Alain'},
    {'citation': 'Je pense, donc je suis.', 'author': 'René Descartes'},
]


class TestValidateGifsJson:
    @pytest.mark.parametrize('data', [
        {'gifs': []},
        {'gifs': ['https://tenor.com/view/a', 'https://tenor.com/view/b']},
    ])
    def test_accepts_valid_structure(self, data):
        datastore.validate_gifs_json(data)

    @pytest.mark.parametrize('data', [
        None,
        [],
        ['https://tenor.com/view/a'],
        {},
        {'gif': []},
        {'gifs': 'https://tenor.com/view/a'},
        {'gifs': {'url': 'https://tenor.com/view/a'}},
    ])
    def test_rejects_invalid_structure(self, data):
        with pytest.raises(ValueError):
            datastore.validate_gifs_json(data)


class TestValidateQuotesJson:
    @pytest.mark.parametrize('data', [
        [],
        VALID_QUOTES,
        [{'citation': 'x', 'author': 'y', 'source': 'extra keys are allowed'}],
    ])
    def test_accepts_valid_structure(self, data):
        datastore.validate_quotes_json(data)

    @pytest.mark.parametrize('data', [
        None,
        {},
        {'quotes': VALID_QUOTES},
        ['Penser, c\'est dire non.'],
        [{'citation': 'sans auteur'}],
        [{'author': 'sans citation'}],
        VALID_QUOTES + [None],
    ])
    def test_rejects_invalid_structure(self, data):
        with pytest.raises(ValueError):
            datastore.validate_quotes_json(data)


class TestLoadGifs:
    def test_returns_gif_list(self, data_files):
        data_files(gifs={'gifs': ['https://tenor.com/view/a']})
        assert datastore.load_gifs() == ['https://tenor.com/view/a']

    def test_missing_file_raises(self, data_files):
        data_files()
        with pytest.raises(FileNotFoundError):
            datastore.load_gifs()

    def test_broken_json_raises(self, data_files):
        data_files(gifs='{"gifs": [')
        with pytest.raises(json.JSONDecodeError):
            datastore.load_gifs()

    def test_invalid_structure_raises(self, data_files):
        data_files(gifs=['https://tenor.com/view/a'])
        with pytest.raises(ValueError):
            datastore.load_gifs()


class TestLoadQuotes:
    def test_returns_quotes_with_accents(self, data_files):
        data_files(quotes=VALID_QUOTES)
        assert datastore.load_quotes() == VALID_QUOTES

    def test_reads_file_again_on_each_call(self, data_files):
        paths = data_files(quotes=VALID_QUOTES)
        datastore.load_quotes()
        paths['quotes'].write_text(json.dumps(VALID_QUOTES[:1]), encoding='utf-8')
        assert datastore.load_quotes() == VALID_QUOTES[:1]

    def test_missing_file_raises(self, data_files):
        data_files()
        with pytest.raises(FileNotFoundError):
            datastore.load_quotes()

    def test_broken_json_raises(self, data_files):
        data_files(quotes='[{"citation": ')
        with pytest.raises(json.JSONDecodeError):
            datastore.load_quotes()

    def test_invalid_structure_raises(self, data_files):
        data_files(quotes=[{'citation': 'sans auteur'}])
        with pytest.raises(ValueError):
            datastore.load_quotes()
