---
name: cmd-cherchecitation
description: Travailler sur la commande `cherchecitation` de BotGhast (search_quote dans bot/src/bot.py, anciennement `searchquote`) — recherche par mot-clé dans les citations et auteurs de bot/data/quotes.json. À utiliser pour modifier, débugger ou tester `?cherchecitation`.
---

# Commande `cherchecitation`

**Code** : `search_quote` dans `bot/src/bot.py` — `@bot.command(name='cherchecitation', ...)`.
**Usage Discord** : `?cherchecitation <mot-clé>` (le mot-clé peut contenir des espaces grâce à `*, keyword`).
**Données** : `QUOTES_FILE` → validé par `validate_quotes_json`.

## Déroulé

1. Relit + valide `quotes.json` (fichier absent / liste vide → message FR).
2. Filtre les citations dont `citation` **ou** `author` contient le mot-clé (sous-chaîne, insensible à la casse, **sensible aux accents** : `ethique` ne trouve pas `éthique`).
3. Aucun résultat → « Aucune citation trouvée pour '<mot-clé>'. »
4. Sinon envoie les **3 premiers** résultats (ordre du fichier, donc groupés par auteur) au format `N. <citation> ~ <author>`, puis « ... et X autres résultats. »

## Pièges connus

- **Mot-clé absent** : `keyword: str` est obligatoire → discord.py lève `MissingRequiredArgument` *avant* le corps de la fonction ; le `if not keyword` n'est jamais atteint et l'utilisateur ne reçoit rien (aucun `on_command_error`). Pour un message FR : `keyword: str = None`, ou un handler `@search_quote.error`.
- **DM** : `ctx.guild.name` dans les logs → `AttributeError`.
- **Mentions** : le mot-clé est renvoyé tel quel dans la réponse ; `@everyone` passé en mot-clé serait réémis. Envisager `allowed_mentions=discord.AllowedMentions.none()` sur les `send`/`reply`.
- **2000 caractères** : 3 citations longues peuvent dépasser la limite → tronquer `response[:2000]` comme `file`.
- Si on rend la recherche insensible aux accents, utiliser `unicodedata.normalize('NFKD', ...)` et retirer les combinants, sur le texte **et** le mot-clé.

## Vérification

`/lint`, puis `/run-bot` : `?cherchecitation Nietzsche`, un mot sans résultat, et `?cherchecitation` seul.
