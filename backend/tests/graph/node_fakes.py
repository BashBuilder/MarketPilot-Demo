"""Deterministic doubles for graph node tests."""

from collections.abc import Mapping, Sequence
from typing import Any

from app.agents.outputs import CampaignBrief
from app.core.errors import RetryExhausted
from app.graph.state import WorkflowState
from app.harness.verification import VerificationEvent

IDEA = "Create a campaign for a fictional hair-care product"

VALID_BRIEF = CampaignBrief(
    product="Aurelia Repair Shampoo",
    goal="Launch a repair line",
    audience="Adults aged 25 to 40",
    tone="Warm and confident",
    channels=["Instagram"],
    constraints=["No medical claims"],
)


class FakeAgent:
    """Return a scripted output or raise, while reporting verification events."""

    name = "brief"
    context_budget = 4000

    def __init__(
        self,
        output: CampaignBrief | None = None,
        *,
        error: Exception | None = None,
        verification: Sequence[VerificationEvent] = (),
    ) -> None:
        self.output = output
        self.error = error
        self.verification = verification
        self.seen_state: WorkflowState | None = None

    async def run(
        self,
        state: WorkflowState,
        llm: object,
        emit: Any = None,
        tools: object = None,
        *,
        settings: object = None,
    ) -> CampaignBrief:
        self.seen_state = state
        for event in self.verification:
            if emit is not None:
                await emit(event)
        if self.error is not None:
            raise self.error
        if self.output is None:
            raise RetryExhausted("fake agent has no output")
        return self.output


class RecordingEmitter:
    """Record (event, data) pairs in call order."""

    def __init__(self) -> None:
        self.events: list[tuple[str, Mapping[str, Any]]] = []

    async def __call__(self, event: str, data: Mapping[str, Any]) -> None:
        self.events.append((event, data))


def event_names(emitter: RecordingEmitter) -> list[str]:
    return [name for name, _ in emitter.events]
