---
name: cmd-citation
description: Travailler sur la commande `citation` de BotGhast (bot/src/bot.py) — envoie une citation philosophique aléatoire tirée de bot/data/quotes.json. À utiliser pour modifier, débugger ou tester `?citation`.
---

# Commande `citation`

**Code** : `citation` dans `bot/src/bot.py` — `@bot.command()`.
**Usage Discord** : `?citation`.
**Données** : `QUOTES_FILE` (défaut `data/quotes.json`, relatif au CWD) → `[{"citation": "...", "author": "..."}]`, validé par `validate_quotes_json`.

## Déroulé

1. `os.path.exists(quotes)` sinon → « Le fichier de citations est introuvable. »
2. Si le bot n'a pas `send_messages` dans le salon → log `error` et **retour silencieux**.
3. Relit + valide le JSON ; liste vide → « Aucune citation disponible. »
4. `random.choice` puis envoi (`ctx.send`) au format `"<citation> ~ <author>"`.
5. `json.JSONDecodeError` → « Erreur de format dans le fichier de citations. » ; autre exception → « Une erreur est survenue lors de la récupération de la citation. »

## Pièges connus

- **DM** : `ctx.guild.name` (logs) et `ctx.guild.me` (check de permission) → `AttributeError` en message privé. Protéger avec `if ctx.guild` et `guild_name = ... else "DM"`.
- Les vérifications `isinstance(random_quote, dict)` / clés présentes sont redondantes avec `validate_quotes_json` (déjà vérifié pour toutes les citations) — on peut les retirer sans risque.
- Le format `"citation ~ author"` est partagé avec `cherchecitation` : garder les deux cohérents si on le change.
- Rester sous 2000 caractères : une citation très longue ferait échouer l'envoi (`HTTPException`, rattrapée par le `except` générique).

## Données

Ajouter/corriger des citations : `/manage-data` (tri par auteur, libellés d'auteur existants, validation). Pris en compte sans redémarrage en local, rebuild en Docker.

## Vérification

`/lint`, puis `/run-bot` et `?citation` plusieurs fois sur Discord.
