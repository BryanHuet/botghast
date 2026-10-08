---
name: run-bot
description: Lancer BotGhast en local (venv) ou dans Docker, avec la bonne configuration .env et les bons chemins de données. À utiliser pour démarrer, tester manuellement ou débugger le bot.
---

# Lancer BotGhast

## Prérequis

Un fichier `.env` à la racine (jamais commité, jamais affiché en entier — ne montrer que les clés) :

```env
DISCORD_TOKEN=...
BOT_PREFIX=?            # optionnel
GIFS_FILE=...           # optionnel
QUOTES_FILE=...         # optionnel
MESSAGES_FILE=...       # optionnel (textes affichés)
```

Sans `DISCORD_TOKEN`, le bot lève `ValueError` au démarrage. S'il n'y a pas de token, s'arrêter là et le dire : on ne peut que lancer les tests (`/test`).

## En local

```bash
python -m venv venv
venv/bin/pip install -r requirements.txt     # Windows : venv/Scripts/...
venv/bin/python bot/src/bot.py
```

Les chemins par défaut des données (`bot/data/*.json`) sont absolus (calculés depuis `config.py`) : le bot se lance depuis n'importe quel dossier. Seul `botghast.log` est écrit dans le dossier courant.

Le bot tourne indéfiniment : le lancer en arrière-plan (`run_in_background`) et surveiller les logs (console + `botghast.log`). Un démarrage réussi logue `Starting BotGhast...` puis aucune erreur de connexion. Les commandes musicales demandent `ffmpeg` dans le `PATH`.

Vérification sans token : `/test` (toutes les commandes sont testées avec de faux objets Discord, sans connexion).

## Docker

L'image de base `dhi.io/python:3.11-alpine3.23-dev` est une Docker Hardened Image : `docker login dhi.io` est requis.

```bash
docker build -t botghast .
docker run --rm --env-file .env botghast
```

- Les données `bot/` sont copiées dans l'image : rebuild après toute modif du code ou des JSON.
- Pour utiliser des données externes sans rebuild : `-v $(pwd)/bot/data:/data -e GIFS_FILE=/data/gifs.json -e QUOTES_FILE=/data/quotes.json -e MESSAGES_FILE=/data/messages.json`.
- `.env` est exclu du contexte via `.dockerignore` → toujours passer `--env-file`.
