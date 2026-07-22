# Conductor — API Reference

Base URL: `http://localhost:8000`. All app endpoints are under `/api/v1`. A machine-readable spec is in
[`openapi.json`](./openapi.json), and interactive docs are at `/docs`.

**Auth / user resolution (demo).** After the OAuth flow, the user is identified by (in priority order) a
`user_id` query param, an `X-User-Id` header, or the `conductor_user` cookie; otherwise the most recently
connected user is used. Real multi-tenant auth is a documented scaling step (see `DESIGN.md`).

---

### `GET /health`
Liveness probe → `{"status":"ok","service":"conductor","version":"0.1.0"}`.

### `GET /api/v1/auth/google`
Redirects (307) to Google's consent screen (offline access, PKCE). Sets short-lived `oauth_state` /
`oauth_verifier` cookies.

### `GET /api/v1/auth/google/callback?code=&state=`
Exchanges the code, upserts the user with tokens + granted scopes, sets the `conductor_user` cookie, and
redirects to the frontend (or a success page if the frontend isn't running).

### `GET /api/v1/auth/me`
Current user → `{id, email, connected, scopes[]}`.

### `POST /api/v1/sync/trigger`
Body: `{"services": ["gmail","gcal","drive"]?, "wait": false}`. Pulls recent items, embeds them, and
upserts into the `*_cache` tables. Runs in the background by default; `wait:true` blocks and returns
per-service counts. Also auto-detects the user's timezone from Calendar.
```json
{"status":"started","services":["gmail","gcal","drive"]}
```

### `GET /api/v1/sync/status`
Per-service `{last_synced_at, status, item_count, error}`.

### `POST /api/v1/query`  ⟵ the main endpoint
Body: `{"query": "...", "conversation_id": "..."?}`.
```json
{
  "conversation_id": "…",
  "query": "Prepare for tomorrow's meeting with Acme Corp",
  "intent": {"services": ["gcal","gmail","drive"], "intent": "prepare_meeting",
             "entities": [{"name":"company","value":"Acme Corp"}],
             "needs_clarification": false, "clarification_question": ""},
  "response": "Here's what I found for tomorrow's Acme Corp meeting: …",
  "actions_taken": [],
  "steps": [
    {"id":"s1","service":"gcal","operation":"search","status":"ok","result_count":2,"error":""},
    {"id":"s2","service":"gmail","operation":"search","status":"ok","result_count":5,"error":""},
    {"id":"s3","service":"drive","operation":"search","status":"ok","result_count":0,"error":""}
  ],
  "pending_confirmations": [],
  "results": { "s1": {"type":"search","hits":[…]} }
}
```
When a query implies a write, `pending_confirmations` contains
`{action_id, service, action_type, preview}` and nothing has been sent/changed yet.

### `GET /api/v1/actions`
Lists this user's pending (unconfirmed) write actions.

### `POST /api/v1/actions/confirm`
Body: `{"action_id": "…"}`. Executes the prepared write (sends the draft, creates/updates/deletes the
event, or shares the file) and returns the Google result.
```json
{"status":"executed","action_type":"send_email","service":"gmail",
 "result":{"executed":true,"message_id":"…","thread_id":"…"}}
```

### `POST /api/v1/actions/cancel`
Body: `{"action_id": "…"}`. Marks the pending action cancelled (nothing is executed).
