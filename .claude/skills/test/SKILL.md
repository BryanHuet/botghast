---
name: test
description: Lancer et écrire les tests pytest de BotGhast (unitaires, fonctionnels, contrats) comme la CI, avec couverture et vérification Python 3.10. À utiliser après une modification du code ou des textes, avant un commit/PR, ou pour ajouter des tests à une commande.
---

# Tests BotGhast

## Lancer

```bash
venv/bin/pip install -r requirements-dev.txt   # une fois
venv/bin/pytest                                # tout, sans réseau ni token Discord (~2 s)
venv/bin/pytest --cov                          # comme la CI : couverture, échoue sous 95 %
venv/bin/pytest tests/functional -k joue       # un sous-ensemble (sans --cov, sinon le seuil échoue)
venv/bin/pytest -m network                     # tests marqués réseau (exclus par défaut)
```

Dans la CI, une étape par type de test (`Unit tests` = tout `tests/` sauf `functional/` et `contract/`, `Functional tests`, `Contract tests`) cumule la couverture, puis l'étape `Coverage` (`coverage report`) applique le seuil de 95 %.

La CI tourne aussi en **Python 3.10** : avant une PR, le vérifier avec un venv jetable dans le scratchpad :

```bash
uv venv -p 3.10 <scratchpad>/py310
VIRTUAL_ENV=<scratchpad>/py310 uv pip install -r requirements.txt -r requirements-dev.txt
<scratchpad>/py310/bin/python -m pytest -q
```

Puis `/lint` (flake8 sur `bot` **et** `tests`).

## Où écrire un test

| Dossier | Quoi | Exemple |
|---|---|---|
| `tests/unit/` | une fonction d'un module, dépendances mockées | `test_views.py`, `test_spotify_client.py` (aioresponses) |
| `tests/functional/` | une commande de bout en bout avec les faux objets Discord | `test_cmd_text.py`, `test_cmd_music.py`, `test_music_flow.py` |
| `tests/contract/` | cohérence code / `messages.json` / README / données | `test_consistency.py` (rien à ajouter en général : il analyse le code tout seul) |

## Outils disponibles

- **Lancer une commande** : `await bot.bot.get_command('joue').callback(ctx, url='...')` (arguments `*, x` passés **par nom**).
- **`tests/fakes.py`** :
  - `FakeCtx()` sur un serveur, `FakeCtx(guild=None)` en message privé, `FakeCtx(reference_id=123)` pour `donneavis`, `FakeTextChannel(can_send=False)` ;
  - `ctx.reply`, `ctx.send`, `channel.send`, `channel.fetch_message` sont des `AsyncMock` : `ctx.reply.await_args.args[0]` = texte, `ctx.send.await_args.kwargs['embed']` = embed ;
  - `make_voice_ctx(listeners=N)` : auteur déjà dans un salon vocal ;
  - `FakeVoiceClient.finish(error=None)` simule la fin d'un titre, puis `await wait_until(lambda: ...)` (l'enchaînement passe par `run_coroutine_threadsafe`, un `sleep(0)` ne suffit pas).
- **Fixtures (`tests/conftest.py`)** :
  - `data_files(gifs=..., quotes=...)` : fichiers temporaires (données Python ou texte brut pour un JSON cassé ; sans argument = fichier absent) ;
  - `fake_audio` : remplace yt-dlp et ffmpeg ; `fake_audio.add(query, title=..., duration=...)` déclare un titre lisible, toute autre requête lève `DownloadError` ; `fake_audio.calls` liste les requêtes résolues ;
  - les états globaux (`music.*`, token Spotify, cache des textes) sont remis à zéro après chaque test.
- Remplacer une dépendance importée **par valeur** dans le module qui l'utilise : `monkeypatch.setattr(bot, 'fetch_spotify_playlist', ...)`, `monkeypatch.setattr(music, 'VOICE_IDLE_TIMEOUT', 0)`.

## Règles

- Textes attendus calculés avec `t('section.cle', ...)` ou les helpers de `views` (`format_quote`, `format_track_line`, `help_text`), **jamais en dur**.
- Tester le cas message privé de chaque nouvelle commande.
- Un bug trouvé en écrivant un test → commit `fix(...)` séparé dans la même PR.
- Si la couverture passe sous 95 %, ajouter des tests plutôt que baisser `fail_under` (`pyproject.toml`).

## Échecs fréquents

- `test_consistency.py` échoue → une clé `t()` absente de `messages.json`, un paramètre `{x}` non fourni, un texte devenu inutile, ou une commande manquante dans `aide.commands` / le README.
- `TypeError: ... takes 1 positional argument` → argument de commande passé par position au lieu de par nom.
- `ClientResponse.__init__() missing ... 'stream_writer'` → aiohttp a été monté en 3.14 (voir CLAUDE.md).
