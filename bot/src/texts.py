"""
Access to the user-visible texts and style of the bot, stored in data/messages.json.

The file is reloaded when it changes on disk, so texts can be edited without restarting
the bot. If the new version is invalid, the last valid one is kept.

Usage:
    t('joue.no_url')                  -> "Donne-moi un lien YouTube : `?joue <lien>`"
    t('cherchecitation.no_result', keyword='kant')
    style('queue_preview_size')       -> 10
    colour('error')                   -> discord.Colour
"""

import json
import os

import discord

from config import MESSAGES_FILE, PREFIX
from log import logger

_cache = {'mtime': None, 'data': None}


def validate_messages_json(data):
    """
    Validate the structure of messages.json file.

    Args:
        data: Parsed JSON data from messages.json file

    Returns:
        None

    Raises:
        ValueError: If the JSON structure is invalid

    Expected structure:
        {
            "style": {"colors": {"<name>": "#RRGGBB", ...}, ...},
            "<section>": {"<key>": "text with {placeholders}", ...},
            ...
        }
    """
    if not isinstance(data, dict):
        raise ValueError("Invalid messages.json structure: expected an object of sections")
    colors = data.get('style', {}).get('colors')
    if not isinstance(colors, dict):
        raise ValueError("Invalid messages.json structure: expected {'style': {'colors': {...}}}")
    for name, value in colors.items():
        if not isinstance(value, str) or not value.startswith('#'):
            raise ValueError(f"Invalid color '{name}' in messages.json: expected '#RRGGBB', got {value!r}")
        int(value[1:], 16)


def load_messages():
    """
    Return the content of messages.json, reloading it if the file changed since the last call.

    Returns:
        dict: Parsed messages, or the last valid version if the file is missing or invalid

    Raises:
        RuntimeError: If no valid version has ever been loaded
    """
    try:
        mtime = os.path.getmtime(MESSAGES_FILE)
        if mtime != _cache['mtime']:
            with open(MESSAGES_FILE, 'r', encoding='utf-8') as file:
                data = json.load(file)
            validate_messages_json(data)
            _cache['mtime'], _cache['data'] = mtime, data
            logger.info(f"Loaded messages from {MESSAGES_FILE}")
    except (OSError, ValueError) as e:
        # json.JSONDecodeError is a ValueError
        if _cache['data'] is None:
            raise RuntimeError(f"Cannot load messages file {MESSAGES_FILE}: {e}") from e
        logger.error(f"Cannot reload messages file {MESSAGES_FILE}, keeping the previous version: {e}")
    return _cache['data']


def get(key):
    """
    Get a raw value of messages.json by its dotted key.

    Args:
        key: Dotted path, e.g. "aide.commands" or "style.colors.music"

    Returns:
        The value (str, number, list or dict)

    Raises:
        KeyError: If the key does not exist
    """
    value = load_messages()
    for part in key.split('.'):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(f"Missing key '{key}' in {MESSAGES_FILE}")
        value = value[part]
    return value


def t(key, **kwargs):
    """
    Get a text of messages.json and fill its {placeholders}.

    {prefix} is always available. A missing key or placeholder is logged and never raises,
    so a typo in messages.json cannot break a command.

    Args:
        key: Dotted key of the text, e.g. "joue.no_url"
        **kwargs: Values of the placeholders

    Returns:
        str: The formatted text, or the key itself if it does not exist
    """
    try:
        template = get(key)
    except KeyError as e:
        logger.error(str(e))
        return key
    kwargs.setdefault('prefix', PREFIX)
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError, ValueError) as e:
        logger.error(f"Cannot format text '{key}' of {MESSAGES_FILE}: {e!r}")
        return template


def style(key):
    """
    Get a style value of messages.json (under "style").

    Args:
        key: Dotted key relative to "style", e.g. "queue_preview_size"

    Returns:
        The value
    """
    return get(f'style.{key}')


def colour(name):
    """
    Get an embed colour of messages.json (under "style.colors").

    Args:
        name: Colour name, e.g. "music" or "error"

    Returns:
        discord.Colour
    """
    return discord.Colour(int(style(f'colors.{name}')[1:], 16))
