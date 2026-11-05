"""FastAPI application entrypoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Validate configuration before serving, then configure JSON logging."""
    settings = get_settings()
    configure_logging(settings.log_level)
    yield


app = FastAPI(title="MarketPilot API", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    """Report liveness for container orchestration and load balancers."""
    return {"status": "ok"}
