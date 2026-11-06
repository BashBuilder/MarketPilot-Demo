"""Shared agent contract: prompt plus mapped state to a verified output model.

An agent is stateless. It reads a slice of workflow state, asks the LLM for a
structured payload, and returns a validated output model; the node wrapper owns
persistence and state merging. This module deliberately has no database import
so agents cannot bypass repositories.
"""

import random
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.agents.contracts import (
    AgentPreparation,
    ChatMessage,
    EventEmitter,
    LLMClient,
    ToolInvoker,
)
from app.agents.prompts.loader import load_prompt
from app.core.config import Settings
from app.graph.state import WorkflowState
from app.harness.context import AGENT_CONTEXT_FIELDS, build_agent_context
from app.harness.guardrails import delimit_untrusted
from app.harness.registry import AgentName
from app.harness.retries import Sleep, default_sleep
from app.harness.validators import Issue
from app.harness.verification import Validator, run_with_verification

__all__ = [
    "AgentPreparation",
    "BaseAgent",
    "ChatMessage",
    "EventEmitter",
    "LLMClient",
    "ToolInvoker",
]


class _CombinedValidator[T]:
    """Run several semantic validators and collect every issue."""

    def __init__(self, validators: Sequence[Validator[T]]) -> None:
        self._validators = validators

    def validate(self, value: T) -> list[Issue]:
        issues: list[Issue] = []
        for validator in self._validators:
            issues.extend(validator.validate(value))
        return issues


class BaseAgent[T: BaseModel]:
    """Base for the pipeline agents defined in section 7 of the backend guide."""

    name: AgentName
    output_model: type[T]
    prompt_name: str
    validators: tuple[Validator[T], ...] = ()
    context_budget: int = 4000
    prompts_dir: Path | None = None

    async def run(
        self,
        state: WorkflowState,
        llm: LLMClient,
        emit: EventEmitter | None = None,
        tools: ToolInvoker | None = None,
        *,
        settings: Settings | None = None,
        sleep: Sleep = default_sleep,
        jitter: Callable[[], float] = random.random,
    ) -> T:
        """Produce this agent's output without mutating ``state``.

        ``tools`` is the middleware boundary; agents that need evidence before
        generating override ``prepare``. Verification settings are injectable
        so tests never sleep or read the process environment.
        """
        prepared = await self.prepare(state, tools, settings=settings)
        prompt = load_prompt(self.prompt_name, prompts_dir=self.prompts_dir)
        messages: list[ChatMessage] = [
            {
                "role": "system",
                "content": f"{prompt.text}\n\nPrompt version: {prompt.version}",
            },
            {"role": "user", "content": self._context_block(state)},
        ]
        if prepared.context:
            messages.append(
                {
                    "role": "user",
                    "content": delimit_untrusted(prepared.context, source="tool-results"),
                }
            )
        validators = (*self.validators, *prepared.validators)
        semantic: Validator[T] | None = _CombinedValidator(validators) if validators else None

        async def step(feedback: str) -> Any:
            attempt = self._with_feedback(messages, feedback)
            return await llm.structured(attempt, schema=self.output_model)

        return await run_with_verification(
            step,
            model=self.output_model,
            semantic=semantic,
            on_event=emit,
            settings=settings,
            sleep=sleep,
            jitter=jitter,
        )

    async def prepare(
        self,
        state: WorkflowState,
        tools: ToolInvoker | None,
        *,
        settings: Settings | None = None,
    ) -> AgentPreparation[T]:
        """Hook for tool-using agents; the default needs no extra context."""
        del state, tools, settings
        return AgentPreparation[T]()

    def _context_block(self, state: WorkflowState) -> str:
        """Serialize only the fields mapped to this agent, fenced as untrusted."""
        context = build_agent_context(state, self.name, self.context_budget)
        fields = ("idea", *AGENT_CONTEXT_FIELDS[self.name])
        payload = context.model_dump_json(include=set(fields), exclude_none=True)
        return delimit_untrusted(payload, source="workflow-state")

    def _with_feedback(self, messages: list[ChatMessage], feedback: str) -> list[ChatMessage]:
        if not feedback:
            return messages
        note = delimit_untrusted(feedback, source="verification-feedback")
        return [*messages, {"role": "user", "content": note}]
