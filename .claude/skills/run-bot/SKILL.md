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
```

Sans `DISCORD_TOKEN`, le bot lève `ValueError` au démarrage. S'il n'y a pas de token, s'arrêter là et le dire : on ne peut que vérifier la syntaxe/les imports.

## En local

L'environnement est sous Windows (venv : `venv/Scripts/python`, pas `venv/bin/python` comme dans le README).

```bash
python -m venv venv
venv/Scripts/python -m pip install -r requirements.txt
```

**Attention au CWD** : les chemins par défaut `data/gifs.json` / `data/quotes.json` sont relatifs au répertoire courant. Deux options :

```bash
# Option A : lancer depuis bot/ (comme dans Docker)
cd bot && ../venv/Scripts/python src/bot.py

# Option B : depuis la racine, en surchargeant les chemins
GIFS_FILE=bot/data/gifs.json QUOTES_FILE=bot/data/quotes.json venv/Scripts/python bot/src/bot.py
```

Le bot tourne indéfiniment : le lancer en arrière-plan (`run_in_background`) et surveiller les logs. Logs : console + `botghast.log` dans le CWD. Un démarrage réussi logue `Starting BotGhast...` puis aucune erreur de connexion.

Vérification sans token : `venv/Scripts/python -c "import ast; ast.parse(open('bot/src/bot.py', encoding='utf-8').read())"`. (Importer `bot.py` directement crée `botghast.log` et configure le bot, mais ne se connecte pas.)

## Docker

L'image de base `dhi.io/python:3.11-alpine3.23-dev` est une Docker Hardened Image : `docker login dhi.io` est requis.

```bash
docker build -t botghast .
docker run --rm --env-file .env botghast
```

(Le README oublie le `.` du contexte de build.)

- Les données `bot/` sont copiées dans l'image : rebuild après toute modif du code ou des JSON.
- Pour utiliser des données externes sans rebuild : `-v $(pwd)/bot/data:/data -e GIFS_FILE=/data/gifs.json -e QUOTES_FILE=/data/quotes.json`.
- `.env` est exclu du contexte via `.dockerignore` → toujours passer `--env-file`.
