"""Validate BotGhast data files and report duplicates.

Usage: python .claude/skills/manage-data/scripts/validate_data.py [gifs.json] [quotes.json]
Defaults to bot/data/gifs.json and bot/data/quotes.json (run from repo root).
Exit code 1 if a structural error is found; duplicates are only warnings.
"""
import json
import sys
from collections import Counter


def load(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def check_gifs(path):
    errors = []
    data = load(path)
    if not isinstance(data, dict) or not isinstance(data.get('gifs'), list):
        return [f"{path}: expected {{'gifs': [...]}}"]
    for i, url in enumerate(data['gifs']):
        if not isinstance(url, str) or not url.startswith('http'):
            errors.append(f"{path}: gifs[{i}] is not an http(s) URL: {url!r}")
    for url, n in Counter(data['gifs']).items():
        if n > 1:
            print(f"WARN {path}: duplicate GIF x{n}: {url}")
    print(f"OK   {path}: {len(data['gifs'])} gifs")
    return errors


def check_quotes(path):
    errors = []
    data = load(path)
    if not isinstance(data, list):
        return [f"{path}: expected a list of quotes"]
    for i, q in enumerate(data):
        if not isinstance(q, dict) or not {'citation', 'author'} <= q.keys():
            errors.append(f"{path}: [{i}] missing 'citation' or 'author': {q!r}")
        elif not str(q['citation']).strip() or not str(q['author']).strip():
            errors.append(f"{path}: [{i}] empty citation or author")
    keys = Counter(q.get('citation', '').strip().lower() for q in data if isinstance(q, dict))
    for c, n in keys.items():
        if n > 1:
            print(f"WARN {path}: duplicate quote x{n}: {c}")
    print(f"OK   {path}: {len(data)} quotes")
    return errors


if __name__ == '__main__':
    gifs = sys.argv[1] if len(sys.argv) > 1 else 'bot/data/gifs.json'
    quotes = sys.argv[2] if len(sys.argv) > 2 else 'bot/data/quotes.json'
    errs = check_gifs(gifs) + check_quotes(quotes)
    for e in errs:
        print(f"ERR  {e}")
    sys.exit(1 if errs else 0)
