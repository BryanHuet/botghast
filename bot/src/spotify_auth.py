"""
One-time Spotify authorization helper for BotGhast.

Opens the Spotify consent page, catches the redirect on a local HTTP server and
prints the refresh token to put in SPOTIFY_REFRESH_TOKEN.

Prerequisites:
- A Spotify app created on https://developer.spotify.com/dashboard
- Redirect URI of the app set to http://127.0.0.1:8888/callback
- SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET set in .env

Usage:
    python bot/src/spotify_auth.py
"""

import base64
import json
import logging
import os
import secrets
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('botghast.spotify_auth')

REDIRECT_URI = 'http://127.0.0.1:8888/callback'
SCOPES = 'playlist-read-private playlist-read-collaborative'


class CallbackHandler(BaseHTTPRequestHandler):
    """Capture the authorization code sent by Spotify on the redirect URI."""

    code = None
    error = None
    expected_state = None

    def do_GET(self):
        """Handle the redirect from Spotify and store the code or the error."""
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if query.get('state', [None])[0] != CallbackHandler.expected_state:
            CallbackHandler.error = 'state mismatch'
        elif 'error' in query:
            CallbackHandler.error = query['error'][0]
        else:
            CallbackHandler.code = query.get('code', [None])[0]

        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        message = 'Autorisation reçue, tu peux fermer cet onglet.' if CallbackHandler.code else 'Autorisation refusée.'
        self.wfile.write(message.encode('utf-8'))

    def log_message(self, format, *args):
        """Silence the default HTTP request logging."""


def exchange_code(client_id, client_secret, code):
    """
    Exchange an authorization code for access and refresh tokens.

    Args:
        client_id: Spotify app client ID
        client_secret: Spotify app client secret
        code: Authorization code received on the redirect URI

    Returns:
        dict: Spotify token response
    """
    credentials = base64.b64encode(f'{client_id}:{client_secret}'.encode()).decode()
    body = urllib.parse.urlencode({
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
    }).encode()
    request = urllib.request.Request(
        'https://accounts.spotify.com/api/token',
        data=body,
        headers={
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def main():
    """Run the authorization flow and print the refresh token."""
    client_id = os.getenv('SPOTIFY_CLIENT_ID')
    client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
    if not client_id or not client_secret:
        logger.error('SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in .env')
        return

    CallbackHandler.expected_state = secrets.token_urlsafe(16)
    auth_url = 'https://accounts.spotify.com/authorize?' + urllib.parse.urlencode({
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': REDIRECT_URI,
        'scope': SCOPES,
        'state': CallbackHandler.expected_state,
    })

    logger.info('Opening the Spotify consent page. If the browser does not open, visit:')
    logger.info(auth_url)
    webbrowser.open(auth_url)

    server = HTTPServer(('127.0.0.1', 8888), CallbackHandler)
    while CallbackHandler.code is None and CallbackHandler.error is None:
        server.handle_request()
    server.server_close()

    if CallbackHandler.error:
        logger.error(f'Authorization failed: {CallbackHandler.error}')
        return

    tokens = exchange_code(client_id, client_secret, CallbackHandler.code)
    logger.info('\nAdd this line to your .env file:\n')
    logger.info(f"SPOTIFY_REFRESH_TOKEN={tokens['refresh_token']}")


if __name__ == '__main__':
    main()
