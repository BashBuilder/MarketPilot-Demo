"""Brief Agent: valid output and a schema failure retried with feedback."""

from typing import Any

from fake_llm import FakeLLMClient

from app.agents.brief import BriefAgent
from app.agents.outputs import CampaignBrief
from app.core.config import Settings
from app.graph.state import WorkflowState
from app.harness.validators import BriefSemanticValidator

IDEA = "Create a campaign for a fictional hair-care product"

VALID_BRIEF: dict[str, Any] = {
    "product": "HydraSilk Shampoo",
    "goal": "Launch a campaign for colour-treated hair",
    "audience": "Adults aged 25 to 40",
    "tone": "Warm and confident",
    "channels": ["Instagram", "Email"],
    "constraints": ["No medical claims"],
}


class SleepRecorder:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


def settings(**overrides: object) -> Settings:
    return Settings(
        _env_file=None,
        deepseek_api_key="test-key",
        database_url="postgresql+asyncpg://user:pass@localhost/marketpilot",
        redis_url="redis://localhost:6379/0",
        **overrides,
    )


def state() -> WorkflowState:
    return WorkflowState(idea=IDEA)


async def test_valid_brief_passes() -> None:
    fake = FakeLLMClient([VALID_BRIEF])

    result = await BriefAgent().run(state(), fake, settings=settings())

    assert isinstance(result, CampaignBrief)
    assert result.product == "HydraSilk Shampoo"
    assert result.audience == "Adults aged 25 to 40"
    assert fake.requests[0].schema is CampaignBrief
    assert len(fake.requests) == 1


async def test_missing_audience_retries_with_the_issue_in_feedback() -> None:
    missing_audience = {key: value for key, value in VALID_BRIEF.items() if key != "audience"}
    fake = FakeLLMClient([missing_audience, VALID_BRIEF])
    sleeps = SleepRecorder()

    result = await BriefAgent().run(
        state(),
        fake,
        settings=settings(retry_max_attempts=2),
        sleep=sleeps,
        jitter=lambda: 0.0,
    )

    assert result.audience == "Adults aged 25 to 40"
    assert len(fake.requests) == 2
    assert sleeps.delays == [0.5]
    retry_message = fake.requests[1].messages[-1]["content"]
    assert '<untrusted source="verification-feedback">' in retry_message
    assert "audience: Field required" in retry_message


def test_semantic_validator_flags_blank_fields_and_no_channels() -> None:
    brief = CampaignBrief.model_construct(
        product=" ",
        goal="Launch a campaign",
        audience="",
        tone="Warm",
        channels=[],
    )

    issues = BriefSemanticValidator().validate(brief)

    assert "product must not be empty" in issues
    assert "audience must not be empty" in issues
    assert "at least one channel is required" in issues
