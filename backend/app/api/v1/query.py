"""Natural-language query endpoint — runs the full orchestration pipeline."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import User
from app.orchestrator import pipeline
from app.orchestrator.writes import write_handler
from app.schemas import QueryRequest, QueryResponse

router = APIRouter(prefix="/query", tags=["query"])


@router.post("", response_model=QueryResponse)
async def run_query(
    payload: QueryRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> QueryResponse:
    return await pipeline.run_query(
        session, user, payload.query,
        chat_id=payload.chat_id,
        write_handler=write_handler,
    )
