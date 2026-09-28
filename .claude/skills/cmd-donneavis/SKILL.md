---
name: cmd-donneavis
description: Travailler sur la commande `donneavis` de BotGhast (bot/src/bot.py) — répond à un message cité avec un GIF aléatoire de bot/data/gifs.json. À utiliser pour modifier, débugger ou tester `?donneavis`.
---

# Commande `donneavis`

**Code** : `donneavis` dans `bot/src/bot.py` — `@bot.command()` (nom = nom de la fonction).
**Usage Discord** : répondre (reply) à un message avec `?donneavis`.
**Données** : `GIFS_FILE` (défaut `data/gifs.json`, relatif au CWD) → `{"gifs": [url, ...]}`, validé par `validate_gifs_json`.

## Déroulé

1. `os.path.exists(gifs)` sinon → « Le fichier de GIFs est introuvable. »
2. Pas de `ctx.message.reference` → « Aucun message sélectionné, tu veux que je réagisse à quoi là ??? »
3. `fetch_message(reference.message_id)` avec gestion `discord.NotFound` / `discord.Forbidden` / `Exception` → message FR dédié à chaque cas.
4. Relit et valide le JSON, tire un GIF au hasard, **répond au message cité** (`referenced_message.reply`), pas au message de commande.
5. Toute erreur de l'étape 4 → `ctx.send('J\'ai besoin de repos...')`.

## Pièges connus

- **DM** : `ctx.guild.name` dans les logs → `AttributeError` en message privé. Utiliser `guild_name = ctx.guild.name if ctx.guild else "DM"`.
- **Liste vide** : `validate_gifs_json` accepte `{"gifs": []}` → `random.choice` lève `IndexError` → l'utilisateur reçoit « J'ai besoin de repos... ». Si on veut un message clair, tester `if not gifs_list` avant.
- `random.shuffle` puis `random.choice` est redondant (sans effet sur l'aléatoire).
- La réponse est une f-string triple-quotée : elle contient des sauts de ligne et de l'indentation autour de l'URL. Discord intègre quand même le GIF ; `await referenced_message.reply(gif)` suffit.
- Le message cité doit être dans le **même salon** (`ctx.message.channel.fetch_message`).
- Permission requise : lire l'historique du salon (sinon `Forbidden`).

## Données

Ajout/vérif de GIFs : utiliser `/manage-data` (URLs Tenor complètes, validation via `validate_data.py`). En local la modif est prise en compte sans redémarrage ; dans Docker il faut rebuild.

## Vérification

`/lint`, puis `/run-bot` et sur Discord : reply à un message + `?donneavis` ; `?donneavis` sans reply (message d'erreur attendu).
