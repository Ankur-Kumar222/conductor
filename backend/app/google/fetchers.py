"""Blocking fetchers that pull normalized, bounded item lists from Google APIs.

Each returns plain dicts ready to upsert into the corresponding *_cache table.
Run these off the event loop (asyncio.to_thread) — googleapiclient is synchronous.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from dateutil import parser as dateparser

from app.google.clients import GoogleServices, execute

FUTURE_WINDOW_DAYS = 120  # calendar: also index upcoming events ("next week")


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = dateparser.parse(value)
    except (ValueError, TypeError, OverflowError):
        return None
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def fetch_gmail(svc: GoogleServices, lookback_days: int, max_items: int) -> list[dict]:
    after = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime("%Y/%m/%d")
    gmail = svc.gmail
    ids: list[str] = []
    req = gmail.users().messages().list(userId="me", q=f"after:{after}", maxResults=500)
    while req is not None and len(ids) < max_items:
        resp = execute(req)
        ids.extend(m["id"] for m in resp.get("messages", []))
        req = gmail.users().messages().list_next(req, resp)
    ids = ids[:max_items]

    items: list[dict] = []
    for mid in ids:
        msg = execute(
            gmail.users().messages().get(
                userId="me", id=mid, format="metadata",
                metadataHeaders=["Subject", "From", "Date"],
            )
        )
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        internal = msg.get("internalDate")
        received = (
            datetime.fromtimestamp(int(internal) / 1000, tz=timezone.utc) if internal else None
        )
        items.append({
            "email_id": mid,
            "thread_id": msg.get("threadId"),
            "subject": headers.get("subject"),
            "sender": headers.get("from"),
            "body_preview": msg.get("snippet"),
            "labels": msg.get("labelIds"),
            "received_at": received,
        })
    return items


def fetch_gcal(svc: GoogleServices, lookback_days: int, max_items: int) -> list[dict]:
    now = datetime.now(timezone.utc)
    time_min = (now - timedelta(days=lookback_days)).isoformat()
    time_max = (now + timedelta(days=FUTURE_WINDOW_DAYS)).isoformat()
    cal = svc.calendar
    events: list[dict] = []
    req = cal.events().list(
        calendarId="primary", timeMin=time_min, timeMax=time_max,
        singleEvents=True, orderBy="startTime", maxResults=250,
    )
    while req is not None and len(events) < max_items:
        resp = execute(req)
        events.extend(resp.get("items", []))
        req = cal.events().list_next(req, resp)
    events = events[:max_items]

    items: list[dict] = []
    for e in events:
        start = e.get("start", {})
        end = e.get("end", {})
        attendees = [
            {"email": a.get("email"), "response": a.get("responseStatus")}
            for a in e.get("attendees", [])
        ]
        items.append({
            "event_id": e["id"],
            "title": e.get("summary"),
            "description": e.get("description"),
            "location": e.get("location"),
            "attendees": attendees,
            "organizer": (e.get("organizer") or {}).get("email"),
            "start_at": _parse_dt(start.get("dateTime") or start.get("date")),
            "end_at": _parse_dt(end.get("dateTime") or end.get("date")),
        })
    return items


def fetch_drive(svc: GoogleServices, lookback_days: int, max_items: int) -> list[dict]:
    drive = svc.drive
    files: list[dict] = []
    req = drive.files().list(
        pageSize=100, orderBy="modifiedTime desc", q="trashed=false",
        fields="nextPageToken, files(id,name,mimeType,modifiedTime,"
               "owners(emailAddress,displayName),webViewLink)",
    )
    while req is not None and len(files) < max_items:
        resp = execute(req)
        files.extend(resp.get("files", []))
        req = drive.files().list_next(req, resp)
    files = files[:max_items]

    items: list[dict] = []
    for f in files:
        owners = [
            {"email": o.get("emailAddress"), "name": o.get("displayName")}
            for o in f.get("owners", [])
        ]
        items.append({
            "file_id": f["id"],
            "name": f.get("name"),
            "mime_type": f.get("mimeType"),
            "content_preview": None,  # full content extraction is a later enhancement
            "owners": owners,
            "web_view_link": f.get("webViewLink"),
            "modified_at": _parse_dt(f.get("modifiedTime")),
        })
    return items
