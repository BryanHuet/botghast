---
name: cmd-stop
description: Travailler sur la commande `stop` de BotGhast (stop dans bot/src/bot.py) — arrête la musique, vide la file et quitte le salon vocal. À utiliser pour modifier, débugger ou tester `?stop` ou la déconnexion vocale.
---

# Commande `stop`

**Code** : `stop` dans `bot/src/bot.py` — `@bot.command(name='stop', ...)`.
**Usage Discord** : `?stop`.

## Déroulé

1. En DM ou bot non connecté en vocal → « Je ne suis connecté à aucun salon vocal. »
2. **Vide la file** et `now_playing` *avant* de se déconnecter : la déconnexion stoppe la piste, donc déclenche le callback `after` → `play_next`, qui doit trouver une file vide (et, voyant le bot déconnecté, nettoie aussi `music_queues`/`now_playing`).
3. `ctx.voice_client.disconnect()` puis embed « Musique arrêtée, je quitte le salon vocal. » (pied de page : auteur de la commande).

Pipeline audio complet : voir `/cmd-joue`.

## Pièges

- Garder l'ordre « vider puis déconnecter », sinon le callback relance une piste pendant la déconnexion.
- `music_channels` et `music_locks` ne sont pas nettoyés (inoffensif, réécrits au prochain `ensure_voice`).
- Aucune déconnexion automatique quand le salon se vide ou que la file se termine : le bot reste en vocal jusqu'à `?stop`. Si on ajoute un auto-leave, le faire via `on_voice_state_update` ou à la fin de `_play_next_locked`, et réutiliser le même nettoyage.
- Pas de contrôle de qui peut arrêter.

## Vérification

`/lint`, puis `/run-bot` : `?viking` puis `?stop` (le bot doit partir sans relancer de titre), `?stop` hors vocal, puis `?joue` à nouveau pour vérifier que l'état repart proprement.
