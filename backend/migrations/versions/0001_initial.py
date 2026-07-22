"""initial schema: users, conversations, *_cache, sync_state, pending_actions + pgvector HNSW

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-22
"""
from typing import Sequence, Union

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.config import settings

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DIM = settings.embedding_dim


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True),
        sa.Column("google_access_token", sa.Text()),
        sa.Column("google_refresh_token", sa.Text()),
        sa.Column("token_expiry", sa.DateTime(timezone=True)),
        sa.Column("scopes", sa.Text()),
        sa.Column("timezone", sa.String(64), server_default="UTC", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("intent", postgresql.JSONB()),
        sa.Column("response", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    op.create_table(
        "gmail_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email_id", sa.String(255), nullable=False),
        sa.Column("thread_id", sa.String(255)),
        sa.Column("subject", sa.Text()),
        sa.Column("sender", sa.String(320)),
        sa.Column("body_preview", sa.Text()),
        sa.Column("labels", postgresql.JSONB()),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(DIM)),
        sa.Column("received_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id", "email_id", name="uq_gmail_user_email"),
    )
    op.create_index("ix_gmail_cache_user_id", "gmail_cache", ["user_id"])
    op.create_index("ix_gmail_cache_sender", "gmail_cache", ["sender"])
    op.create_index("ix_gmail_cache_received_at", "gmail_cache", ["received_at"])

    op.create_table(
        "gcal_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", sa.String(255), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("location", sa.Text()),
        sa.Column("attendees", postgresql.JSONB()),
        sa.Column("organizer", sa.String(320)),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(DIM)),
        sa.Column("start_at", sa.DateTime(timezone=True)),
        sa.Column("end_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id", "event_id", name="uq_gcal_user_event"),
    )
    op.create_index("ix_gcal_cache_user_id", "gcal_cache", ["user_id"])
    op.create_index("ix_gcal_cache_start_at", "gcal_cache", ["start_at"])

    op.create_table(
        "gdrive_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", sa.String(255), nullable=False),
        sa.Column("name", sa.Text()),
        sa.Column("mime_type", sa.String(255)),
        sa.Column("content_preview", sa.Text()),
        sa.Column("owners", postgresql.JSONB()),
        sa.Column("web_view_link", sa.Text()),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(DIM)),
        sa.Column("modified_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id", "file_id", name="uq_gdrive_user_file"),
    )
    op.create_index("ix_gdrive_cache_user_id", "gdrive_cache", ["user_id"])
    op.create_index("ix_gdrive_cache_mime_type", "gdrive_cache", ["mime_type"])
    op.create_index("ix_gdrive_cache_modified_at", "gdrive_cache", ["modified_at"])

    op.create_table(
        "sync_state",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service", sa.String(32), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(32), server_default="idle", nullable=False),
        sa.Column("item_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error", sa.Text()),
        sa.UniqueConstraint("user_id", "service", name="uq_sync_user_service"),
    )
    op.create_index("ix_sync_state_user_id", "sync_state", ["user_id"])

    op.create_table(
        "pending_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True)),
        sa.Column("service", sa.String(32), nullable=False),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("preview", sa.Text()),
        sa.Column("status", sa.String(32), server_default="pending", nullable=False),
        sa.Column("result", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_pending_actions_user_id", "pending_actions", ["user_id"])

    # HNSW indexes for cosine similarity (pgvector). m=16, ef_construction=64.
    for table in ("gmail_cache", "gcal_cache", "gdrive_cache"):
        op.execute(
            f"CREATE INDEX {table}_embedding_hnsw ON {table} "
            f"USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
        )


def downgrade() -> None:
    for table in ("gmail_cache", "gcal_cache", "gdrive_cache"):
        op.execute(f"DROP INDEX IF EXISTS {table}_embedding_hnsw")
    op.drop_table("pending_actions")
    op.drop_table("sync_state")
    op.drop_table("gdrive_cache")
    op.drop_table("gcal_cache")
    op.drop_table("gmail_cache")
    op.drop_table("conversations")
    op.drop_table("users")
