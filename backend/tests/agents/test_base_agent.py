"""BaseAgent behavior with a deterministic LLM: context, retries, no mutation."""

from pathlib import Path
from typing import Any

import pytest
from fake_llm import FakeLLMClient

from app.agents.base import BaseAgent
from app.agents.outputs import AudienceResearch, AudienceSegment, CampaignBrief
from app.core.config import Settings
from app.core.errors import RetryExhausted
from app.graph.state import WorkflowState
from app.harness.registry import AgentName

IDEA = "Create a campaign for a fictional hair-care product"

VALID_BRIEF: dict[str, Any] = {
    "product": "HydraSilk Shampoo",
    "goal": "Launch a campaign for colour-treated hair",
    "audience": "Adults aged 25 to 40",
    "tone": "Warm and confident",
    "channels": ["Instagram", "Email"],
    "constraints": ["No medical claims"],
}


class BriefAgent(BaseAgent[CampaignBrief]):
    name: AgentName = "brief"
    output_model = CampaignBrief
    prompt_name = "brief"


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


def write_prompt(tmp_path: Path, text: str = "Write a concise campaign brief.") -> Path:
    (tmp_path / "brief.md").write_text(f"version: 1\n\n{text}\n", encoding="utf-8")
    return tmp_path


def make_state() -> WorkflowState:
    brief = CampaignBrief(
        product="HydraSilk Shampoo",
        goal="Launch a campaign for colour-treated hair",
        audience="Adults aged 25 to 40",
        tone="Warm and confident",
        channels=["Instagram", "Email"],
        constraints=["No medical claims"],
    )
    research = AudienceResearch(
        segments=[
            AudienceSegment(
                name="Colour care",
                description="People treating dyed or highlighted hair",
            )
        ],
        pain_points=["Frizz after washing"],
        messaging_angles=["Softness without weight"],
        sources=[
            {
                "url": "https://example.com/research/hair-care-trends",
                "title": "Hair care trends: scalp-first routines",
            }
        ],
    )
    return WorkflowState(idea=IDEA, brief=brief, research=research)


async def test_only_mapped_context_reaches_the_prompt_and_state_is_unchanged(
    tmp_path: Path,
) -> None:
    state = make_state()
    before = state.model_dump()
    fake = FakeLLMClient([VALID_BRIEF])
    agent = BriefAgent()
    agent.prompts_dir = write_prompt(tmp_path)

    result = await agent.run(state, fake, settings=settings())

    assert isinstance(result, CampaignBrief)
    assert state.model_dump() == before
    request = fake.requests[0]
    assert request.schema is CampaignBrief
    user_message = request.messages[1]["content"]
    assert IDEA in user_message
    assert '"idea"' in user_message
    assert '"brief"' in user_message
    assert '"research"' not in user_message
    assert "Frizz after washing" not in user_message
    assert "Launch a campaign for colour-treated hair" in user_message
    assert '<untrusted source="workflow-state">' in user_message


async def test_invalid_output_retries_with_feedback(tmp_path: Path) -> None:
    fake = FakeLLMClient([{"product": ""}, VALID_BRIEF])
    agent = BriefAgent()
    agent.prompts_dir = write_prompt(tmp_path)
    sleeps = SleepRecorder()

    result = await agent.run(
        make_state(),
        fake,
        settings=settings(retry_max_attempts=2),
        sleep=sleeps,
        jitter=lambda: 0.0,
    )

    assert result.product == "HydraSilk Shampoo"
    assert len(fake.requests) == 2
    assert sleeps.delays == [0.5]
    retry_message = fake.requests[1].messages[-1]["content"]
    assert '<untrusted source="verification-feedback">' in retry_message
    assert "The previous output failed verification:" in retry_message
    assert "product:" in retry_message


async def test_exhausted_attempts_raise_retry_exhausted(tmp_path: Path) -> None:
    fake = FakeLLMClient([{"product": ""}])
    agent = BriefAgent()
    agent.prompts_dir = write_prompt(tmp_path)

    with pytest.raises(RetryExhausted) as excinfo:
        await agent.run(
            make_state(),
            fake,
            settings=settings(retry_max_attempts=2),
            sleep=SleepRecorder(),
            jitter=lambda: 0.0,
        )

    assert len(fake.requests) == 2
    assert excinfo.value.details["attempts"] == 2
