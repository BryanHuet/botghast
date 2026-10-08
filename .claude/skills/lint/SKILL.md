---
name: lint
description: Reproduire en local les vérifications flake8 de la CI GitHub de BotGhast et corriger les problèmes. À utiliser avant un commit/PR ou après une modification du code (bot/src) ou des tests.
---

# Lint comme la CI

La CI (`.github/workflows/python-app.yml`, Python 3.10 et 3.11) lance flake8 en deux passes, puis pytest (voir `/test`) :

```bash
# 1. Bloquant : erreurs de syntaxe et noms non définis
venv/bin/flake8 bot tests --count --select=E9,F63,F7,F82 --show-source --statistics
# 2. Bloquant aussi : style, complexité ≤ 10, lignes ≤ 127
venv/bin/flake8 bot tests --count --max-complexity=10 --max-line-length=127 --statistics
```

Cibler `bot tests` (la CI lance `flake8 .`, mais localement cela scannerait `venv/`). flake8 est dans `requirements-dev.txt`.

## Interprétation

- Les deux passes sont bloquantes : le moindre avertissement casse la CI. Corriger tout ce qui est signalé (espaces en fin de ligne `W291/W293`, lignes vides `E302/E303`, imports inutilisés `F401`, etc.).
- La CI scanne tout le dépôt, y compris `.claude/skills/*/scripts/` : pour être exhaustif, `venv/bin/flake8 . --exclude=venv,.git,__pycache__ --max-complexity=10 --max-line-length=127`.
- `C901` (complexité) : pour une nouvelle commande, extraire des helpers (dans `views.py`, `music.py`...) plutôt que d'empiler les `if`.

Après le lint, lancer les tests : `/test`.
