---
name: cmd-suivant
description: Travailler sur la commande `suivant` de BotGhast (skip dans bot/src/bot.py) — passe au titre suivant de la file musicale. À utiliser pour modifier, débugger ou tester `?suivant`.
---

# Commande `suivant`

**Code** : `skip` dans `bot/src/bot.py` — `@bot.command(name='suivant', ...)`.
**Usage Discord** : `?suivant`.

## Déroulé

1. Pas de guilde, pas de `voice_client`, ou rien en lecture/pause → `suivant.nothing_playing`.
2. `voice_client.stop()` : c'est le callback `after` de la piste (défini dans `start_track`) qui appelle `play_next` et lance la suivante — `suivant` ne démarre rien lui-même.
3. Répond un embed `suivant.skipped_track` (ou `suivant.skipped` sans titre connu), + `suivant.queue_empty` si la file est vide (le bot reste alors connecté en silence).

Pipeline audio complet : voir `/cmd-joue`.

## Pièges

- La file est lue juste après `stop()` mais avant tout `await` : `play_next` (programmé par le callback via `run_coroutine_threadsafe`) ne peut pas encore avoir dépilé l'entrée suivante, donc `suivant.queue_empty` est fiable. Garder cette lecture avant le premier `await`.
- Si la piste suivante n'est pas lisible, `_play_next_locked` la saute et annonce un embed rouge `voice.track_error` dans le salon mémorisé.
- Aucun contrôle de qui skip (pas de vote, pas de vérif que l'auteur est dans le même salon vocal). À ajouter ici si besoin (`ctx.author.voice.channel == voice_client.channel`).
- Ne pas appeler `play_next` directement en plus du `stop()` : double démarrage évité par le lock, mais inutile.

## Vérification

`/test` (`tests/functional/test_cmd_music.py::TestSuivant`), `/lint`, puis `/run-bot` : lancer `?viking` (file de plusieurs titres), `?suivant`, `?file` ; puis `?suivant` sans lecture.
