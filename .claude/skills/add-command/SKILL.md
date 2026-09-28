---
name: add-command
description: Ajouter ou modifier une commande Discord de BotGhast (bot/src/bot.py) en respectant les conventions du projet (logging, messages FR, gestion d'erreurs, aide, README). À utiliser dès qu'on crée/renomme/modifie une commande du bot.
---

# Ajouter une commande BotGhast

Toutes les commandes vivent dans `bot/src/bot.py`. Lis le fichier avant d'éditer et place la nouvelle commande après les commandes existantes, avant le bloc `if __name__ == "__main__":`.

## Squelette

```python
@bot.command(name='macommande', help='Short English description')
async def ma_commande(ctx, *, arg: str = None):
    """
    One-line English summary.

    Args:
        ctx: discord.ext.commands.Context object
        arg: ...

    Returns:
        None

    Usage:
        ?macommande <arg>
    """
    guild_name = ctx.guild.name if ctx.guild else "DM"
    logger.info(f"Command 'macommande' invoked by {ctx.author} in channel {ctx.channel} on server {guild_name}")

    try:
        ...
        await ctx.send("Réponse en français")
    except Exception as e:
        logger.error(f"Error in macommande command: {e} on server {guild_name}")
        await ctx.reply("Une erreur est survenue ...")
```

## Règles

1. **Langues** : identifiants, docstrings, logs en anglais ; tout texte envoyé sur Discord en français.
2. **Logging** : `logger` (`botghast`) uniquement, jamais `print`. `info` à l'invocation et sur le résultat, `warning` pour une mauvaise utilisation, `error` dans les `except`.
3. **Erreurs** : ne jamais laisser une exception remonter ; répondre avec un message FR. Traiter explicitement `discord.NotFound` / `discord.Forbidden` quand on fetch des messages.
4. **DM** : ne pas appeler `ctx.guild.name` / `ctx.guild.me` sans vérifier `ctx.guild` (les commandes existantes ne le font pas — ne pas reproduire le bug).
5. **Données JSON** : relire le fichier à chaque appel (`open(..., encoding='utf-8')`), vérifier `os.path.exists`, puis appeler `validate_gifs_json` / `validate_quotes_json`. Pour un nouveau fichier de données, ajouter une variable d'env `XXX_FILE` avec défaut `data/xxx.json` + une fonction `validate_xxx_json` sur le même modèle.
6. **Limite Discord** : un message fait max 2000 caractères — tronquer / paginer les résultats longs (cf. `cherchecitation` qui limite à 3, `file` qui tronque à 2000).
7. Compatibilité Python 3.10 (version de la CI).

## Checklist de fin

- [ ] Ligne ajoutée dans le texte de `help_command` (`aide`) avec `{PREFIX}`.
- [ ] Commande documentée dans le `README.md` si pertinent (et nouvelle variable d'env dans la section Environment).
- [ ] Docstring du module en haut de `bot.py` mise à jour si la commande est majeure.
- [ ] `/lint` passe (flake8 comme la CI).
- [ ] Test manuel via `/run-bot` si un token est disponible — sinon au minimum `python -c "import ast; ast.parse(open('bot/src/bot.py', encoding='utf-8').read())"`.
