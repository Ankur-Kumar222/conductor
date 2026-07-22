# Sample Queries & Expected Outputs

Real runs against a live Google account (some output trimmed). Each shows the classified intent, the
execution steps (the DAG that ran), and the synthesized answer. `POST /api/v1/query`.

Legend for steps: `(operation, service, status, result_count)`.

---

## Single-service

### 1. "Find emails from LinkedIn about jobs"
- **intent:** `search_email` · services `[gmail]`
- **steps:** `[(search, gmail, ok, 5)]`
- **response:** Lists 5 real LinkedIn job emails with sender + received time + message id, e.g. *"Machine
  Learning Engineer … at HCLTech — LinkedIn Job Alerts, 2026-07-22"*. Offers to open/label.

### 2. "Show me spreadsheets in my Drive"
- **intent:** `find_files` · `[drive]`
- **steps:** `[(search, drive, ok, 5)]`
- **response:** Spreadsheets most-recent-first with owner, modified date, and Drive link.

### 3. "Show me PDFs in my Drive from this year"  *(metadata filter)*
- **intent:** `find_files` · `[drive]` (filters: `mime_type=pdf`, `after=2026-01-01`)
- **steps:** `[(search, drive, ok, 5)]`
- **response:** Only 2026 PDFs (résumés etc.) with links — mime + date filter applied before ranking.

### 4. "What's on my calendar next week?"  *(temporal)*
- **intent:** `list_events` · `[gcal]` (filters resolved to the coming Mon–Sun in the user's timezone)
- **steps:** `[(search, gcal, ok, N)]`
- **response:** Events in that window, times rendered in the user's timezone.

---

## Multi-service (parallel fan-out)

### 5. "What's on my calendar next week where john@company.com is invited?"  *(attendee filter)*
- **intent:** `filter_events_by_attendee` · `[gcal]`
- **steps:** `[(search, gcal, ok, 3)]`
- **response:**
  > - 1:1 with John — Mon, Jul 27, 11:00–11:30 AM
  > - Acme Corp Quarterly Review (Boardroom) — Tue, Jul 28, 2:00–3:00 PM
  > - Product Planning — Sat, Aug 1, 11:00 AM–12:00 PM

### 6. "Prepare for tomorrow's meeting with Acme Corp"  *(Calendar + Gmail + Drive)*
- **intent:** `prepare_meeting` · `[gcal, gmail, drive]`
- **steps:** `[(search, gmail, ok, 5), (search, drive, ok, 0), (search, gcal, ok, 2), (get_context, gcal, ok, 1), (get_context, gmail, ok, 1)]`
- **response:** Meeting time/location/purpose, attendees + response status, related email/doc context, and
  offers to draft an agenda email (which would then require confirmation).

### 7. "Find emails and documents related to my job interviews"  *(Gmail + Drive)*
- **intent:** `search_emails_and_files` · `[gmail, drive]`
- **steps:** `[(search, drive, ok, 1), (search, gmail, ok, 5)]` (run in parallel)
- **response:** A Drive "Job Interviews" sheet plus recent application/interview emails.

---

## Writes (draft + confirm)

### 8. "Draft an email to myself summarizing my most recent job-application emails"
- **intent:** `draft_email` · `[gmail]`
- **steps:** `[(search, gmail, ok), (get_context, gmail, ok), (draft_email, gmail, pending_confirmation)]`
- **response:** Returns a `pending_confirmation` with the full drafted email preview; a real **unsent**
  Gmail draft is created. Nothing sends until `POST /actions/confirm`.

### 9. "Create a calendar event tomorrow from 3pm to 4pm titled Conductor Demo Sync"
- **intent:** `create_event` · `[gcal]`
- **steps:** `[(create_event, gcal, pending_confirmation)]`
- **preview:** `Create event: Conductor Demo Sync — 2026-07-23T15:00:00+05:30 → …+05:30`
- On confirm → event created (verified via `events.get`), returns `event_id` + `html_link`.

### 10. "Draft a reply to my most recent Wellfound email"
- **intent:** `draft_email` · `[gmail]`
- **steps:** search → get_context → draft_email (pending). Reply body grounded in the actual thread;
  awaits confirmation to send.

---

## Hard cases

### 11. "Move the meeting with John"  *(ambiguous)*
- **intent:** `move_event` · `needs_clarification = true`
- **steps:** `[]` (short-circuits before execution)
- **response:** *"Which meeting do you want to move — '1:1 with John' on Mon, Jul 27 or 'Acme Corp
  Quarterly Review' on Tue, Jul 28? And what new date/time?"*

### 12. "Summarize the most relevant one of those in more detail"  *(conversation context)*
- Uses the last 5 turns to resolve **"those"**; re-runs search then `get_context` on the top hits and
  reads the actual sheet/email body before summarizing.

### 13. "Next Tuesday"–style phrasing  *(temporal + timezone)*
- The planner receives the current datetime + the user's auto-detected timezone (`Asia/Kolkata`) and
  resolves relative dates to ISO bounds on the calendar filter. Verified: "next week" →
  `2026-07-27 → 2026-08-03` (Mon–Sun, IST).

---

### Graceful partial failure
If one service errors mid-orchestration (e.g. a transient Calendar 5xx), that step is recorded as
`status=error` and the others still return; the synthesizer answers with what succeeded and notes what
couldn't be retrieved. Covered by `tests/test_orchestrator.py::test_partial_failure_is_isolated`.
