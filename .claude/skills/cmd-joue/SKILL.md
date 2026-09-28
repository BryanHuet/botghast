---
name: cmd-joue
description: Travailler sur la commande `joue` de BotGhast (play dans bot/src/bot.py) — joue l'audio d'une vidéo YouTube dans le salon vocal via yt-dlp + ffmpeg. Décrit aussi le pipeline audio commun aux commandes musicales. À utiliser pour modifier, débugger ou tester `?joue` ou la lecture audio.
---

# Commande `joue` (et pipeline audio)

**Code** : `play` dans `bot/src/bot.py` — `@bot.command(name='joue', ...)`.
**Usage Discord** : `?joue <lien YouTube>` (l'auteur doit être dans un salon vocal).

## Déroulé

1. Pas d'URL → « Donne-moi un lien YouTube : `?joue <lien>` ».
2. `ensure_voice(ctx)` : refuse en DM, si l'auteur n'est pas en vocal, si `ffmpeg` n'est pas dans le `PATH` ; sinon connecte/déplace le bot dans le salon de l'auteur et mémorise le salon texte (`music_channels`).
3. Sous le verrou de guilde (`music_locks`, le même que `play_next`, pour que deux `?joue` simultanés ne voient pas tous deux le lecteur libre) :
   - rien ne joue → `start_track` → embed `now_playing_embed` (titre cliquable, miniature, durée, chaîne, titre suivant, « Demandé par ») ;
   - sinon → `extract_audio_info` pour valider le lien et récupérer le titre, puis ajout **en fin de file** `{'query', 'label', 'url', 'duration', 'thumbnail', 'requester'}` → embed `queued_embed` (durée, position). La suite est gérée par `play_next`, comme pour `viking`.
4. `yt_dlp.utils.DownloadError` → vidéo invalide/privée (le lien n'est pas ajouté) ; `discord.ClientException` → échec du lancement ; autre → message générique.

**Playlist YouTube** : si l'URL contient `list=` (`is_youtube_playlist`), y compris `watch?v=...&list=...`, `queue_youtube_playlist` est appelé à la place des étapes 3-4 : `extract_youtube_playlist` (yt-dlp avec `YTDL_PLAYLIST_OPTIONS`, `extract_flat='in_playlist'`, donc rapide car les flux ne sont pas résolus) liste les vidéos dans l'ordre, en ignorant `[Private video]` / `[Deleted video]`. Toutes les vidéos sont ajoutées en fin de file → embed `playlist_embed` (nom cliquable, miniature, nombre de titres, durée totale), puis `play_next` (sans effet si un titre joue déjà). Les playlists « Mix » (`list=RD...`) sont générées par YouTube et limitées à quelques dizaines de titres.

`joue` **n'interrompt plus** la lecture : pour remplacer, `?suivant` ou `?stop`. `viking` en revanche vide la file (y compris les titres ajoutés par `joue`).

## Pipeline audio commun

- État par guilde (dicts globaux indexés par `guild.id`) : `music_queues` (deque de `{'query', 'label'}` + `url`, `duration`, `requester` optionnels), `music_channels`, `music_locks`, `now_playing` (dict de métadonnées renvoyé par `extract_audio_info`, + `requester`).
- Tous les messages musicaux sont des embeds (`MUSIC_COLOR` blurple, `MUSIC_ERROR_COLOR` rouge) construits par les helpers `now_playing_embed`, `queued_embed`, `playlist_embed`, `queue_embed`, `music_message_embed`. Pas d'emojis.
- `extract_audio_info(query)` : yt-dlp **bloquant**, appelé via `run_in_executor` ; ne télécharge rien, récupère l'URL du flux (`YTDL_OPTIONS` : `bestaudio`, `noplaylist`, `default_search='auto'`). Accepte aussi `ytsearch1:...`.
- `start_track` : `FFmpegPCMAudio` (`FFMPEG_OPTIONS` avec reconnexion) + `PCMVolumeTransformer(volume=0.5)`. Le callback `after` tourne dans le thread audio → `run_coroutine_threadsafe(play_next(guild), bot.loop)`.
- `play_next` / `_play_next_locked` : sous `asyncio.Lock` par guilde, dépile jusqu'à trouver une entrée lisible, annonce chaque titre dans `music_channels`, saute les entrées en erreur avec un embed rouge « Impossible de lire ... ».

## Dépendances

- `yt-dlp` et `PyNaCl` (voix) dans `requirements.txt` ; **ffmpeg** doit être installé (`winget install ffmpeg`).
- **Docker** : le `Dockerfile` n'installe pas ffmpeg → toutes les commandes musicales répondent « ffmpeg n'est pas installé ». Ajouter `apk add --no-cache ffmpeg` dans l'étape runtime si on veut la musique en conteneur.
- yt-dlp casse régulièrement quand YouTube change : premier réflexe sur une `DownloadError` inattendue → mettre à jour `yt-dlp` dans `requirements.txt`.
- Intent : `message_content` activé ; les états vocaux (`ctx.author.voice`) sont couverts par `Intents.default()`.

## Pièges

- Les URLs de flux yt-dlp expirent (~6 h) : ne pas les mettre en cache ; résoudre au moment de jouer (déjà le cas pour la file).
- `default_search='auto'` : un texte non-URL est traité comme une recherche, pas rejeté.
- Ne jamais appeler yt-dlp directement dans une coroutine (bloque la boucle et déconnecte le bot).

## Vérification

`/lint`, puis `/run-bot` avec ffmpeg installé : rejoindre un vocal, `?joue <url>`, puis `?joue <autre url>` pendant la lecture (doit s'ajouter en file, visible via `?file`, et démarrer à la fin du premier ou après `?suivant`), `?joue <lien invalide>` pendant la lecture (refusé, rien n'est ajouté), `?joue <lien playlist>` à vide puis pendant une lecture (tout doit arriver dans `?file`, dans l'ordre), et `?joue` hors vocal.
