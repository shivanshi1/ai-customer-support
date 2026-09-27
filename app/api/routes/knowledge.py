"""Protected knowledge-base management routes."""

import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session, get_settings
from app.config import Settings
from app.services.knowledge_base import KnowledgeBase

router = APIRouter(prefix="/knowledge", tags=["Knowledge base"])


@router.post("/reindex")
async def reindex_knowledge(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, int]:
    """Rebuild document chunks. Requires a configured bearer token."""
    if not settings.knowledge_admin_token:
        raise HTTPException(status_code=503, detail="Knowledge management is not configured.")
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    if not hmac.compare_digest(supplied, settings.knowledge_admin_token):
        raise HTTPException(status_code=401, detail="Invalid management credentials.")
    try:
        count = await KnowledgeBase(session, settings).ingest()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"chunks_indexed": count}
