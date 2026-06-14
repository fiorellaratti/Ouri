from __future__ import annotations

import json
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from ouri.config import TOKENS_PATH, settings

AUTH_URL = "https://cloud.ouraring.com/oauth/authorize"
TOKEN_URL = "https://api.ouraring.com/oauth/token"
DEFAULT_SCOPES = "daily personal heartrate workout tag spo2Daily"


class TokenStore:
    def __init__(self, path: Path = TOKENS_PATH) -> None:
        self.path = path

    def load(self) -> dict | None:
        if not self.path.exists():
            return None
        return json.loads(self.path.read_text())

    def save(self, tokens: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(tokens, indent=2))
        self.path.chmod(0o600)

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()


class OAuthClient:
    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
        store: TokenStore | None = None,
    ) -> None:
        self.client_id = client_id or settings.oura_client_id
        self.client_secret = client_secret or settings.oura_client_secret
        self.redirect_uri = redirect_uri or settings.oura_redirect_uri
        self.store = store or TokenStore()

    def authorization_url(self, scopes: str = DEFAULT_SCOPES) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": scopes,
        }
        return f"{AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str) -> dict:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
        }
        response = httpx.post(TOKEN_URL, data=data, timeout=30.0)
        response.raise_for_status()
        tokens = response.json()
        self.store.save(tokens)
        return tokens

    def refresh(self, refresh_token: str | None = None) -> dict:
        stored = self.store.load() or {}
        token = refresh_token or stored.get("refresh_token")
        if not token:
            raise RuntimeError("No refresh token. Run ouri-auth first.")

        data = {
            "grant_type": "refresh_token",
            "refresh_token": token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        response = httpx.post(TOKEN_URL, data=data, timeout=30.0)
        response.raise_for_status()
        tokens = response.json()
        if "refresh_token" not in tokens and token:
            tokens["refresh_token"] = token
        self.store.save(tokens)
        return tokens

    def get_access_token(self) -> str:
        stored = self.store.load()
        if not stored or "access_token" not in stored:
            raise RuntimeError("Not authenticated. Run: ouri-auth")

        # Try current token; refresh on 401 is handled by OuraClient
        return stored["access_token"]

    def run_interactive_flow(self, scopes: str = DEFAULT_SCOPES) -> dict:
        if not self.client_id or not self.client_secret:
            raise RuntimeError("Set OURA_CLIENT_ID and OURA_CLIENT_SECRET in .env")

        parsed = urlparse(self.redirect_uri)
        port = parsed.port or 8080
        auth_code: dict[str, str] = {}

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                query = parse_qs(urlparse(self.path).query)
                if "code" in query:
                    auth_code["code"] = query["code"][0]
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<h1>Ouri authorized!</h1><p>You can close this tab.</p>")
                else:
                    self.send_response(400)
                    self.end_headers()

            def log_message(self, format: str, *args: object) -> None:
                pass

        url = self.authorization_url(scopes)
        print(f"Opening browser for Oura authorization...\n{url}")
        webbrowser.open(url)

        server = HTTPServer(("localhost", port), CallbackHandler)
        print(f"Waiting for callback on {self.redirect_uri} ...")
        server.handle_request()

        if "code" not in auth_code:
            raise RuntimeError("Authorization failed — no code received.")

        tokens = self.exchange_code(auth_code["code"])
        print(f"Tokens saved to {self.store.path}")
        return tokens
