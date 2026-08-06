from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import openai_compat
from app.api.router import api_router
from app.core.config import clear_settings_cache, get_settings
from app.models.schemas import HealthResponse
from app.utils.logging import get_logger, setup_logging


async def _reminder_poll_loop(stop: asyncio.Event) -> None:
    logger = get_logger("jarvis.reminders")
    while not stop.is_set():
        settings = get_settings()
        interval = max(0, int(settings.reminder_poll_seconds or 0))
        if interval <= 0:
            await asyncio.sleep(30)
            continue
        try:
            from app.services.reminder_service import ReminderService

            result = await ReminderService().run_due()
            if result.get("processed"):
                logger.info("reminders_processed", **result)
        except Exception:
            logger.exception("reminder_poll_error")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass


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
        resend=bool(settings.resend_api_key),
    )
    stop = asyncio.Event()
    poll_task = asyncio.create_task(_reminder_poll_loop(stop))
    yield
    stop.set()
    poll_task.cancel()
    try:
        await poll_task
    except asyncio.CancelledError:
        pass
    logger.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.2.0",
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
