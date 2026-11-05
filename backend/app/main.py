"""FastAPI application entrypoint."""

import logging
from collections.abc import AsyncIterator, Collection, Iterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from app.api.campaigns import router as campaigns_router
from app.api.dependencies import DEFAULT_WORKFLOW_SERVICES, RecordingRunLauncher
from app.api.runs import router as runs_router
from app.api.schemas import ErrorDetail, ErrorResponse
from app.api.versions import router as versions_router
from app.core.config import get_settings
from app.core.errors import (
    GuardrailViolation,
    InvalidRunState,
    MarketPilotError,
    NotFoundError,
    ValidationFailure,
)
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)
API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Validate configuration before serving, then configure JSON logging."""
    settings = get_settings()
    configure_logging(settings.log_level)
    yield


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
) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message, details=details))
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json", exclude_none=True),
    )


app = FastAPI(title="MarketPilot API", version="0.1.0", lifespan=lifespan)
app.state.run_launcher = RecordingRunLauncher()
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
app.include_router(api_router)
app.add_api_route("/health", health, methods=["GET"], name="health")


@app.exception_handler(MarketPilotError)
async def handle_marketpilot_error(_: Request, exc: MarketPilotError) -> JSONResponse:
    """Map typed errors to their contract status without leaking internals."""
    status_code = _status_for(exc)
    if status_code == 500:
        logger.error("typed API error", extra={"code": exc.code})
        return _error_response(500, "internal_error", "Internal server error")
    return _error_response(status_code, exc.code, exc.message, exc.details)


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
