---
name: cmd-donneavis
description: Travailler sur la commande `donneavis` de BotGhast (bot/src/bot.py) — répond à un message cité avec un GIF aléatoire de bot/data/gifs.json. À utiliser pour modifier, débugger ou tester `?donneavis`.
---

# Commande `donneavis`

**Code** : `donneavis` dans `bot/src/bot.py` — `@bot.command()` (nom = nom de la fonction).
**Usage Discord** : répondre (reply) à un message avec `?donneavis`.
**Données** : `GIFS_FILE` (défaut `bot/data/gifs.json`) → `{"gifs": [url, ...]}`, lu et validé par `datastore.load_gifs`.
**Textes** : section `donneavis` de `bot/data/messages.json`.

## Déroulé

1. `os.path.exists(GIFS_FILE)` sinon → `donneavis.gifs_file_missing`.
2. Pas de `ctx.message.reference` → `donneavis.no_reference`.
3. `fetch_message(reference.message_id)` : `None` → `reference_inaccessible`, `discord.NotFound` → `reference_not_found`, `discord.Forbidden` → `reference_forbidden`, autre → `reference_error`.
4. `load_gifs()`, tire un GIF au hasard, **répond au message cité** (`referenced_message.reply(t('donneavis.response', gif=...))`), pas au message de commande.
5. Toute erreur de l'étape 4 → `ctx.send(t('donneavis.error'))`.

## Pièges connus

- Fonctionne en message privé (`guild_name(ctx)`).
- **Liste vide** : `validate_gifs_json` accepte `{"gifs": []}` → `random.choice` lève `IndexError` → l'utilisateur reçoit `donneavis.error`. Le test de cohérence `test_gifs_file_is_valid` refuse un `gifs.json` réel vide.
- Le message cité doit être dans le **même salon** (`ctx.message.channel.fetch_message`).
- Permission requise : lire l'historique du salon (sinon `Forbidden`).

## Données

Ajout/vérif de GIFs : utiliser `/manage-data` (URLs Tenor complètes, validation via `validate_data.py` et `/test`). En local la modif est prise en compte sans redémarrage ; dans Docker il faut rebuild.

## Vérification

`/test` (`tests/functional/test_cmd_text.py::TestDonneAvis`), `/lint`, puis `/run-bot` et sur Discord : reply à un message + `?donneavis` ; `?donneavis` sans reply (message d'erreur attendu).
