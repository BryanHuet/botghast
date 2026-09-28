---
name: lint
description: Reproduire en local les vérifications de la CI GitHub de BotGhast (flake8) et corriger les problèmes. À utiliser avant un commit/PR ou après une modification de bot/src/bot.py.
---

# Lint comme la CI

La CI (`.github/workflows/python-app.yml`, Python 3.10) n'exécute que flake8, en deux passes :

```bash
pip install flake8
# 1. Bloquant : erreurs de syntaxe et noms non définis
flake8 bot --count --select=E9,F63,F7,F82 --show-source --statistics
# 2. Informatif (exit-zero) : style, complexité ≤ 10, lignes ≤ 127
flake8 bot --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
```

Cibler `bot/` (la CI lance `flake8 .`, mais localement cela scannerait `venv/`). Si un venv existe, utiliser `venv/Scripts/python -m flake8`.

## Interprétation

- Passe 1 en échec = la CI casse → corriger impérativement.
- Passe 2 : ne corriger que les avertissements **dans le code modifié** (espaces en fin de ligne `W291/W293`, lignes vides `E302/E303`, imports inutilisés `F401`, etc.). Ne pas reformater tout le fichier sans demande : le code existant contient déjà des warnings (ex. trailing whitespace).
- `C901` (complexité) : les commandes existantes sont proches de la limite ; pour une nouvelle commande, extraire des helpers plutôt que d'empiler les `if`.

Il n'y a pas de tests automatisés (étape pytest commentée dans la CI). Si des tests sont ajoutés, les placer dans `tests/` et décommenter l'étape pytest.
