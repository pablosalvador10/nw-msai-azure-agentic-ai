"""Sign in with GitHub through a GitHub App, and keep the result in a signed cookie.

/auth/login sends the browser to GitHub. GitHub sends it back to /auth/callback with a one-time
code. The site exchanges the code for a user token, reads the user's login, and asks GitHub
whether that user can read the course repository. The token is then dropped: the session cookie
holds only the login, signed with HMAC, so it cannot be forged or edited in the browser.
"""

import base64
import binascii
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx2

GITHUB = "https://github.com"
GITHUB_API = "https://api.github.com"


class GitHubError(Exception):
    """GitHub refused the sign-in or did not answer."""


@dataclass(frozen=True)
class User:
    login: str
    id: int


class Signer:
    """Signs small JSON values with an expiry. Each purpose gets its own key."""

    def __init__(self, secret: bytes, purpose: str) -> None:
        if not secret:
            raise ValueError("A signing secret is required.")
        self._key = hmac.new(secret, f"lectures:{purpose}".encode(), hashlib.sha256).digest()

    def dumps(self, data: dict[str, Any], ttl_s: int) -> str:
        body = json.dumps({**data, "exp": int(time.time()) + ttl_s}, separators=(",", ":")).encode()
        payload = _b64(body)
        return f"{payload}.{self._sign(payload)}"

    def loads(self, token: str | None) -> dict[str, Any] | None:
        """The data, or None when the token is missing, tampered with, malformed or expired."""
        if not token or token.count(".") != 1:
            return None
        payload, signature = token.split(".")
        if not hmac.compare_digest(signature.encode(), self._sign(payload).encode()):
            return None
        try:
            data = json.loads(_unb64(payload))
        except (ValueError, binascii.Error):
            return None
        if not isinstance(data, dict) or not isinstance(data.get("exp"), int) or data["exp"] < time.time():
            return None
        return data

    def _sign(self, payload: str) -> str:
        return _b64(hmac.new(self._key, payload.encode(), hashlib.sha256).digest())


def pkce_challenge(verifier: str) -> str:
    """S256 code challenge (RFC 7636): proves the callback comes from the browser that started sign-in."""
    return _b64(hashlib.sha256(verifier.encode()).digest())


class GitHub:
    """The three GitHub calls sign-in needs. Tests replace this class with a fake."""

    def __init__(self, client_id: str, client_secret: str, timeout: float = 10.0) -> None:
        self.client_id = client_id
        self._secret = client_secret
        self._http = httpx2.Client(timeout=timeout, headers={"User-Agent": "lectures-site"})

    def authorize_url(self, redirect_uri: str, state: str, challenge: str) -> str:
        query = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "allow_signup": "false",
        }
        return f"{GITHUB}/login/oauth/authorize?{urlencode(query)}"

    def exchange(self, code: str, redirect_uri: str, verifier: str) -> str:
        """Trade the one-time code for a user access token."""
        response = self._http.post(
            f"{GITHUB}/login/oauth/access_token",
            data={
                "client_id": self.client_id,
                "client_secret": self._secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": verifier,
            },
            headers={"Accept": "application/json"},
        )
        body = _json(response)
        token = body.get("access_token")
        if response.status_code != 200 or not isinstance(token, str) or not token:
            raise GitHubError(f"GitHub did not issue a token: {body.get('error', response.status_code)}")
        return token

    def user(self, token: str) -> User:
        response = self._http.get(f"{GITHUB_API}/user", headers=_api_headers(token))
        body = _json(response)
        if response.status_code != 200 or not isinstance(body.get("login"), str) or not isinstance(body.get("id"), int):
            raise GitHubError(f"GitHub did not return the user: {response.status_code}")
        return User(login=body["login"], id=body["id"])

    def can_read(self, token: str, repo: str) -> bool:
        """True when this user can see the repository (and the GitHub App is installed on it)."""
        # A renamed repository answers 301 at its old name: follow it to the new one.
        response = self._http.get(f"{GITHUB_API}/repos/{repo}", headers=_api_headers(token), follow_redirects=True)
        if response.status_code == 200:
            return True
        if response.status_code in (403, 404):
            return False
        raise GitHubError(f"GitHub answered {response.status_code} for the repository check.")


def _api_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _json(response: httpx2.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
