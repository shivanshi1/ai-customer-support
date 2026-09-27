"""Conversation history endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.schemas import ConversationDetail, ConversationSummary, MessageResponse
from app.api.dependencies import get_session
from app.repositories.support import SupportRepository


router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("", response_model=list[ConversationSummary])
async def list_conversations(
    customer_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ConversationSummary]:
    """List persisted conversations for one customer."""

    conversations = await SupportRepository(session).list_conversations(customer_id)
    return [ConversationSummary.model_validate(conversation) for conversation in conversations]


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    customer_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConversationDetail:
    """Return a customer's conversation together with ordered messages."""

    repository = SupportRepository(session)
    conversation = await repository.get_conversation(customer_id, conversation_id)
    messages = await repository.get_messages(conversation.id)
    return ConversationDetail(
        id=conversation.id,
        subject=conversation.subject,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[MessageResponse.model_validate(message) for message in messages],
    )
