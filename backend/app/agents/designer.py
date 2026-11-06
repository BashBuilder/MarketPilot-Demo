"""Designer Agent: execute the creative direction as verified image assets.

Unlike the text agents, the Designer's work is deterministic tool execution:
the Creative Director already chose the prompts, so the Designer generates one
file per prompt and records what the image tool returns. There is deliberately
no retry loop around tool calls, so a guardrail denial stops the node instead of
burning more of the run's image budget.
"""

import random
from collections.abc import Callable, Sequence
from pathlib import Path

from app.agents.base import BaseAgent, EventEmitter, LLMClient, ToolInvoker
from app.agents.designer_targets import (
    flagged_indices,
    revision_instruction,
    seed_for,
    to_asset,
)
from app.agents.outputs import Asset, AssetSet, ComplianceItem, CreativeDirection
from app.core.config import Settings, get_settings
from app.core.errors import ToolError, ValidationFailure
from app.graph.state import WorkflowState
from app.harness.registry import AgentName
from app.harness.retries import Sleep, default_sleep
from app.harness.verification import AssetSemanticValidator, verify_output
from app.tools.image_models import EditImageArgs, GeneratedImage, GenerateImageArgs

__all__ = ["DesignerAgent"]

_GENERATE = "generate_image"
_EDIT = "edit_image"


class DesignerAgent(BaseAgent[AssetSet]):
    """Generate visuals, or revise only the assets compliance flagged."""

    name: AgentName = "designer"
    output_model = AssetSet
    prompt_name = "designer"

    async def run(
        self,
        state: WorkflowState,
        llm: LLMClient | None = None,
        emit: EventEmitter | None = None,
        tools: ToolInvoker | None = None,
        *,
        settings: Settings | None = None,
        sleep: Sleep = default_sleep,
        jitter: Callable[[], float] = random.random,
    ) -> AssetSet:
        """Produce verified assets without mutating state or retrying denials."""
        del llm, emit, sleep, jitter
        limits = settings or get_settings()
        direction = state.direction
        if direction is None:
            raise ValidationFailure("designer requires a creative direction")
        if tools is None:
            raise ToolError("designer requires the image tool middleware")

        payload = await self._build(state, direction, tools, limits)
        parsed, issues = verify_output(
            self.output_model,
            payload,
            AssetSemanticValidator(limits.asset_dir),
        )
        if parsed is None or issues:
            raise ValidationFailure(
                "designer produced invalid assets",
                details={"issues": issues},
            )
        return parsed

    async def _build(
        self,
        state: WorkflowState,
        direction: CreativeDirection,
        tools: ToolInvoker,
        settings: Settings,
    ) -> AssetSet:
        existing = state.assets
        if existing is not None and state.compliance is not None:
            return await self._revise(existing, state.compliance.items, tools, settings)
        return AssetSet(assets=await self._generate(direction, tools, settings))

    async def _generate(
        self,
        direction: CreativeDirection,
        tools: ToolInvoker,
        settings: Settings,
    ) -> list[Asset]:
        negative = ", ".join(direction.negative_prompts)
        assets: list[Asset] = []
        # The Creative Director may return any number of prompts; generate only
        # the first few so a long direction cannot exhaust the run's image cap.
        prompts = direction.image_prompts[: settings.max_generated_images_per_run]
        for index, prompt in enumerate(prompts):
            args = GenerateImageArgs(
                prompt=prompt,
                negative_prompt=negative,
                seed=seed_for(prompt, index),
            )
            raw = await tools.call(_GENERATE, args.model_dump())
            assets.append(to_asset(GeneratedImage.model_validate(raw), settings.asset_dir))
        return assets

    async def _revise(
        self,
        existing: AssetSet,
        items: Sequence[ComplianceItem],
        tools: ToolInvoker,
        settings: Settings,
    ) -> AssetSet:
        failed = tuple(item for item in items if not item.passed)
        flagged = flagged_indices(failed, existing.assets)
        assets = list(existing.assets)
        for number in sorted(flagged):
            current = assets[number - 1]
            instruction = revision_instruction(failed, current, number)
            args = EditImageArgs(image_path=Path(current.uri), instruction=instruction)
            raw = await tools.call(_EDIT, args.model_dump())
            assets[number - 1] = to_asset(GeneratedImage.model_validate(raw), settings.asset_dir)
        return AssetSet(assets=assets)
