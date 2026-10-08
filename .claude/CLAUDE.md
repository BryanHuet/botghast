# BotGhast

Bot Discord personnel (discord.py, commandes à préfixe) qui envoie des GIFs et des citations philosophiques, et joue de la musique en vocal (YouTube / playlists Spotify).

## Structure

- `bot/src/bot.py` — **tout le code** : logging, validation JSON, pipeline audio (yt-dlp + ffmpeg, API Spotify) et toutes les commandes (`@bot.command()`).
- `bot/src/spotify_auth.py` — script à lancer une fois pour obtenir `SPOTIFY_REFRESH_TOKEN`.
- `bot/data/gifs.json` — `{"gifs": ["https://tenor.com/...", ...]}`
- `bot/data/quotes.json` — `[{"citation": "...", "author": "..."}, ...]`
- `Dockerfile` — build multi-stage sur l'image hardened `dhi.io/python:3.11-alpine3.23-dev` (nécessite `docker login dhi.io`).
- `.github/workflows/python-app.yml` — CI : flake8 + pytest (matrice Python 3.10 / 3.11).
- `tests/` — pytest (`pyproject.toml`, deps dans `requirements-dev.txt`). `conftest.py` fixe l'env de test **avant** d'importer les modules (config figée à l'import) et remet à zéro les états globaux ; `fakes.py` = faux objets discord (`FakeCtx`, `FakeVoiceClient`...). Fixture `data_files` pour rediriger GIFs/citations. Lancer : `venv/bin/pytest`.

## Commandes du bot

| Commande | Rôle |
|---|---|
| `aide` | Aide (texte **maintenu à la main** dans `help_command`) |
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
- `GIFS_FILE` (défaut `data/gifs.json`), `QUOTES_FILE` (défaut `data/quotes.json`)
- `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN`, `SPOTIFY_PLAYLIST` (pour `viking`, voir `.env.example`)

## Conventions

- Code, docstrings et logs en **anglais** ; messages envoyés aux utilisateurs Discord en **français**.
- Chaque commande : docstring style Google (Args/Returns/Usage), `logger.info` à l'invocation avec auteur/canal/serveur, `try/except` qui log l'erreur et répond un message d'erreur en français plutôt que de laisser remonter l'exception.
- Les fichiers JSON sont relus à chaque commande et validés via `validate_gifs_json` / `validate_quotes_json` → les modifs de données ne nécessitent pas de redémarrage en local.
- Utiliser le logger `botghast` (jamais `print`). Timestamps en Europe/Paris via `ParisTimeFormatter`.
- Commits : Conventional Commits (`feat(scope): ...`, `fix(env): ...`). Branches : `<n°-issue>-<slug>`, PR vers `main`.

## Pièges connus

- **Chemins relatifs au CWD** : les chemins par défaut `data/*.json` ne marchent que si on lance depuis `bot/` (c'est le cas dans Docker, `WORKDIR /usr/bot`). Depuis la racine, il faut `GIFS_FILE=bot/data/gifs.json` et `QUOTES_FILE=bot/data/quotes.json`.
- `botghast.log` est écrit dans le CWD (ignoré par git via `*.log`).
- `aide`, `donneavis`, `citation`, `cherchecitation` accèdent à `ctx.guild.name` → `AttributeError` en message privé (guild = `None`). Les commandes musicales sont protégées (`guild_name = ... else "DM"`) : faire pareil pour les nouvelles.
- Les commandes musicales exigent `ffmpeg` dans le `PATH` ; le `Dockerfile` ne l'installe pas encore.
- Dans Docker, les données sont copiées dans l'image : modifier les JSON impose un rebuild (ou un montage de volume + `GIFS_FILE`/`QUOTES_FILE`).
- `requirements.txt` contient à la fois `discord` (paquet miroir) et `discord.py` ; ne pas en retirer un sans vérifier.
- `aiohttp` est figé en 3.13.x dans `requirements.txt` : `aioresponses` (mock HTTP des tests Spotify) casse avec aiohttp 3.14 (`ClientResponse.__init__() missing ... 'stream_writer'`). Ne monter qu'après avoir vérifié les tests.
- Versions Python divergentes : CI 3.10, Docker 3.11, README ">= 3.8". Garder le code compatible 3.10.
- Toute nouvelle commande doit être ajoutée au texte de `aide` et au README.

## Skills du projet

- `/run-bot` — lancer le bot en local ou via Docker
- `/add-command` — ajouter une commande Discord selon les conventions
- `/manage-data` — ajouter/valider des GIFs et citations
- `/lint` — reproduire les vérifications de la CI
- `/cmd-aide`, `/cmd-donneavis`, `/cmd-citation`, `/cmd-cherchecitation`, `/cmd-joue` (+ pipeline audio), `/cmd-viking`, `/cmd-suivant`, `/cmd-file`, `/cmd-stop` — une commande chacun
