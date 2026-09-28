---
name: manage-data
description: Ajouter, retirer ou vérifier des GIFs (bot/data/gifs.json) et des citations (bot/data/quotes.json) de BotGhast, avec validation de structure et détection des doublons. À utiliser quand on touche aux fichiers de données du bot.
---

# Gérer les données de BotGhast

## Formats

`bot/data/gifs.json` — objet avec une clé `gifs` :
```json
{ "gifs": ["https://tenor.com/view/...-gif-12345678"] }
```

`bot/data/quotes.json` — tableau d'objets :
```json
[{ "citation": "Penser, c'est dire non.", "author": "Alain" }]
```

## Règles d'édition

- Encodage UTF-8, indentation 2 espaces, garder le style existant (pas de réécriture complète du fichier juste pour reformater).
- Citations : en français, apostrophes typographiques `’` comme la majorité du fichier, champ `author` = nom usuel de l'auteur (ex. `"Aristote"`, `"André Malraux"`). Les citations sont groupées par auteur, triées alphabétiquement par auteur : insérer au bon endroit. Si l'auteur existe déjà, réutiliser exactement son libellé (attention : le fichier contient des variantes comme `Sartre` / `Jean - Paul Sartre` — les signaler plutôt que d'en créer une nouvelle).
- GIFs : URLs Tenor complètes (`https://tenor.com/view/...`), Discord les intègre automatiquement.
- Ne pas ajouter d'autres clés : les validateurs du bot n'exigent que `citation`/`author` ou `gifs`, mais gardons le format minimal.

## Validation (obligatoire après chaque modif)

Depuis la racine du repo :

```bash
python .claude/skills/manage-data/scripts/validate_data.py
```

Le script vérifie la structure attendue par `validate_gifs_json` / `validate_quotes_json` de `bot/src/bot.py`, que les GIFs sont des URLs http(s), que les citations/auteurs ne sont pas vides, et signale les doublons (warnings). Code de sortie 1 en cas d'erreur de structure. Accepte des chemins alternatifs : `validate_data.py <gifs.json> <quotes.json>`.

## Prise en compte

- En local : immédiate (les fichiers sont relus à chaque commande).
- Docker : les données sont copiées dans l'image → rebuild nécessaire (voir `/run-bot`).
