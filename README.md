# botghast
Personal Bot Discord

## Requirements
- Python >= 3.8

## Installation
1. Clone this repository to your local machine:
```bash
git clone https://github.com/BryanHuet/botghast.git
```
2. Create a python environment
```bash
python -m venv venv
```
3. Install all required packages
```bash
venv/bin/pip install -r requirements.txt
```

## Environment
Create in the root folder a **.env** file such as
```.env
DISCORD_TOKEN=token-bot-discord-api
BOT_PREFIX=?
GIFS_FILE=path-to-custom-gifs-file
QUOTES_FILE=path-to-custom-quotes-file
```
`BOT_PREFIX` defaults to `?`. The Spotify variables used by `?viking` are listed in `.env.example` (see [Spotify setup](#spotify-setup)).

## Execution
```bash
venv/bin/python bot/src/bot.py
```

## Tests
```bash
venv/bin/pip install -r requirements-dev.txt
venv/bin/pytest                # unit and functional tests, no network nor Discord token needed
venv/bin/pytest --cov          # with coverage report
```
Tests live in `tests/` (`conftest.py` isolates the configuration from your `.env`, `fakes.py` provides fake Discord objects). The CI runs flake8 and pytest on Python 3.10 and 3.11.

## Docker
```bash
docker build -t botghast && docker run --env-file .env botghast
```





## Commands
| Command | Description |
|---|---|
| `?aide` | Show the list of commands |
| `?donneavis` | Reply to a message with this command: the bot answers it with a random GIF |
| `?citation` | Send a random philosophical quote |
| `?cherchecitation <keyword>` | Search quotes by keyword (quote text or author), first 3 results |

### Voice commands
| Command | Description |
|---|---|
| `?joue <youtube-url>` | Play a YouTube video or playlist (URL with `list=`), or add it to the queue if a track is already playing |
| `?viking [playlist-url]` | Queue a Spotify playlist in random order (defaults to `SPOTIFY_PLAYLIST`) |
| `?suivant` | Skip to the next track |
| `?file` | Show the current track and the next ones |
| `?stop` | Stop, clear the queue and leave the voice channel |

They require [FFmpeg](https://ffmpeg.org/) available in the `PATH` (e.g. `winget install ffmpeg`, `apt install ffmpeg`, `apk add ffmpeg`). The Docker image does not install it yet.

### Spotify setup
Audio is not streamed from Spotify: the bot reads the track names with the Spotify Web API, then plays each track from YouTube.
Since March 2026, Spotify apps in development mode only return the tracks of playlists **owned by the authorized account**, and the app owner needs a **Premium** subscription.

1. Create an app on the [Spotify dashboard](https://developer.spotify.com/dashboard) (Web API), with the redirect URI `http://127.0.0.1:8888/callback`.
2. Add `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` to `.env`.
3. Run once, log in with the account owning the playlist and copy the printed line into `.env`:
```bash
venv/bin/python bot/src/spotify_auth.py
```
4. Optionally set `SPOTIFY_PLAYLIST` (URL or ID) to play it with a bare `?viking`.
