"""FastAPI dependencies backed by application-lifecycle resources."""

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.support_agent import SupportAgent
from app.config import Settings
from app.db.database import Database
from app.repositories.support import SupportRepository
from app.services.llm_service import LLMService


def get_settings(request: Request) -> Settings:
    return request.app.state.settings  # type: ignore[no-any-return]


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    database: Database = request.app.state.database
    async for session in database.session():
        yield session


def get_llm_service(request: Request) -> LLMService:
    return request.app.state.llm_service  # type: ignore[no-any-return]


def get_support_agent(
    session: AsyncSession,
    settings: Settings,
    llm_service: LLMService,
) -> SupportAgent:
    return SupportAgent(
        llm_service=llm_service,
        repository=SupportRepository(session),
        settings=settings,
    )
