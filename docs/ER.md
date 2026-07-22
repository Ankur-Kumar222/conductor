# Data Model (ER)

PostgreSQL + pgvector. `*_cache` tables hold synced Google items with a `vector(1536)` embedding and an
HNSW cosine index. Migrations live in `backend/migrations/` (Alembic).

```mermaid
erDiagram
    users ||--o{ chats : has
    chats ||--o{ messages : contains
    users ||--o{ gmail_cache : owns
    users ||--o{ gcal_cache : owns
    users ||--o{ gdrive_cache : owns
    users ||--o{ sync_state : tracks
    users ||--o{ pending_actions : proposes

    users {
        uuid id PK
        string email UK
        text google_access_token
        text google_refresh_token
        timestamptz token_expiry
        text scopes
        string timezone
        timestamptz created_at
    }
    chats {
        uuid id PK
        uuid user_id FK
        string title
        timestamptz created_at
        timestamptz updated_at
    }
    messages {
        uuid id PK
        uuid chat_id FK
        uuid user_id
        string role "user|assistant"
        text content
        jsonb meta "intent, steps, actions, pending (assistant)"
        timestamptz created_at
    }
    gmail_cache {
        uuid id PK
        uuid user_id
        string email_id
        string thread_id
        text subject
        string sender
        text body_preview
        jsonb labels
        vector embedding "vector(1536), HNSW cosine"
        timestamptz received_at
    }
    gcal_cache {
        uuid id PK
        uuid user_id
        string event_id
        text title
        text description
        text location
        jsonb attendees
        string organizer
        vector embedding "vector(1536), HNSW cosine"
        timestamptz start_at
        timestamptz end_at
    }
    gdrive_cache {
        uuid id PK
        uuid user_id
        string file_id
        text name
        string mime_type
        text content_preview
        jsonb owners
        text web_view_link
        vector embedding "vector(1536), HNSW cosine"
        timestamptz modified_at
    }
    sync_state {
        uuid id PK
        uuid user_id
        string service
        timestamptz last_synced_at
        string status
        int item_count
        text error
    }
    pending_actions {
        uuid id PK
        uuid user_id
        uuid conversation_id
        string service
        string action_type
        jsonb payload
        text preview
        string status "pending|executed|cancelled"
        jsonb result
        timestamptz created_at
    }
```

**Indexes of note**
- `{gmail,gcal,gdrive}_cache_embedding_hnsw` — `USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)`
- B-tree on `sender`, `received_at`, `start_at`, `mime_type`, `modified_at` for the metadata-filter stage
- `UNIQUE(user_id, <external_id>)` per cache table so sync is an idempotent upsert
