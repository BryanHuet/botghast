---
name: cmd-aide
description: Travailler sur la commande `aide` de BotGhast (help_command dans bot/src/bot.py) — texte d'aide maintenu à la main. À utiliser pour modifier/débugger `?aide` ou pour resynchroniser l'aide après l'ajout, le renommage ou la suppression d'une commande.
---

# Commande `aide`

**Code** : `help_command` dans `bot/src/bot.py` — `@bot.command(name='aide', ...)`.
**Usage Discord** : `?aide` (préfixe = `BOT_PREFIX`, défaut `?`).

## Comportement

Envoie (`ctx.send`) un bloc de texte statique en français listant toutes les commandes, chaque ligne préfixée par `{PREFIX}`. Aucune donnée lue, aucun `try/except`.

## Source de vérité

Le texte est **écrit à la main** : il n'est pas généré depuis les commandes enregistrées. Pour le resynchroniser :

1. Lister les commandes réelles : `grep -n "@bot.command" bot/src/bot.py` (prendre `name=` s'il existe, sinon le nom de la fonction).
2. Comparer avec les lignes `{PREFIX}...` de `help_text`, et avec le tableau des commandes du `README.md`.
3. Une ligne par commande, format `{PREFIX}<nom> <args> - <description FR>` ; arguments obligatoires en `<...>`, optionnels en `[...]`.

Commandes attendues actuellement : `aide`, `donneavis`, `citation`, `cherchecitation`, `joue`, `viking`, `suivant`, `file`, `arrete`.

## Pièges

- **DM** : le `logger.info` d'invocation lit `ctx.guild.name` → `AttributeError` en message privé, l'aide ne s'affiche pas. Correctif : `guild_name = ctx.guild.name if ctx.guild else "DM"` (cf. commandes musicales).
- Le texte est une f-string triple-quotée indentée : les 4 espaces de chaque ligne sont envoyés tels quels. Utiliser `textwrap.dedent` ou des lignes concaténées si on veut un rendu propre.
- `commands.Bot` garde sa commande `help` par défaut (en anglais) : `?help` existe aussi. Pour la retirer, `commands.Bot(..., help_command=None)`.
- Rester sous 2000 caractères (limite d'un message Discord).

## Vérification

`/lint`, puis test manuel `?aide` via `/run-bot` (sur un serveur **et** en DM si on a corrigé le bug DM).
