# BotGhast

Bot Discord personnel (discord.py, commandes à préfixe) qui envoie des GIFs et des citations philosophiques, et joue de la musique en vocal (YouTube / playlists Spotify).

## Structure

- `bot/src/bot.py` — **uniquement les commandes** (`@bot.command()`) et l'événement `on_voice_state_update`.
- `bot/src/config.py` — variables d'environnement et constantes techniques (options yt-dlp/ffmpeg, volume, `VOICE_IDLE_TIMEOUT`). Figées à l'import.
- `bot/src/log.py` — logger `botghast` (console + `botghast.log`, heure de Paris).
- `bot/src/texts.py` + `bot/data/messages.json` — **tous les textes affichés** et le style (couleurs, limites) : `t('section.cle', param=...)`, `style(...)`, `colour(...)`. Rechargé à chaud si le fichier change.
- `bot/src/views.py` — construction des textes et embeds (citation, aide, recherche, embeds musicaux).
- `bot/src/datastore.py` — lecture + validation de `gifs.json` / `quotes.json` (`load_gifs`, `load_quotes`, `validate_*_json`).
- `bot/src/youtube.py` / `bot/src/spotify_client.py` — sources audio (yt-dlp, API Spotify).
- `bot/src/music.py` — état par serveur (files, titre en cours, verrous), lecture ffmpeg, enchaînement, déconnexion quand le bot reste seul.
- `bot/src/spotify_auth.py` — script à lancer une fois pour obtenir `SPOTIFY_REFRESH_TOKEN`.
- `bot/data/gifs.json` — `{"gifs": ["https://tenor.com/...", ...]}` ; `bot/data/quotes.json` — `[{"citation": "...", "author": "..."}, ...]`.
- `Dockerfile` — build multi-stage sur l'image hardened `dhi.io/python:3.11-alpine3.23-dev` (nécessite `docker login dhi.io`).
- `.github/workflows/python-app.yml` — CI : flake8 + pytest avec couverture (matrice Python 3.10 / 3.11).
- `tests/` — pytest, voir ci-dessous.

## Tests

`venv/bin/pytest` (skill `/test`). Pas de réseau ni de token Discord.

- `tests/unit/` — un fichier par module, appels réseau mockés (`aioresponses` pour Spotify).
- `tests/functional/` — chaque commande lancée via `bot.bot.get_command('<nom>').callback(ctx, ...)` avec les faux objets de `tests/fakes.py` (`FakeCtx`, `FakeCtx(guild=None)` = message privé, `make_voice_ctx`, `FakeVoiceClient.finish()` = fin de titre, `wait_until`).
- `tests/contract/` — cohérence code / `messages.json` / README / données réelles : toute clé `t()` doit exister et recevoir ses paramètres, aucun texte inutilisé, `aide` et README listent exactement les commandes enregistrées.
- `conftest.py` fixe l'env de test **avant** d'importer les modules et remet à zéro les états globaux. Fixtures : `data_files` (GIFs/citations temporaires), `fake_audio` (remplace yt-dlp et ffmpeg).
- Textes attendus calculés avec `t()`, jamais écrits en dur.
- Couverture minimale 95 % (`fail_under` dans `pyproject.toml`) : `pytest --cov` échoue en dessous.

## Commandes du bot

| Commande | Rôle |
|---|---|
| `aide` | Aide (liste dans `aide.commands` de `messages.json`) |
| `donneavis` | À utiliser en réponse à un message : le bot répond au message cité avec un GIF aléatoire |
| `citation` | Citation aléatoire |
| `cherchecitation <mot-clé>` | Recherche dans citation + auteur, 3 premiers résultats |
| `joue <lien>` | Joue une vidéo ou une playlist YouTube (URL avec `list=`) en vocal (ajoutée en fin de file si un titre est en cours) |
| `viking [playlist]` | Met en file une playlist Spotify (défaut `SPOTIFY_PLAYLIST`), lue depuis YouTube |
| `suivant` | Passe au titre suivant |
| `file` | Titre en cours + file d'attente |
| `stop` | Stoppe, vide la file, quitte le vocal |

Chaque commande a un skill dédié `/cmd-<commande>` (déroulé, pièges, vérification).

## Variables d'environnement (`.env` à la racine, chargé par `python-dotenv`)

- `DISCORD_TOKEN` (obligatoire)
- `BOT_PREFIX` (défaut `?`)
- `GIFS_FILE`, `QUOTES_FILE`, `MESSAGES_FILE` (défaut : fichiers de `bot/data/`, chemin absolu calculé depuis `config.py`, quel que soit le dossier de lancement)
- `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN`, `SPOTIFY_PLAYLIST` (pour `viking`, voir `.env.example`)

## Conventions

- Code, docstrings et logs en **anglais** ; textes affichés sur Discord en **français**, dans `bot/data/messages.json` (jamais en dur dans le code).
- Chaque commande : docstring style Google (Args/Returns/Usage), `logger.info` à l'invocation avec auteur/canal/serveur (`guild_name(ctx)`, sûr en message privé), `try/except` qui log l'erreur et répond un message d'erreur en français plutôt que de laisser remonter l'exception.
- Les fichiers JSON sont relus à chaque commande (`datastore`) et `messages.json` dès qu'il change → pas de redémarrage en local.
- Utiliser le logger `botghast` (jamais `print`). Timestamps en Europe/Paris via `ParisTimeFormatter`.
- Commits : Conventional Commits (`feat(scope): ...`, `fix(env): ...`). Branches : `<n°-issue>-<slug>`, PR vers `main`.

## Pièges connus

- `botghast.log` est écrit dans le CWD (ignoré par git via `*.log`).
- Les commandes musicales exigent `ffmpeg` dans le `PATH` ; le `Dockerfile` ne l'installe pas encore.
- Dans Docker, les données sont copiées dans l'image : modifier les JSON impose un rebuild (ou un montage de volume + `GIFS_FILE`/`QUOTES_FILE`/`MESSAGES_FILE`).
- `requirements.txt` contient à la fois `discord` (paquet miroir) et `discord.py` ; ne pas en retirer un sans vérifier.
- `aiohttp` est figé en 3.13.x dans `requirements.txt` : `aioresponses` (mock HTTP des tests Spotify) casse avec aiohttp 3.14 (`ClientResponse.__init__() missing ... 'stream_writer'`). Ne monter qu'après avoir vérifié les tests.
- Versions Python divergentes : CI 3.10 et 3.11, Docker 3.11. Garder le code compatible 3.10.
- `t()` ne lève jamais d'erreur (clé ou paramètre manquant → log + texte brut) : ce sont les tests de `tests/contract/` qui attrapent ces fautes.
- Toute nouvelle commande doit être ajoutée à `aide.commands` (`messages.json`) et au README : les tests de cohérence échouent sinon.

## Skills du projet

- `/run-bot` — lancer le bot en local ou via Docker
- `/add-command` — ajouter une commande Discord selon les conventions
- `/manage-data` — ajouter/valider des GIFs et citations
- `/lint` — reproduire flake8 comme la CI
- `/test` — lancer et écrire les tests pytest
- `/cmd-aide`, `/cmd-donneavis`, `/cmd-citation`, `/cmd-cherchecitation`, `/cmd-joue` (+ pipeline audio), `/cmd-viking`, `/cmd-suivant`, `/cmd-file`, `/cmd-stop` — une commande chacun
