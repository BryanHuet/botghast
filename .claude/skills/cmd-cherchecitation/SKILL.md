---
name: cmd-cherchecitation
description: Travailler sur la commande `cherchecitation` de BotGhast (search_quote dans bot/src/bot.py, anciennement `searchquote`) — recherche par mot-clé dans les citations et auteurs de bot/data/quotes.json. À utiliser pour modifier, débugger ou tester `?cherchecitation`.
---

# Commande `cherchecitation`

**Code** : `search_quote` dans `bot/src/bot.py` — `@bot.command(name='cherchecitation', ...)`.
**Usage Discord** : `?cherchecitation <mot-clé>` (le mot-clé peut contenir des espaces grâce à `*, keyword`).
**Données** : `QUOTES_FILE` → lu et validé par `datastore.load_quotes`.
**Textes** : section `cherchecitation` de `bot/data/messages.json` ; réponse construite par `views.search_results_text`.

## Déroulé

1. Mot-clé absent ou vide → `cherchecitation.no_keyword`.
2. Relit + valide `quotes.json` (fichier absent → `common.quotes_file_missing`, liste vide → `common.no_quotes`, fichier invalide → `cherchecitation.error`).
3. Filtre les citations dont `citation` **ou** `author` contient le mot-clé (sous-chaîne, insensible à la casse, **sensible aux accents** : `ethique` ne trouve pas `éthique`).
4. Aucun résultat → `cherchecitation.no_result`.
5. Sinon envoie les **`style.search_results` (3) premiers** résultats (ordre du fichier, donc groupés par auteur) : `cherchecitation.header`, une ligne `cherchecitation.result` par citation, puis `cherchecitation.more` s'il en reste.

## Pièges connus

- Garder `keyword: str = None` : sans valeur par défaut, discord.py lève `MissingRequiredArgument` avant la fonction et l'utilisateur ne reçoit rien.
- **Mentions** : le mot-clé est renvoyé tel quel dans la réponse ; `@everyone` passé en mot-clé serait réémis. Envisager `allowed_mentions=discord.AllowedMentions.none()` sur les `send`/`reply`.
- **2000 caractères** : 3 citations longues peuvent dépasser la limite (rien ne tronque) → l'envoi échoue et l'utilisateur reçoit `cherchecitation.error`.
- Si on rend la recherche insensible aux accents, utiliser `unicodedata.normalize('NFKD', ...)` et retirer les combinants, sur le texte **et** le mot-clé.

## Vérification

`/test` (`tests/functional/test_cmd_text.py::TestChercheCitation`), `/lint`, puis `/run-bot` : `?cherchecitation Nietzsche`, un mot sans résultat, et `?cherchecitation` seul.
