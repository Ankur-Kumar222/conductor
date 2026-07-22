"""Google OAuth 2.0 web flow + credential helpers.

Single-user local demo: the callback upserts a `users` row and stores tokens.
Credentials auto-refresh on use; refreshed tokens are persisted by the caller.
"""
from __future__ import annotations

import os

# localhost redirect is http, and Google may return scopes in a different order.
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from app.config import settings

# Read + write across the three services (draft/confirm safety is enforced in app logic).
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.modify",  # read, draft, labels (no permanent delete)
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",  # full read/write
    "https://www.googleapis.com/auth/drive",  # full read/write incl. sharing
]

AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"


def _client_config() -> dict:
    return {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": AUTH_URI,
            "token_uri": TOKEN_URI,
            "redirect_uris": [settings.google_redirect_uri],
        }
    }


def build_flow(state: str | None = None) -> Flow:
    return Flow.from_client_config(
        _client_config(),
        scopes=SCOPES,
        redirect_uri=settings.google_redirect_uri,
        state=state,
    )


def authorization_url() -> tuple[str, str, str]:
    """Return (auth_url, state, code_verifier).

    PKCE is enabled, so the code_verifier generated here must be carried to the
    callback and set on the flow before exchanging the code.
    """
    flow = build_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        # show the account chooser so a user can switch/add a different Google account
        prompt="select_account consent",
    )
    return auth_url, state, flow.code_verifier


def exchange_code(code: str, state: str | None = None, code_verifier: str | None = None) -> Credentials:
    flow = build_flow(state=state)
    if code_verifier:
        flow.code_verifier = code_verifier
    flow.fetch_token(code=code)
    return flow.credentials


def credentials_from_tokens(access_token: str | None, refresh_token: str | None,
                            scopes: str | None) -> Credentials:
    return Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri=TOKEN_URI,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=scopes.split() if scopes else SCOPES,
    )


def ensure_fresh(creds: Credentials) -> bool:
    """Refresh the access token if expired. Returns True if the token changed."""
    if creds.valid:
        return False
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        return True
    return False


def expiry_utc(creds: Credentials) -> datetime | None:
    if creds.expiry is None:
        return None
    # google-auth stores naive UTC expiry; make it tz-aware.
    return creds.expiry.replace(tzinfo=timezone.utc)
