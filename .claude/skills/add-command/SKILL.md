---
name: add-command
description: Ajouter ou modifier une commande Discord de BotGhast (bot/src/bot.py) en respectant les conventions du projet (logging, textes dans messages.json, gestion d'erreurs, aide, README, tests). À utiliser dès qu'on crée/renomme/modifie une commande du bot.
---

# Ajouter une commande BotGhast

Les commandes vivent dans `bot/src/bot.py`, qui ne contient **que** les commandes. La logique va dans le module adapté (`views.py` pour construire un texte ou un embed, `datastore.py` pour un fichier de données, `music.py` pour la lecture...). Placer la commande après les existantes, avant le bloc `if __name__ == "__main__":`.

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
    server = guild_name(ctx)
    logger.info(f"Command 'macommande' invoked by {ctx.author} in channel {ctx.channel} on server {server}")

    if not arg:
        await ctx.reply(t('macommande.no_arg'))
        return

    try:
        ...
        await ctx.send(t('macommande.result', value=...))
    except Exception as e:
        logger.error(f"Error in macommande command: {e} on server {server}")
        await ctx.reply(t('macommande.error'))
```

Et dans `bot/data/messages.json`, une section du même nom :

```json
"macommande": {
  "no_arg": "Donne-moi ... : `{prefix}macommande <arg>`",
  "result": "...{value}...",
  "error": "Une erreur est survenue ..."
}
```

## Règles

1. **Langues** : identifiants, docstrings, logs en anglais ; tout texte affiché sur Discord en français, **dans `messages.json`** via `t('section.cle', param=...)` (`{prefix}` est toujours disponible). Jamais de texte en dur dans le code.
2. **Logging** : `logger` (`botghast`) uniquement, jamais `print`. `info` à l'invocation et sur le résultat, `warning` pour une mauvaise utilisation, `error` dans les `except`.
3. **Erreurs** : ne jamais laisser une exception remonter ; répondre avec un message FR. Traiter explicitement `discord.NotFound` / `discord.Forbidden` quand on récupère des messages.
4. **Message privé** : `guild_name(ctx)` pour les logs ; ne pas lire `ctx.guild.xxx` sans vérifier `ctx.guild`. Commande réservée aux serveurs → `t('common.server_only')`. Commande vocale → `music.ensure_voice(ctx)` fait toutes les vérifications.
5. **Arguments** : toujours une valeur par défaut (`arg: str = None`) et un message FR si absent ; sinon discord.py lève `MissingRequiredArgument` avant la fonction et l'utilisateur ne reçoit rien.
6. **Données JSON** : passer par `datastore` (`load_gifs`, `load_quotes`), qui relit et valide le fichier à chaque appel. Pour un nouveau fichier : variable `XXX_FILE` dans `config.py` (défaut dans `DATA_DIR`) + `load_xxx` / `validate_xxx_json` sur le même modèle.
7. **Limites Discord** : 2000 caractères par message, 4096 pour la description d'un embed. Limiter les résultats (valeur dans `style` de `messages.json`, comme `search_results`).
8. Compatibilité Python 3.10 (version minimale de la CI).

## Checklist de fin

- [ ] Ligne ajoutée dans `aide.commands` de `messages.json` (`usage` commençant par le nom de la commande).
- [ ] Ligne ajoutée dans un tableau des commandes du `README.md` (format `` | `?nom ...` | ... | ``), et nouvelle variable d'env dans la section Environment.
- [ ] Docstring du module en haut de `bot.py` mise à jour.
- [ ] Nom ajouté à `EXPECTED_COMMANDS` dans `tests/test_smoke.py`.
- [ ] Tests fonctionnels dans `tests/functional/` : cas nominal, message privé, chaque message d'erreur (voir `/test`).
- [ ] `/lint` et `/test` passent (les tests de `tests/contract/` vérifient les clés, paramètres, `aide` et README).
- [ ] Un skill `/cmd-<nom>` si la commande a des pièges à retenir.
