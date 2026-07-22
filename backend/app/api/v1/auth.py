"""Google OAuth endpoints: start consent, handle callback, report status."""
from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from googleapiclient.discovery import build
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.deps import USER_COOKIE, get_current_user
from app.google import oauth
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/google")
async def google_login() -> RedirectResponse:
    """Redirect the browser to Google's consent screen."""
    auth_url, state, code_verifier = oauth.authorization_url()
    resp = RedirectResponse(auth_url)
    resp.set_cookie("oauth_state", state, httponly=True, max_age=600, samesite="lax")
    resp.set_cookie("oauth_verifier", code_verifier, httponly=True, max_age=600, samesite="lax")
    return resp


@router.get("/google/callback")
async def google_callback(
    response: Response,
    code: str = Query(...),
    state: str | None = Query(default=None),
    oauth_state: str | None = Cookie(default=None),
    oauth_verifier: str | None = Cookie(default=None),
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    """Exchange the auth code for tokens, upsert the user, redirect to the frontend."""
    if oauth_state and state and oauth_state != state:
        raise HTTPException(status_code=400, detail="OAuth state mismatch")
    try:
        creds = oauth.exchange_code(code, state=state, code_verifier=oauth_verifier)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed: {exc}") from exc

    # Resolve the account email via the userinfo endpoint.
    email = None
    try:
        info = build("oauth2", "v2", credentials=creds, cache_discovery=False).userinfo().get().execute()
        email = info.get("email")
    except Exception:  # noqa: BLE001
        pass

    user: User | None = None
    if email:
        user = (
            await session.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
    if user is None:
        user = User(email=email)
        session.add(user)

    user.google_access_token = creds.token
    user.google_refresh_token = creds.refresh_token or user.google_refresh_token
    user.token_expiry = oauth.expiry_utc(creds)
    user.scopes = " ".join(creds.scopes or oauth.SCOPES)
    await session.commit()
    await session.refresh(user)

    # Once the frontend exists (P5) it will be running and we hand off to it;
    # until then, show a self-contained success page so the flow is verifiable.
    frontend_up = await _frontend_available()
    if frontend_up:
        resp: Response = RedirectResponse(f"{settings.frontend_url}/?connected=1")
    else:
        resp = HTMLResponse(_success_page(user.email, str(user.id)))
    resp.set_cookie(
        USER_COOKIE, str(user.id), httponly=False, max_age=60 * 60 * 24 * 30, samesite="lax"
    )
    return resp


async def _frontend_available() -> bool:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=0.4) as client:
            await client.get(settings.frontend_url)
        return True
    except Exception:  # noqa: BLE001
        return False


def _success_page(email: str | None, user_id: str) -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Conductor — Connected</title>
    <style>body{{font-family:-apple-system,system-ui,sans-serif;background:#0b0f19;color:#e6e9f0;
    display:flex;min-height:100vh;align-items:center;justify-content:center}}
    .card{{background:#151b2b;padding:40px 48px;border-radius:16px;max-width:520px;
    box-shadow:0 10px 40px rgba(0,0,0,.4)}} .ok{{color:#5eead4;font-size:15px}}
    code{{background:#0b0f19;padding:2px 8px;border-radius:6px;color:#a5b4fc}}
    h1{{margin:0 0 12px;font-size:22px}} p{{line-height:1.6;color:#aeb6c8}}</style></head>
    <body><div class="card"><h1>✅ Google Workspace connected</h1>
    <p class="ok">Conductor now has access to Gmail, Calendar &amp; Drive.</p>
    <p>Account: <code>{email or "unknown"}</code><br>User id: <code>{user_id}</code></p>
    <p>You can close this tab. Next: trigger a sync from the API or (soon) the Conductor UI.</p>
    </div></body></html>"""


@router.post("/logout")
async def logout(response: Response) -> dict:
    """Clear the local session cookie. The frontend also clears its stored user id.
    Google authorization itself is not revoked; reconnecting shows the account chooser."""
    response.delete_cookie(USER_COOKIE)
    return {"ok": True}


@router.get("/me")
async def me(user: User = Depends(get_current_user)) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "connected": bool(user.google_refresh_token or user.google_access_token),
        "scopes": (user.scopes or "").split(),
    }
