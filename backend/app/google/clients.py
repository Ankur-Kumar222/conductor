"""Build Google API service clients from a user's stored credentials, with
token auto-refresh (persisted) and retry/backoff on transient Google errors.
"""
from __future__ import annotations

import asyncio
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.google import oauth
from app.models import User

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, HttpError):
        status = getattr(exc.resp, "status", None)
        try:
            status = int(status) if status is not None else None
        except (TypeError, ValueError):
            status = None
        return status in _RETRYABLE_STATUS
    return isinstance(exc, (TimeoutError, ConnectionError))


@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
    retry=retry_if_exception(_is_retryable),
)
def execute(request: Any) -> Any:
    """Execute a googleapiclient request with retry/exponential backoff on transient errors."""
    return request.execute()


async def execute_async(request: Any) -> Any:
    """Run a blocking googleapiclient request off the event loop."""
    return await asyncio.to_thread(execute, request)


class GoogleServices:
    """Lazily-built gmail/calendar/drive clients bound to one user's credentials.

    On construction, refreshes the access token if needed. If it changed, the
    caller should persist `user` (fields are updated in place) and commit.
    """

    def __init__(self, user: User):
        self.user = user
        self.creds = oauth.credentials_from_tokens(
            user.google_access_token, user.google_refresh_token, user.scopes
        )
        self.token_refreshed = oauth.ensure_fresh(self.creds)
        if self.token_refreshed:
            user.google_access_token = self.creds.token
            user.token_expiry = oauth.expiry_utc(self.creds)
        self._gmail = None
        self._calendar = None
        self._drive = None

    @property
    def gmail(self):
        if self._gmail is None:
            self._gmail = build("gmail", "v1", credentials=self.creds, cache_discovery=False)
        return self._gmail

    @property
    def calendar(self):
        if self._calendar is None:
            self._calendar = build("calendar", "v3", credentials=self.creds, cache_discovery=False)
        return self._calendar

    @property
    def drive(self):
        if self._drive is None:
            self._drive = build("drive", "v3", credentials=self.creds, cache_discovery=False)
        return self._drive
