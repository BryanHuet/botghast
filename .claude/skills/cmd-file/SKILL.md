---
name: cmd-file
description: Travailler sur la commande `file` de BotGhast (show_queue dans bot/src/bot.py) — affiche le titre en cours et la file d'attente musicale. À utiliser pour modifier, débugger ou tester `?file`.
---

# Commande `file`

**Code** : `show_queue` dans `bot/src/bot.py` — `@bot.command(name='file', ...)`.
**Usage Discord** : `?file`.

## Déroulé

1. En DM → « Cette commande ne fonctionne que sur un serveur. »
2. Lit `now_playing[guild.id]` (dict de métadonnées de la piste en cours : `title`, `url`, `thumbnail`, `duration`, `uploader`, `requester`) et `music_queues[guild.id]`.
3. Rien des deux → embed « La file est vide. Lance un titre avec `?joue <lien>`. »
4. Sinon → `queue_embed` : champ « En cours » (lien + durée, miniature), description « À suivre » (10 premiers, liens masqués + durées), pied de page avec le nombre de titres et la durée totale connue.
   (`label` des entrées : `titre - artistes` pour Spotify, le titre YouTube pour `joue`.)
5. Les labels sont tronqués à `MAX_LABEL_LENGTH` (90) pour rester sous les limites des embeds.

Structure de l'état : voir `/cmd-joue`.

## Pièges

- Lecture seule : ne jamais modifier la file ici. `get_queue` crée une deque vide si la guilde n'en a pas — sans effet gênant.
- `now_playing` affiche le **titre YouTube résolu**, alors que la file affiche le **label Spotify** : les deux formats diffèrent, c'est voulu (le titre YouTube n'est connu qu'au moment de la lecture).
- `now_playing` n'est vidé qu'en fin de file ou par `arrete` ; si le bot est déconnecté manuellement du vocal, un titre fantôme peut rester jusqu'au prochain `play_next`.
- Le `[:2000]` peut couper au milieu d'une ligne ; réduire le nombre d'entrées plutôt que de dépasser.

## Vérification

`/lint`, puis `/run-bot` : `?file` à vide, après `?joue`, et après `?viking` (plus de 10 titres).
