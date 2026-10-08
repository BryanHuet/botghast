---
name: cmd-citation
description: Travailler sur la commande `citation` de BotGhast (bot/src/bot.py) — envoie une citation philosophique aléatoire tirée de bot/data/quotes.json. À utiliser pour modifier, débugger ou tester `?citation`.
---

# Commande `citation`

**Code** : `citation` dans `bot/src/bot.py` — `@bot.command()`.
**Usage Discord** : `?citation`.
**Données** : `QUOTES_FILE` (défaut `bot/data/quotes.json`) → `[{"citation": "...", "author": "..."}]`, lu et validé par `datastore.load_quotes`.
**Textes** : sections `citation` et `common` de `bot/data/messages.json` ; format de la citation = `common.quote` (`views.format_quote`).

## Déroulé

1. `os.path.exists(QUOTES_FILE)` sinon → `common.quotes_file_missing`.
2. Si le bot n'a pas `send_messages` dans le salon → log `error` et **retour silencieux**.
3. `load_quotes()` ; liste vide → `common.no_quotes`.
4. `random.choice` puis envoi (`ctx.send`) de `format_quote(quote)` (`"<citation> ~ <author>"`).
5. `ValueError` (JSON invalide ou mauvaise structure) → `citation.json_error` ; autre exception → `citation.error`.

## Pièges connus

- Fonctionne en message privé (`guild_name(ctx)`, `ctx.me`).
- Le format `common.quote` est partagé avec `cherchecitation` (`format_quote`) : le changer dans `messages.json` change les deux.
- Rester sous 2000 caractères : une citation très longue ferait échouer l'envoi (`HTTPException`, rattrapée par le `except` générique).

## Données

Ajouter/corriger des citations : `/manage-data` (tri par auteur, libellés d'auteur existants, validation). Pris en compte sans redémarrage en local, rebuild en Docker.

## Vérification

`/test` (`tests/functional/test_cmd_text.py::TestCitation`), `/lint`, puis `/run-bot` et `?citation` plusieurs fois sur Discord.
