"""Creative Director Agent: direction only, with no tool access at all."""

import re
from collections.abc import Iterable

from app.agents.base import AgentPreparation, BaseAgent, ToolInvoker
from app.agents.blocklist import BLOCKED_NAMES
from app.agents.outputs import CreativeDirection
from app.core.config import Settings, get_settings
from app.graph.state import WorkflowState
from app.harness.registry import AgentName
from app.harness.validators import Issue

__all__ = ["CreativeDirectionValidator", "CreativeDirectorAgent"]


class CreativeDirectionValidator:
    """Reject unsafe or unusable direction before the Designer sees it."""

    def __init__(
        self,
        max_image_prompt_length: int,
        blocked: Iterable[str] = BLOCKED_NAMES,
    ) -> None:
        self._max_length = max_image_prompt_length
        self._blocked = tuple(
            (name, re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE)) for name in blocked
        )

    def validate(self, value: CreativeDirection) -> list[Issue]:
        issues: list[Issue] = []
        for index, prompt in enumerate(value.image_prompts, start=1):
            text = prompt.strip()
            if not text:
                issues.append(f"image prompt {index} is empty")
            elif len(text) > self._max_length:
                issues.append(
                    f"image prompt {index} is {len(text)} characters; limit is {self._max_length}"
                )

        if not value.negative_prompts:
            issues.append("at least one negative prompt is required")

        fields = (
            ("image_prompts", tuple(value.image_prompts)),
            ("video_prompts", tuple(value.video_prompts)),
            ("style_guide", (value.style_guide,)),
            ("composition", (value.composition,)),
            ("negative_prompts", tuple(value.negative_prompts)),
        )
        for field, texts in fields:
            for text in texts:
                for name, pattern in self._blocked:
                    if pattern.search(text):
                        issues.append(f"{field} contains blocked named person or brand {name!r}")
        return issues


class CreativeDirectorAgent(BaseAgent[CreativeDirection]):
    """Write the visual direction without calling any tools."""

    name: AgentName = "creative_director"
    output_model = CreativeDirection
    prompt_name = "creative_director"

    async def prepare(
        self,
        state: WorkflowState,
        tools: ToolInvoker | None,
        *,
        settings: Settings | None = None,
    ) -> AgentPreparation[CreativeDirection]:
        del state, tools
        limit = (settings or get_settings()).max_image_prompt_length
        return AgentPreparation(validators=(CreativeDirectionValidator(limit),))
