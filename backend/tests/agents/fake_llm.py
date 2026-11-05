"""Deterministic LLM double that records the requests it receives."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from app.agents.base import ChatMessage


@dataclass(frozen=True)
class LLMRequest:
    messages: tuple[ChatMessage, ...]
    schema: type[BaseModel]


class FakeLLMClient:
    """Return scripted payloads in order, repeating the last one on overflow."""

    def __init__(self, payloads: Sequence[Any]) -> None:
        if not payloads:
            raise ValueError("FakeLLMClient needs at least one payload")
        self._payloads = list(payloads)
        self.requests: list[LLMRequest] = []

    async def structured(
        self,
        messages: Sequence[ChatMessage],
        *,
        schema: type[BaseModel],
    ) -> Any:
        self.requests.append(LLMRequest(messages=tuple(messages), schema=schema))
        index = min(len(self.requests) - 1, len(self._payloads) - 1)
        return self._payloads[index]
