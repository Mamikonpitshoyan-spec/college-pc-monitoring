"""FastAPI entry point for the Monitoring Server backend."""

import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.pages import router as pages_router
from app.api.router import api_router
from app.core.config import settings
from app.database.session import initialize_database
from app.monitoring.offline_watcher import offline_sweeper
import app.models  # noqa: F401 - registers all SQLAlchemy models before create_all


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize tables and start the offline sweeper."""
    initialize_database()
    sweep_task = asyncio.create_task(offline_sweeper())
    yield
    sweep_task.cancel()


def create_app() -> FastAPI:
    """Create the REST backend plus the HTML admin dashboard."""
    application = FastAPI(title=settings.app_name, version="0.6.0", lifespan=lifespan)
    application.include_router(api_router)
    application.include_router(pages_router)
    static_dir = Path(__file__).resolve().parent / "static"
    application.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    return application


app = create_app()


if __name__ == "__main__":
    """Run with `python -m app.main` so HOST and PORT from .env take effect."""
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port)
