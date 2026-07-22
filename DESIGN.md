# Conductor — Design & Scaling

This document explains how Conductor is built and how it scales from a single-user demo to ~1M users.

## 1. Request lifecycle

```
POST /api/v1/query {query, chat_id?}
  0. Resolve/create chat thread  (chats + messages; auto-title new chats from the first query)
  1. Load chat context          (recent messages in this thread → resolves "that email")
  2. Intent classification       (GPT-5 structured → Intent{services, intent, entities, needs_clarification})
       └─ if ambiguous → return clarification question, stop
  3. Query planning              (GPT-5 structured → Plan{steps[]}), given current time + timezone
  4. Orchestration               (topological levels; parallel within a level; failures isolated)
       ├─ search       → hybrid pgvector search over *_cache
       ├─ get_context  → fetch full email/event/file from Google for reasoning
       └─ write        → build payload, create draft/preview, record pending_action
  5. Response synthesis          (GPT-5 structured → grounded NL answer + actions_taken)
  6. Persist the turn; return response + steps + pending_confirmations
```

Each stage is a separate module (`app/orchestrator/{intent,planner,orchestrator,synthesizer}.py`) so it
can be tested and swapped independently.

## 2. Orchestration engine (from scratch)

- **Plan = DAG.** Each `PlanStep` names a `service`, an `operation`, a semantic `query`, structured
  `filters`, and `depends_on`. The planner marks independent reads with no dependencies and chains
  sequential work (e.g. `search → draft_email`).
- **Execution.** `_topo_levels` (Kahn's algorithm) groups steps into levels; each level runs with
  `asyncio.gather(..., return_exceptions=True)`. A step that raises is recorded as `status=error` and
  its output is simply absent — dependents and the synthesizer degrade gracefully rather than crashing.
- **Data flow.** `get_context` and write steps read their dependencies' outputs from an in-memory
  result map (e.g. a draft step consumes the top hit of the search it depends on).
- **Concurrency safety.** Steps in a level run concurrently, so each DB touch opens its own
  `AsyncSession` (SQLAlchemy sessions are not concurrency-safe). The shared Google client is built once
  behind an `asyncio.Lock`; a refreshed token is persisted via a dedicated session.

## 3. Embeddings & hybrid search

- **What we embed.** Gmail: `subject + sender + snippet`. Calendar: `title + description + location +
  attendees`. Drive: `name + mime type`. One vector per item (`text-embedding-3-small`, 1536-d).
- **Storage.** `*_cache` tables with a `vector(1536)` column and an **HNSW** index
  (`vector_cosine_ops`, `m=16`, `ef_construction=64`).
- **Hybrid retrieval.** Structured filters (`sender ILIKE`, `received_at` range, `mime_type`,
  attendee JSONB containment) run in SQL first; survivors are ranked by cosine distance. Metadata-first
  keeps the vector scan small — faster and more precise, per the assignment hint.
- **Quality.** On real data, Drive "assignment document" returns the exact file at score 0.51; the
  attendee-filter query returns exactly the events with that attendee. Query latency is ~0.5s, dominated
  by the embedding round-trip (see caching below).

## 4. Safety & correctness

- **Draft + confirm.** No query auto-sends or mutates. Writes become `pending_actions`; email drafts are
  created *unsent* in Gmail; `/actions/confirm` executes, `/actions/cancel` discards. Calendar seeding
  and internal writes use `sendUpdates='none'` to avoid stray invites.
- **Grounding.** The synthesizer is instructed to use only provided results and never invent
  emails/events/dates; empty results are reported honestly.
- **Resilience.** Google calls retry with exponential backoff on 429/5xx (`tenacity`); OAuth tokens
  auto-refresh; embedding batches retry.

## 5. Scaling to ~1M users

The current build is deliberately single-node and simple. The path to 1M:

| Concern | Now | At scale |
|---|---|---|
| **Caching** | none | Redis: query-embedding cache (the ~400 ms hot path), intent-classification cache, conversation context. Target >80% hit rate. |
| **Background work** | FastAPI `BackgroundTasks` | **Celery** workers + broker for sync/orchestration; API stays thin and returns fast. |
| **Sync** | bounded pull on demand | Incremental sync via Gmail history API / Calendar sync tokens / Drive changes feed, every ~15 min; watch/push webhooks to cut latency. |
| **DB** | one Postgres | Read replicas; **partition/shard `*_cache` and conversations by `user_id`**; pgvector HNSW per shard. |
| **Rate limits** | per-call retry | Per-user token buckets (e.g. 100 q/user/hr) + global Google quota budgeting (250 units/s) with batching. |
| **Multi-region** | localhost | Deploy API + cache + DB per region (US/EU/APAC); route to nearest; keep tokens region-local for data residency. |
| **Isolation** | user cookie / header | Real auth (JWT/session), encrypted token-at-rest (KMS), per-request tenant scoping, audit log of every write. |
| **Observability** | logs | P99 latency (<2s target), cache hit rate, Google error rate (<0.1%), embedding-freshness lag (<15 min). |

**Latency budget at scale (P99 < 2s):** cache-hit intent/embeddings → skip 1–2 LLM calls; run planner
and searches concurrently; keep synthesis on the critical path only. Long/expensive orchestrations move
to Celery with a job id the client polls or receives over WebSocket.

## 6. Notable trade-offs

- **Two LLM calls (intent, then plan) instead of one.** Clearer separation and better matches the
  rubric; at low `reasoning.effort` the extra call is cheap. Could be merged for latency.
- **Cache-then-search vs. live Google search.** We pre-index into pgvector so semantic search is fast
  and offline-capable; freshness is bounded by sync cadence (mitigated by incremental sync at scale).
- **`get_context` fetches full content lazily** (only for the top hit of a dependency) to avoid pulling
  large bodies for every candidate.
- **Bounded sync for the demo** (recent N / lookback window) — deliberately simple; incremental sync is
  the documented next step, not built here.
