"""
Spotify Web API client: reads the tracks of a playlist (audio itself comes from YouTube).
"""

import re
import time

import aiohttp

from config import SPOTIFY_API, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN
from log import logger

spotify_token = {'access_token': None, 'expires_at': 0, 'refresh_token': SPOTIFY_REFRESH_TOKEN}


def parse_spotify_playlist_id(value):
    """
    Extract a Spotify playlist ID from a URL, a URI or a raw ID.

    Args:
        value: "https://open.spotify.com/playlist/<id>?si=...", "spotify:playlist:<id>" or "<id>"

    Returns:
        str: The playlist ID, or None if the value is not recognized
    """
    match = re.search(r'playlist[/:]([A-Za-z0-9]{22})', value)
    if match:
        return match.group(1)
    if re.fullmatch(r'[A-Za-z0-9]{22}', value):
        return value
    return None


async def get_spotify_access_token(session):
    """
    Get a Spotify access token, refreshing it with the stored refresh token when expired.

    Args:
        session: aiohttp.ClientSession used for the request

    Returns:
        str: A valid access token

    Raises:
        RuntimeError: If credentials are missing or Spotify refuses the refresh
    """
    if spotify_token['access_token'] and time.time() < spotify_token['expires_at']:
        return spotify_token['access_token']

    if not (SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET and spotify_token['refresh_token']):
        raise RuntimeError("SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET and SPOTIFY_REFRESH_TOKEN must be set")

    logger.info("Refreshing Spotify access token")
    auth = aiohttp.BasicAuth(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)
    data = {'grant_type': 'refresh_token', 'refresh_token': spotify_token['refresh_token']}
    async with session.post('https://accounts.spotify.com/api/token', data=data, auth=auth) as resp:
        payload = await resp.json()
        if resp.status != 200:
            raise RuntimeError(f"Spotify token refresh failed ({resp.status}): {payload}")

    spotify_token['access_token'] = payload['access_token']
    # Refresh one minute early to avoid using a token that expires mid-request
    spotify_token['expires_at'] = time.time() + payload.get('expires_in', 3600) - 60
    if payload.get('refresh_token'):
        # Spotify may rotate the refresh token: keep the new one for this session
        spotify_token['refresh_token'] = payload['refresh_token']
        logger.warning("Spotify returned a new refresh token; update SPOTIFY_REFRESH_TOKEN if the old one stops working")
    return spotify_token['access_token']


async def fetch_spotify_playlist(playlist_id):
    """
    Fetch the name and all tracks of a Spotify playlist owned by the authorized account.

    Args:
        playlist_id: Spotify playlist ID

    Returns:
        tuple: (playlist, tracks) where playlist is a {'name', 'url', 'thumbnail'} dict
        and tracks is a list of {'query', 'label', 'url', 'duration'} dicts

    Raises:
        RuntimeError: If the Spotify API returns an error
    """
    tracks = []
    async with aiohttp.ClientSession() as session:
        token = await get_spotify_access_token(session)
        headers = {'Authorization': f'Bearer {token}'}

        async with session.get(f'{SPOTIFY_API}/playlists/{playlist_id}', headers=headers,
                               params={'fields': 'name,images,external_urls'}) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Spotify playlist request failed ({resp.status}): {await resp.text()}")
            data = await resp.json()
        images = data.get('images') or []
        playlist = {
            'name': data.get('name', playlist_id),
            'url': (data.get('external_urls') or {}).get('spotify'),
            'thumbnail': images[0].get('url') if images else None,
        }

        url = f'{SPOTIFY_API}/playlists/{playlist_id}/items'
        params = {'limit': 50, 'additional_types': 'track'}
        while url:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Spotify items request failed ({resp.status}): {await resp.text()}")
                page = await resp.json()
            for entry in page.get('items', []):
                # 'track' is the deprecated name of 'item'
                track = entry.get('item') or entry.get('track')
                if not track or track.get('type') != 'track' or not track.get('name'):
                    continue
                artists = ', '.join(a['name'] for a in track.get('artists', []) if a.get('name'))
                label = f"{track['name']} - {artists}" if artists else track['name']
                duration_ms = track.get('duration_ms')
                tracks.append({'query': f"ytsearch1:{track['name']} {artists}", 'label': label,
                               'url': (track.get('external_urls') or {}).get('spotify'),
                               'duration': duration_ms / 1000 if duration_ms else None})
            # 'next' already contains the query parameters
            url = page.get('next')
            params = None

    logger.info(f"Fetched {len(tracks)} tracks from Spotify playlist '{playlist['name']}'")
    return playlist, tracks
