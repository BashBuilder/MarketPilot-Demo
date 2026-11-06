"""Database-backed concurrency gate for starting new workflow runs.

The count is read from Postgres on every request so multiple API processes
share one cap. It intentionally counts only ``running`` rows: pending and
awaiting-approval runs are not consuming an execution slot.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import TooManyRuns
from app.database.repositories import runs

__all__ = ["ensure_run_capacity"]


async def ensure_run_capacity(session: AsyncSession, settings: Settings) -> None:
    """Raise ``TooManyRuns`` before the caller inserts a new run."""
    running = await runs.count_running(session)
    if running >= settings.max_concurrent_runs:
        raise TooManyRuns(
            "too many concurrent runs",
            details={"limit": settings.max_concurrent_runs, "running": running},
        )
