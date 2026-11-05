"""Types shared across agents and the harness boundary."""

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, TypedDict

from pydantic import BaseModel

from app.harness.verification import Validator, VerificationEvent


class ChatMessage(TypedDict):
    role: str
    content: str


class LLMClient(Protocol):
    """Structured LLM boundary; the verifier, not the client, validates shape."""

    async def structured(
        self,
        messages: Sequence[ChatMessage],
        *,
        schema: type[BaseModel],
    ) -> Any: ...


class ToolInvoker(Protocol):
    """The slice of the tool middleware an agent may use."""

    async def call(
        self,
        name: str,
        payload: Mapping[str, Any],
        *,
        cost: float = 0.0,
    ) -> Any: ...


type EventEmitter = Callable[[VerificationEvent], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class AgentPreparation[T]:
    """Run-specific tool output and validators produced before generation."""

    context: str | None = None
    validators: tuple[Validator[T], ...] = ()
