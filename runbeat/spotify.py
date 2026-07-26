from __future__ import annotations

import base64
import hashlib
import secrets
from urllib.parse import urlencode

import requests

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_URL = "https://api.spotify.com/v1"
SCOPES = "playlist-modify-private playlist-modify-public user-read-private"


def create_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return verifier, challenge


def authorization_url(client_id: str, redirect_uri: str, challenge: str, state: str) -> str:
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
        "show_dialog": "true",
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def exchange_code(client_id: str, redirect_uri: str, code: str, verifier: str) -> dict:
    response = requests.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": verifier,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def api_request(method: str, path: str, token: str, **kwargs) -> dict:
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    response = requests.request(method, f"{API_URL}{path}", headers=headers, timeout=30, **kwargs)
    if response.status_code == 429:
        reason = ""
        try:
            reason = response.json().get("reason", "")
        except ValueError:
            pass
        raise RuntimeError(f"Spotify rate/quota limit reached{f': {reason}' if reason else ''}.")
    response.raise_for_status()
    return response.json() if response.content else {}


def current_user(token: str) -> dict:
    return api_request("GET", "/me", token)


def create_playlist(token: str, name: str, description: str) -> dict:
    return api_request(
        "POST",
        "/me/playlists",
        token,
        json={"name": name, "description": description, "public": False},
    )


def replace_playlist_items(token: str, playlist_id: str, uris: list[str]) -> None:
    first_batch = uris[:100]
    api_request("PUT", f"/playlists/{playlist_id}/items", token, json={"uris": first_batch})
    for start in range(100, len(uris), 100):
        api_request(
            "POST",
            f"/playlists/{playlist_id}/items",
            token,
            json={"uris": uris[start : start + 100]},
        )
