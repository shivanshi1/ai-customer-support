import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.chat import router as chat_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.health import router as health_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.dashboard import router as dashboard_router
from app.config import get_settings
from app.core.errors import AppError, app_error_handler
from app.core.logging import configure_logging
from app.db.database import Database
from app.repositories.support import SupportRepository
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


def create_app(settings_override=None) -> FastAPI:
    """Create the FastAPI application; tests can supply isolated settings."""

    settings = settings_override or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Create and dispose shared resources for the application lifetime."""

        configure_logging(settings.log_level)
        database = Database(settings)
        await database.create_schema()
        async with database.session_factory() as session:
            repository = SupportRepository(session)
            await repository.seed_demo_data()
            await session.commit()

        app.state.settings = settings
        app.state.database = database
        app.state.llm_service = LLMService(settings)
        logger.info("application_started environment=%s", settings.app_env)
        try:
            yield
        finally:
            await app.state.llm_service.close()
            await database.dispose()
            logger.info("application_stopped")

    app = FastAPI(
        title="AI Customer Support Automation",
        description=(
            "An AI-powered customer support automation platform "
            "built with FastAPI and Groq."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        """Attach a request ID to every response and log request completion."""

        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_completed method=%s path=%s status=%s request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            request_id,
        )
        return response

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return app_error_handler(request, exc)

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(conversations_router, prefix="/api/v1")
    app.include_router(knowledge_router, prefix="/api/v1")
    app.include_router(dashboard_router, prefix="/api/v1")
    return app


app = create_app()
