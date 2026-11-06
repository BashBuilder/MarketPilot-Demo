"""FastAPI application entrypoint."""

import logging
from collections.abc import AsyncIterator, Collection, Iterator
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from starlette.middleware.cors import CORSMiddleware

from app.api.campaigns import router as campaigns_router
from app.api.dependencies import (
    DEFAULT_EVENT_BUS,
    DEFAULT_WORKFLOW_SERVICES,
    RecordingRunLauncher,
    WorkflowServices,
)
from app.api.limits import RateLimitClient, RedisRateLimiter
from app.api.runs import router as runs_router
from app.api.schemas import ErrorDetail, ErrorResponse
from app.api.stream import router as stream_router
from app.api.versions import router as versions_router
from app.core.config import get_settings
from app.core.errors import (
    GuardrailViolation,
    InvalidRunState,
    MarketPilotError,
    NotFoundError,
    RateLimited,
    TooManyRuns,
    ValidationFailure,
)
from app.core.logging import configure_logging
from app.database.seed import seed
from app.database.session import get_sessionmaker, session_scope
from app.events.bus import RedisEventBus
from app.events.emitter import make_emitter
from app.llm.deepseek import DeepSeekLLMClient
from app.runs.launcher import WorkflowRunLauncher
from app.runs.services import build_agents, build_tool_registry
from app.runs.startup import resume_unfinished_runs

logger = logging.getLogger(__name__)
API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Validate configuration, configure logging and attach the Redis bus."""
    settings = get_settings()
    configure_logging(settings.log_level)
    await _seed_policies()
    bus = RedisEventBus.from_url(
        settings.redis_url,
        maxlen=settings.event_stream_maxlen,
        ttl_seconds=settings.event_stream_ttl_seconds,
    )
    rate_client = Redis.from_url(settings.redis_url, decode_responses=True)
    session_factory = get_sessionmaker()
    agents = build_agents()
    llm = DeepSeekLLMClient(settings)
    registry = build_tool_registry(settings, session_factory)
    launcher = WorkflowRunLauncher(
        agents=agents,
        llm=llm,
        registry=registry,
        session_factory=session_factory,
        event_bus=bus,
        settings=settings,
    )
    application.state.event_bus = bus
    application.state.rate_limiter = RedisRateLimiter(cast(RateLimitClient, rate_client))
    application.state.run_launcher = launcher
    application.state.workflow_services = WorkflowServices(
        agents=agents,
        llm=llm,
        tools={},
        emit=make_emitter(bus),
        registry=registry,
        session_factory=session_factory,
    )
    if settings.resume_on_startup:
        try:
            await resume_unfinished_runs(
                session_factory=get_sessionmaker(),
                launcher=application.state.run_launcher,
                settings=settings,
            )
        except Exception:
            logger.exception("startup run resume failed")
    try:
        yield
    finally:
        await launcher.close()
        await bus.close()
        await rate_client.aclose()


async def _seed_policies() -> None:
    """Re-embed seeded policies when the configured embedder has changed."""
    async with session_scope() as session:
        await seed(session)


class _FrontendOriginAllowlist(Collection[str]):
    """Resolve the single allowed origin lazily so imports need no config."""

    def __contains__(self, origin: object) -> bool:
        if origin == "*":
            return False
        return isinstance(origin, str) and origin == get_settings().frontend_origin

    def __iter__(self) -> Iterator[str]:
        yield get_settings().frontend_origin

    def __len__(self) -> int:
        return 1


async def health() -> dict[str, str]:
    """Report liveness for container orchestration and load balancers."""
    return {"status": "ok"}


def _status_for(exc: MarketPilotError) -> int:
    if isinstance(exc, (RateLimited, TooManyRuns)):
        return 429
    if isinstance(exc, ValidationFailure):
        return 422
    if isinstance(exc, GuardrailViolation):
        return 403
    if isinstance(exc, NotFoundError):
        return 404
    if isinstance(exc, InvalidRunState):
        return 409
    return 500


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message, details=details))
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json", exclude_none=True),
        headers=headers,
    )


app = FastAPI(title="MarketPilot API", version="0.1.0", lifespan=lifespan)
app.state.run_launcher = RecordingRunLauncher()
app.state.event_bus = DEFAULT_EVENT_BUS
app.state.rate_limiter = None
app.state.workflow_services = DEFAULT_WORKFLOW_SERVICES
app.add_middleware(
    CORSMiddleware,
    allow_origins=_FrontendOriginAllowlist(),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix=API_PREFIX)
api_router.add_api_route("/health", health, methods=["GET"], name="api_health")
api_router.include_router(campaigns_router)
api_router.include_router(versions_router)
api_router.include_router(runs_router)
api_router.include_router(stream_router)
app.include_router(api_router)
app.add_api_route("/health", health, methods=["GET"], name="health")


@app.exception_handler(MarketPilotError)
async def handle_marketpilot_error(_: Request, exc: MarketPilotError) -> JSONResponse:
    """Map typed errors to their contract status without leaking internals."""
    status_code = _status_for(exc)
    if status_code == 500:
        logger.error("typed API error", extra={"code": exc.code})
        return _error_response(500, "internal_error", "Internal server error")
    headers = {"Retry-After": str(exc.retry_after)} if isinstance(exc, RateLimited) else None
    return _error_response(status_code, exc.code, exc.message, exc.details, headers)


@app.exception_handler(RequestValidationError)
async def handle_request_validation(
    _: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Translate FastAPI request validation into the shared error envelope."""
    errors = [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    return _error_response(
        422,
        "validation_failed",
        "Request validation failed",
        {"errors": errors},
    )


@app.exception_handler(Exception)
async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
    """Return a generic 500 body; the stack trace stays in server logs."""
    logger.error("unhandled request error", exc_info=exc)
    return _error_response(500, "internal_error", "Internal server error")
