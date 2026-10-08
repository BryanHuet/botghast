---
name: cmd-viking
description: Travailler sur la commande `viking` de BotGhast (spotify dans bot/src/bot.py) — charge une playlist Spotify en file (ordre aléatoire) et joue chaque titre depuis YouTube. À utiliser pour modifier, débugger ou tester `?viking`, l'auth Spotify ou bot/src/spotify_auth.py.
---

# Commande `viking`

**Code** : `spotify` dans `bot/src/bot.py` — `@bot.command(name='viking', ...)`. Helpers dans `bot/src/spotify_client.py` : `parse_spotify_playlist_id`, `get_spotify_access_token`, `fetch_spotify_playlist`.
**Textes** : section `viking` de `bot/data/messages.json`.
**Usage Discord** : `?viking` (playlist `SPOTIFY_PLAYLIST`) ou `?viking <lien/URI/ID de playlist>`.

## Déroulé

1. `parse_spotify_playlist_id` accepte `https://open.spotify.com/playlist/<id>?si=...`, `spotify:playlist:<id>` ou l'ID brut (22 caractères). Invalide → `viking.no_playlist`.
2. `ensure_voice` (voir `/cmd-joue`).
3. `fetch_spotify_playlist` : nom de la playlist puis pagination de `/playlists/{id}/items` (50 par page, champ `item` ou l'ancien `track`), ne garde que les `type == 'track'`. Chaque titre devient `{'query': 'ytsearch1:<titre> <artistes>', 'label': '<titre> - <artistes>'}`.
4. Mélange, **remplace** la file de la guilde, annonce via `playlist_embed` (nom et pochette de la playlist, nombre de titres, durée totale, ordre aléatoire).
5. Si quelque chose joue → `stop()` (le callback `after` lance la file) ; sinon `play_next`.
6. Aucun titre → `viking.empty_playlist` ; `RuntimeError` (API/identifiants) → `viking.api_error` ; autre → `viking.error`.

L'audio ne vient **jamais** de Spotify : chaque titre est recherché sur YouTube au moment de sa lecture (1ʳᵉ réponse de `ytsearch1`, donc parfois une mauvaise version).

## Configuration (`.env`, voir `.env.example`)

- `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN` (obligatoires), `SPOTIFY_PLAYLIST` (optionnel).
- Refresh token obtenu une fois avec `python bot/src/spotify_auth.py` (redirect URI `http://127.0.0.1:8888/callback` déclarée dans le dashboard Spotify). Ne jamais afficher ces valeurs.
- Depuis mars 2026, une app en mode développement ne lit que les playlists **appartenant au compte autorisé**, et le propriétaire de l'app doit être **Premium**. Une playlist d'un autre compte → 403 ou 0 titre (`viking.empty_playlist`).

## Pièges

- Le token d'accès est mis en cache dans `spotify_token` (mémoire) et rafraîchi 60 s avant expiration. Si Spotify renvoie un nouveau refresh token, il n'est gardé qu'en mémoire (warning dans les logs) → mettre à jour `.env` si l'ancien cesse de marcher.
- Une grosse playlist = beaucoup de pages API mais la résolution YouTube est paresseuse (une piste à la fois) : ne pas précharger toute la file avec yt-dlp.

## Vérification

`/test` (`tests/unit/test_spotify_client.py` avec aioresponses, `tests/functional/test_cmd_music.py::TestViking`), `/lint`, puis `/run-bot` avec ffmpeg + identifiants Spotify : `?viking`, `?file`, `?suivant`, et `?viking <lien invalide>`.
