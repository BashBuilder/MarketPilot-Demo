"""DeepSeek structured-output client behind the ``LLMClient`` protocol.

The harness owns retries and validation, so this adapter makes exactly one
request per call and lets provider errors propagate to the node wrapper.
"""

from collections.abc import Sequence
from typing import Any

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.agents.contracts import ChatMessage
from app.core.config import Settings

DEFAULT_MODEL = "deepseek-chat"


class DeepSeekLLMClient:
    """Call DeepSeek through its OpenAI-compatible endpoint."""

    def __init__(self, settings: Settings, *, model: str = DEFAULT_MODEL) -> None:
        self._model = ChatOpenAI(
            model=model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            temperature=0,
            timeout=60.0,
            max_retries=0,
        )

    async def structured(
        self,
        messages: Sequence[ChatMessage],
        *,
        schema: type[BaseModel],
    ) -> Any:
        """Return one payload matching ``schema`` or raise a provider error."""
        runnable = self._model.with_structured_output(schema, method="function_calling")
        return await runnable.ainvoke([dict(message) for message in messages])
