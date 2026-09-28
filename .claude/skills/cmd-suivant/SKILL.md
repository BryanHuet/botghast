---
name: cmd-suivant
description: Travailler sur la commande `suivant` de BotGhast (skip dans bot/src/bot.py) — passe au titre suivant de la file musicale. À utiliser pour modifier, débugger ou tester `?suivant`.
---

# Commande `suivant`

**Code** : `skip` dans `bot/src/bot.py` — `@bot.command(name='suivant', ...)`.
**Usage Discord** : `?suivant`.

## Déroulé

1. Pas de guilde, pas de `voice_client`, ou rien en lecture/pause → « Rien n'est en cours de lecture. »
2. `voice_client.stop()` : c'est le callback `after` de la piste (défini dans `start_track`) qui appelle `play_next` et lance la suivante — `suivant` ne démarre rien lui-même.
3. Répond un embed « Titre passé : <titre en cours> » (+ « La file est vide. » si c'est le cas) (le bot reste alors connecté en silence).

Pipeline audio complet : voir `/cmd-joue`.

## Pièges

- La longueur de file est lue juste après `stop()` : le callback tourne dans un autre thread et peut déjà avoir dépilé l'entrée suivante → la mention « La file est vide » peut manquer quand il ne restait qu'un titre. Sans conséquence fonctionnelle.
- Si la piste suivante n'est pas lisible, `_play_next_locked` la saute et annonce un embed rouge « Impossible de lire ... » dans le salon mémorisé.
- Aucun contrôle de qui skip (pas de vote, pas de vérif que l'auteur est dans le même salon vocal). À ajouter ici si besoin (`ctx.author.voice.channel == voice_client.channel`).
- Ne pas appeler `play_next` directement en plus du `stop()` : double démarrage évité par le lock, mais inutile.

## Vérification

`/lint`, puis `/run-bot` : lancer `?viking` (file de plusieurs titres), `?suivant`, `?file` ; puis `?suivant` sans lecture.
