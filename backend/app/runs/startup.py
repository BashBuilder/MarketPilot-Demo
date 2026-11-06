"""Recover runs left running by a previous process.

Startup recovery is best-effort: one broken run must not prevent the API from
serving, and a short Redis lock stops two server processes claiming the same
run. The launcher owns graph execution and resumes from the latest checkpoint.
"""

import logging
from typing import Any, Protocol
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.database.models import RunStatus, WorkflowRun
from app.database.repositories import runs
from app.graph.state import WorkflowState
from app.harness.checkpoints import load_latest_checkpoint

logger = logging.getLogger(__name__)
_RESUME_LOCK_TIMEOUT_SECONDS = 30


class RunStarter(Protocol):
    """The launcher boundary: start or resume one run by id."""

    async def start(self, run_id: UUID) -> None: ...


async def resume_unfinished_runs(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    launcher: RunStarter,
    settings: Settings,
    redis: Redis | None = None,
) -> list[UUID]:
    """Resume every running run that no other process has claimed."""
    if not settings.resume_on_startup:
        return []

    client = (
        redis if redis is not None else Redis.from_url(settings.redis_url, decode_responses=True)
    )
    owns_client = redis is None
    try:
        async with session_factory() as session:
            candidates = await runs.list_by_status(session, RunStatus.RUNNING)

        resumed: list[UUID] = []
        for run in candidates:
            try:
                if await _resume_one(run, session_factory, launcher, client):
                    resumed.append(run.id)
                    logger.info("resumed unfinished run", extra={"run_id": str(run.id)})
            except Exception:
                logger.exception("could not resume run", extra={"run_id": str(run.id)})
        return resumed
    finally:
        if owns_client:
            await client.aclose()


async def _resume_one(
    run: WorkflowRun,
    session_factory: async_sessionmaker[AsyncSession],
    launcher: RunStarter,
    redis: Redis,
) -> bool:
    state = await _latest_state(session_factory, run.id)
    if state is not None and state.status == "escalated":
        return False

    lock: Any = redis.lock(
        _lock_key(run.id),
        timeout=_RESUME_LOCK_TIMEOUT_SECONDS,
        blocking_timeout=0,
    )
    if not await lock.acquire(blocking=False):
        logger.info("run is locked by another process", extra={"run_id": str(run.id)})
        return False
    try:
        await launcher.start(run.id)
    finally:
        await _release(lock)
    return True


async def _latest_state(
    session_factory: async_sessionmaker[AsyncSession],
    run_id: UUID,
) -> WorkflowState | None:
    async with session_factory() as session:
        return await load_latest_checkpoint(session, run_id)


async def _release(lock: Any) -> None:
    try:
        await lock.release()
    except Exception:
        logger.warning("could not release resume lock", exc_info=True)


def _lock_key(run_id: UUID) -> str:
    return f"run:{run_id}:resume"
