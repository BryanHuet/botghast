# botghast
Personal Bot Discord

## Requirements
- Python >= 3.10
- [FFmpeg](https://ffmpeg.org/) for the voice commands

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
MESSAGES_FILE=path-to-custom-messages-file
```
`BOT_PREFIX` defaults to `?`. The data files default to `bot/data/gifs.json`, `bot/data/quotes.json` and `bot/data/messages.json`, whatever the working directory. The Spotify variables used by `?viking` are listed in `.env.example` (see [Spotify setup](#spotify-setup)).

## Execution
```bash
venv/bin/python bot/src/bot.py
```

## Tests
```bash
venv/bin/pip install -r requirements-dev.txt
venv/bin/pytest                # all tests, no network nor Discord token needed
venv/bin/pytest --cov          # with coverage report, fails under 95% (as in the CI)
venv/bin/flake8 bot tests --max-line-length=127
```
Tests live in `tests/`:
- `unit/`: one file per module, network calls mocked
- `functional/`: every command run end to end with fake Discord objects (`fakes.py`), YouTube and FFmpeg replaced by fakes
- `contract/`: consistency between the code, `bot/data/messages.json`, this README and the data files (every text used exists and gets its placeholders, `?aide` and the tables below list exactly the registered commands)

`conftest.py` isolates the configuration from your `.env`. The CI runs flake8 and pytest on Python 3.10 and 3.11.

## Docker
```bash
docker build -t botghast . && docker run --env-file .env botghast
```

## Texts
Every text sent on Discord (in French), the embed colours and the display limits are in `bot/data/messages.json`. The file is reloaded when it changes, no restart needed (in Docker, rebuild the image or mount the file with `MESSAGES_FILE`).

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
