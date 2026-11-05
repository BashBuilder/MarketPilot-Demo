"""Creative Director Agent: direction validation and safe retries."""

from typing import Any

from fake_llm import FakeLLMClient

from app.agents.creative_director import CreativeDirectorAgent
from app.agents.outputs import AdCopySet, CampaignBrief, CreativeDirection
from app.core.config import Settings
from app.graph.state import WorkflowState

VALID_DIRECTION: dict[str, Any] = {
    "image_prompts": ["Soft-lit studio portrait with glossy, natural hair"],
    "video_prompts": ["Slow dolly shot through a sunlit bathroom"],
    "style_guide": "Warm neutrals, editorial calm, no glossy plastic textures",
    "composition": "Rule of thirds with generous negative space on the right",
    "negative_prompts": ["text", "watermark", "distorted hands"],
}

BLOCKED_DIRECTION = {
    **VALID_DIRECTION,
    "image_prompts": ["Editorial portrait of Taylor Swift with glossy hair"],
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
    return WorkflowState(
        idea="Create a campaign for a fictional hair-care product",
        brief=CampaignBrief(
            product="HydraSilk Shampoo",
            goal="Launch a campaign for colour-treated hair",
            audience="Adults aged 25 to 40",
            tone="Warm and confident",
            channels=["Instagram"],
            constraints=["No medical claims"],
        ),
        copy=AdCopySet(
            variants=[
                {
                    "channel": "Instagram",
                    "headline": "Repair starts here",
                    "description": "A weekly ritual for colour-treated hair.",
                    "cta": "Shop now",
                }
            ]
        ),
    )


async def test_valid_direction_passes() -> None:
    fake = FakeLLMClient([VALID_DIRECTION])

    result = await CreativeDirectorAgent().run(state(), fake, settings=settings())

    assert result.style_guide.startswith("Warm neutrals")
    assert len(fake.requests) == 1
    assert fake.requests[0].schema is CreativeDirection


async def test_blocklisted_name_triggers_a_retry_with_feedback() -> None:
    fake = FakeLLMClient([BLOCKED_DIRECTION, VALID_DIRECTION])
    sleeps = SleepRecorder()

    result = await CreativeDirectorAgent().run(
        state(),
        fake,
        settings=settings(retry_max_attempts=2),
        sleep=sleeps,
        jitter=lambda: 0.0,
    )

    assert result.image_prompts[0].startswith("Soft-lit")
    assert len(fake.requests) == 2
    assert sleeps.delays == [0.5]
    feedback = fake.requests[1].messages[-1]["content"]
    assert "taylor swift" in feedback
    assert "blocked named person or brand" in feedback


async def test_image_prompt_length_limit_comes_from_settings() -> None:
    long_prompt = {**VALID_DIRECTION, "image_prompts": ["x" * 60]}
    fake = FakeLLMClient([long_prompt, VALID_DIRECTION])

    result = await CreativeDirectorAgent().run(
        state(),
        fake,
        settings=settings(max_image_prompt_length=55, retry_max_attempts=2),
        sleep=SleepRecorder(),
        jitter=lambda: 0.0,
    )

    assert result.image_prompts[0].startswith("Soft-lit")
    feedback = fake.requests[1].messages[-1]["content"]
    assert "limit is 55" in feedback
