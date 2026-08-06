from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import openai_compat
from app.api.router import api_router
from app.core.config import clear_settings_cache, get_settings
from app.models.schemas import HealthResponse
from app.utils.logging import get_logger, setup_logging


@asynccontextmanager
async def lifespan(_app: FastAPI):
    clear_settings_cache()
    setup_logging()
    logger = get_logger("jarvis")
    settings = get_settings()
    logger.info(
        "startup",
        app=settings.app_name,
        env=settings.app_env,
        channel_bridge=settings.enable_channel_bridge,
    )
    yield
    logger.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
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
    app.include_router(api_router)
    # OpenAI-compatible surface for ZeroClaw (custom:http://host:8000/v1)
    app.include_router(openai_compat.router, prefix="/v1")

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            app=settings.app_name,
            env=settings.app_env,
        )

    return app


app = create_app()
