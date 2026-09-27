from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_llm_service, get_session, get_settings
from app.agents.schemas import ChatRequest, ChatResponse
from app.agents.support_agent import SupportAgent
from app.config import Settings
from app.repositories.support import SupportRepository
from app.services.llm_service import LLMService


router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


def get_support_agent(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    llm_service: Annotated[LLMService, Depends(get_llm_service)],
) -> SupportAgent:
    """Create the support agent dependency."""

    return SupportAgent(
        llm_service=llm_service,
        repository=SupportRepository(session),
        settings=settings,
    )


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    agent: SupportAgent = Depends(get_support_agent),
) -> ChatResponse:
    """Process a customer support message."""

    return await agent.process_message(
        customer_id=request.customer_id,
        message=request.message,
        conversation_id=request.conversation_id,
    )
