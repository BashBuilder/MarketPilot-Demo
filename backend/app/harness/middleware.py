"""Middleware that gates, times, logs and audits every tool call.

Audit rows are written through their own short-lived session: a failed node
rolls back the run session, and the failure row must survive that rollback.
"""

import hashlib
import json
import logging
import time
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import GuardrailViolation, ValidationFailure
from app.core.logging import bind_run_context
from app.database.repositories import tool_calls
from app.database.repositories.tool_calls import ToolCallStatus
from app.harness.guardrails import RunGuardrails
from app.harness.registry import AgentName, ToolRegistry

logger = logging.getLogger(__name__)


def _args_hash(payload: Mapping[str, Any]) -> str:
    """Hash canonical args so logs and rows never contain raw user text."""
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ToolCallMiddleware:
    """Single entry point for agent tool use: allowlist, budget, audit."""

    def __init__(
        self,
        *,
        registry: ToolRegistry,
        guardrails: RunGuardrails,
        session_factory: async_sessionmaker[AsyncSession],
        run_id: UUID,
        agent: AgentName,
        step: str | None = None,
    ) -> None:
        self._registry = registry
        self._guardrails = guardrails
        self._session_factory = session_factory
        self._run_id = run_id
        self._agent = agent
        self._step = step

    async def call(
        self,
        name: str,
        payload: Mapping[str, Any],
        *,
        cost: float = 0.0,
    ) -> Any:
        """Resolve, budget, run and audit one tool call; failures still audited."""
        with bind_run_context(run_id=str(self._run_id), agent=self._agent, step=self._step):
            start = time.perf_counter()
            try:
                spec = self._registry.get_tool(self._agent, name)
                self._guardrails.record_call(name)
                self._guardrails.check_cost(cost)
                try:
                    args = spec.args_model.model_validate(dict(payload))
                except ValidationError as exc:
                    raise ValidationFailure(f"invalid args for tool {name!r}: {exc}") from exc
                result = await spec.run(args)
            except GuardrailViolation as exc:
                await self._write(name, payload, start, "denied", cost=None, error=exc.message)
                logger.warning("tool %s denied for agent %s: %s", name, self._agent, exc.message)
                raise
            except Exception as exc:
                await self._write(name, payload, start, "error", cost=None, error=str(exc))
                logger.warning("tool %s failed for agent %s: %s", name, self._agent, exc)
                raise
            else:
                self._guardrails.record_cost(cost)
                await self._write(name, payload, start, "success", cost=cost, error=None)
                logger.info("tool %s succeeded for agent %s", name, self._agent)
                return result

    async def _write(
        self,
        name: str,
        payload: Mapping[str, Any],
        start: float,
        status: ToolCallStatus,
        *,
        cost: float | None,
        error: str | None,
    ) -> None:
        duration_ms = max(0, int((time.perf_counter() - start) * 1000))
        try:
            async with self._session_factory() as session:
                await tool_calls.create(
                    session,
                    run_id=self._run_id,
                    agent=self._agent,
                    tool=name,
                    args_hash=_args_hash(payload),
                    duration_ms=duration_ms,
                    status=status,
                    cost=cost,
                    error=error,
                )
                await session.commit()
        except Exception:
            if status == "success":
                raise
            # Never mask the tool failure with an audit write failure.
            logger.exception("failed to record %s tool call %s", status, name)
