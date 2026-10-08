---
name: cmd-aide
description: Travailler sur la commande `aide` de BotGhast (help_command dans bot/src/bot.py) — liste des commandes tirée de aide.commands dans bot/data/messages.json. À utiliser pour modifier/débugger `?aide` ou pour resynchroniser l'aide après l'ajout, le renommage ou la suppression d'une commande.
---

# Commande `aide`

**Code** : `help_command` dans `bot/src/bot.py` — `@bot.command(name='aide', ...)` ; texte construit par `views.help_text()`.
**Textes** : section `aide` de `bot/data/messages.json` (`title`, `line`, `commands`, `footer`).
**Usage Discord** : `?aide` (préfixe = `BOT_PREFIX`, défaut `?`).

## Comportement

Envoie (`ctx.send`) : `aide.title`, une ligne `aide.line` par entrée de `aide.commands` (`{prefix}{usage} - {description}`), puis `aide.footer`. Fonctionne aussi en message privé.

## Source de vérité

La liste est **écrite à la main** dans `aide.commands` (pas générée depuis les commandes enregistrées), mais `tests/contract/test_consistency.py` vérifie qu'elle contient exactement les commandes enregistrées (premier mot de `usage`), comme les tableaux du README. Après un ajout/renommage/suppression :

1. Mettre à jour `aide.commands` : `{"usage": "nom <arg obligatoire> [arg optionnel]", "description": "..."}`.
2. Mettre à jour le tableau du `README.md`.
3. `/test` : `test_aide_lists_exactly_the_registered_commands` et `test_readme_lists_exactly_the_registered_commands` doivent passer.

Le fichier est rechargé à chaud : pas de redémarrage pour changer le texte en local.

## Pièges

- `commands.Bot` garde sa commande `help` par défaut (en anglais) : `?help` existe aussi. Pour la retirer, `commands.Bot(..., help_command=None)`, puis retirer `help` de `BUILTIN_COMMANDS` (`tests/contract/test_consistency.py`).
- Rester sous 2000 caractères (limite d'un message Discord).

## Vérification

`/test` (`tests/functional/test_cmd_text.py::TestAide` + tests de cohérence), puis test manuel `?aide` via `/run-bot`.
