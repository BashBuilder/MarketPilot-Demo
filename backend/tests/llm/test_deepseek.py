"""DeepSeek adapter must hand invalid structured payloads back to the harness."""

from types import SimpleNamespace
from typing import Any

import pytest

from app.core.config import Settings
from app.llm.deepseek import DeepSeekLLMClient


class _Runnable:
    def __init__(self, result: Any) -> None:
        self._result = result

    async def ainvoke(self, messages: list[dict[str, str]]) -> Any:
        del messages
        return self._result


class _Model:
    def __init__(self, result: Any) -> None:
        self._result = result

    def with_structured_output(self, schema: object, **kwargs: object) -> _Runnable:
        del schema
        assert kwargs["include_raw"] is True
        return _Runnable(self._result)


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        deepseek_api_key="test-key",
        database_url="postgresql+asyncpg://user:pass@localhost/test",
        redis_url="redis://localhost:6379/0",
    )


def _client(result: Any) -> DeepSeekLLMClient:
    client = DeepSeekLLMClient(_settings())
    client._model = _Model(result)  # type: ignore[assignment]
    return client


async def test_invalid_tool_arguments_are_returned_for_verification() -> None:
    payload = {"brief_alignment": {"score": 8, "justification": "x" * 250}}
    raw = SimpleNamespace(
        tool_calls=[{"args": payload}],
        additional_kwargs={},
    )
    client = _client({"parsed": None, "raw": raw, "parsing_error": ValueError("too long")})

    result = await client.structured([{"role": "user", "content": "score"}], schema=object)

    assert result == payload


async def test_legacy_tool_call_shape_is_decoded() -> None:
    raw = SimpleNamespace(
        tool_calls=[],
        additional_kwargs={"tool_calls": [{"function": {"arguments": '{"total": 82.0}'}}]},
    )
    client = _client({"parsed": None, "raw": raw, "parsing_error": None})

    result = await client.structured([{"role": "user", "content": "score"}], schema=object)

    assert result == {"total": 82.0}


async def test_valid_payload_is_returned_as_parsed() -> None:
    parsed = SimpleNamespace(total=82.0)
    client = _client({"parsed": parsed, "raw": None, "parsing_error": None})

    result = await client.structured([{"role": "user", "content": "score"}], schema=object)

    assert result is parsed


async def test_a_missing_tool_call_with_a_parse_error_raises() -> None:
    error = ValueError("no tool call")
    client = _client({"parsed": None, "raw": None, "parsing_error": error})

    with pytest.raises(ValueError, match="no tool call"):
        await client.structured([{"role": "user", "content": "score"}], schema=object)
