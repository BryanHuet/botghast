"""
Loading and validation of the bot data files (GIFs and quotes).

Files are read again on every call, so data changes do not require a restart.
"""

import json

from config import GIFS_FILE, QUOTES_FILE
from log import logger


def validate_gifs_json(data):
    """
    Validate the structure of gifs.json file.

    Args:
        data: Parsed JSON data from gifs.json file

    Returns:
        None

    Raises:
        ValueError: If the JSON structure is invalid

    Expected structure:
        {
            "gifs": ["gif_url_1", "gif_url_2", ...]
        }
    """
    logger.debug("Validating GIFs JSON structure")
    if not isinstance(data, dict) or 'gifs' not in data:
        logger.error("Invalid gifs.json structure: expected {'gifs': [...]}")
        raise ValueError("Invalid gifs.json structure: expected {'gifs': [...]}")
    if not isinstance(data['gifs'], list):
        logger.error("Invalid gifs.json structure: 'gifs' should be an array")
        raise ValueError("Invalid gifs.json structure: 'gifs' should be an array")
    logger.info(f"Successfully validated {len(data['gifs'])} GIFs")


def validate_quotes_json(data):
    """
    Validate the structure of quotes.json file.

    Args:
        data: Parsed JSON data from quotes.json file

    Returns:
        None

    Raises:
        ValueError: If the JSON structure is invalid

    Expected structure:
        [
            {
                "citation": "quote text",
                "author": "author name"
            },
            ...
        ]
    """
    logger.debug("Validating quotes JSON structure")
    if not isinstance(data, list):
        logger.error("Invalid quotes.json structure: expected array of quotes")
        raise ValueError("Invalid quotes.json structure: expected array of quotes")
    for quote in data:
        if not isinstance(quote, dict) or 'citation' not in quote or 'author' not in quote:
            logger.error(f"Invalid quote structure: {quote}")
            raise ValueError(f"Invalid quote structure: {quote}")
    logger.info(f"Successfully validated {len(data)} quotes")


def load_gifs():
    """
    Read and validate the GIFs file.

    Returns:
        list: GIF URLs

    Raises:
        OSError, json.JSONDecodeError, ValueError: If the file cannot be read or is invalid
    """
    logger.debug(f"Loading GIFs from file: {GIFS_FILE}")
    with open(GIFS_FILE, 'r', encoding='utf-8') as file:
        data = json.load(file)
    validate_gifs_json(data)
    return data['gifs']


def load_quotes():
    """
    Read and validate the quotes file.

    Returns:
        list: {'citation', 'author'} dicts

    Raises:
        OSError, json.JSONDecodeError, ValueError: If the file cannot be read or is invalid
    """
    logger.debug(f"Loading quotes from file: {QUOTES_FILE}")
    with open(QUOTES_FILE, 'r', encoding='utf-8') as file:
        data = json.load(file)
    validate_quotes_json(data)
    return data
