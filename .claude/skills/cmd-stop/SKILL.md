---
name: cmd-stop
description: Travailler sur la commande `stop` de BotGhast (stop dans bot/src/bot.py) — arrête la musique, vide la file et quitte le salon vocal. À utiliser pour modifier, débugger ou tester `?stop` ou la déconnexion vocale.
---

# Commande `stop`

**Code** : `stop` dans `bot/src/bot.py` — `@bot.command(name='stop', ...)`.
**Usage Discord** : `?stop`.

## Déroulé

1. En DM ou bot non connecté en vocal → `stop.not_connected`.
2. **Vide la file** et `now_playing` *avant* de se déconnecter : la déconnexion stoppe la piste, donc déclenche le callback `after` → `play_next`, qui doit trouver une file vide (et, voyant le bot déconnecté, nettoie aussi `music_queues`/`now_playing`).
3. `ctx.voice_client.disconnect()` puis embed `stop.stopped` (pied de page : auteur de la commande).

Pipeline audio complet : voir `/cmd-joue`.

## Pièges

- Garder l'ordre « vider puis déconnecter », sinon le callback relance une piste pendant la déconnexion.
- `music_channels` et `music_locks` ne sont pas nettoyés (inoffensif, réécrits au prochain `ensure_voice`).
- Déconnexion automatique : quand plus aucun humain n'est dans le salon, `on_voice_state_update` → `music.watch_listeners` programme `disconnect_if_alone` (après `VOICE_IDLE_TIMEOUT` = 30 s, annulé si quelqu'un revient), qui fait le même nettoyage que `stop` et annonce `voice.left_empty`. `stop` n'annule pas cette tâche : elle trouve le bot déjà déconnecté et ne fait rien. En fin de file (sans départ des auditeurs), le bot reste connecté.
- Pas de contrôle de qui peut arrêter.

## Vérification

`/test` (`tests/functional/test_cmd_music.py::TestStop`, `test_music_flow.py::TestIdleDisconnect`), `/lint`, puis `/run-bot` : `?viking` puis `?stop` (le bot doit partir sans relancer de titre), `?stop` hors vocal, puis `?joue` à nouveau pour vérifier que l'état repart proprement.
