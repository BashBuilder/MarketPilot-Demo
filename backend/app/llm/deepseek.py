"""DeepSeek structured-output client behind the ``LLMClient`` protocol.

The harness owns validation retries, so this adapter makes exactly one
structured request per call. It deliberately returns the raw tool arguments
instead of letting LangChain validate the payload: a schema miss must reach
``run_with_verification`` so the validation error becomes retry feedback.

The transport still gets a small retry budget. A transient connect error or
server disconnect says nothing about the model's answer, so retrying it here
(handled by the OpenAI SDK, including ``Retry-After``) is cheaper than failing
the whole run and asking a human to start over.
"""

import json
from collections.abc import Sequence
from typing import Any

import httpx
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.agents.contracts import ChatMessage
from app.core.config import Settings

DEFAULT_MODEL = "deepseek-chat"
CONNECT_TIMEOUT_SECONDS = 10.0


class DeepSeekLLMClient:
    """Call DeepSeek through its OpenAI-compatible endpoint."""

    def __init__(self, settings: Settings, *, model: str = DEFAULT_MODEL) -> None:
        # ChatOpenAI is only the OpenAI-compatible transport. The endpoint and
        # model below are DeepSeek's; no OpenAI model is configured anywhere.
        self._model = ChatOpenAI(
            model=model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            temperature=0,
            timeout=httpx.Timeout(
                settings.deepseek_timeout_seconds,
                connect=CONNECT_TIMEOUT_SECONDS,
            ),
            max_retries=settings.deepseek_max_retries,
        )

    async def structured(
        self,
        messages: Sequence[ChatMessage],
        *,
        schema: type[BaseModel],
    ) -> Any:
        """Return the raw payload for ``schema`` or raise a provider error."""
        runnable = self._model.with_structured_output(
            schema,
            method="function_calling",
            include_raw=True,
        )
        result = await runnable.ainvoke([dict(message) for message in messages])
        if not isinstance(result, dict):
            return result

        parsed = result.get("parsed")
        if parsed is not None:
            return parsed

        raw_args = _tool_call_args(result.get("raw"))
        if raw_args is not None:
            return raw_args

        # DeepSeek occasionally answers with the JSON object in ``content``
        # even when a tool call was requested. Accept that shape instead of
        # handing an empty payload to the schema verifier.
        content_args = _content_args(result.get("raw"))
        if content_args is not None:
            return content_args

        error = result.get("parsing_error")
        if error is not None:
            raise error
        return {}


def _tool_call_args(raw: Any) -> dict[str, Any] | None:
    """Extract the first tool call's arguments from a LangChain message."""
    calls = getattr(raw, "tool_calls", None)
    if isinstance(calls, list) and calls:
        first = calls[0]
        if isinstance(first, dict):
            args = first.get("args")
            if isinstance(args, dict) and args:
                return args

    additional = getattr(raw, "additional_kwargs", None)
    if isinstance(additional, dict):
        legacy = additional.get("tool_calls")
        if isinstance(legacy, list) and legacy:
            first_call = legacy[0]
            function = first_call.get("function") if isinstance(first_call, dict) else None
            arguments = function.get("arguments") if isinstance(function, dict) else None
            if isinstance(arguments, str):
                decoded = _loads_object(arguments)
                if decoded is not None:
                    return decoded
    return None


def _content_args(raw: Any) -> dict[str, Any] | None:
    """Parse a JSON object some models place in the message content.

    A model that ignores ``tool_choice`` can still produce a valid structured
    payload; returning it keeps the harness's schema verification useful
    instead of reporting every field as missing.
    """
    content = getattr(raw, "content", None)
    if isinstance(content, list):
        content = "".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") in {None, "text"}
        )
    if not isinstance(content, str):
        return None

    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return _loads_object(text) if text else None


def _loads_object(text: str) -> dict[str, Any] | None:
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        return None
    return decoded if isinstance(decoded, dict) and decoded else None
