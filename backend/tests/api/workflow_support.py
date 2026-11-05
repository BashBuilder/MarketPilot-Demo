"""Seeded gate state and scripted agents for approval API tests."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.contracts import EventEmitter, LLMClient, ToolInvoker
from app.agents.outputs import CreativeScore
from app.api.dependencies import DEFAULT_WORKFLOW_SERVICES, WorkflowServices
from app.core.config import Settings
from app.database.repositories import campaigns, runs, versions
from app.graph.routing import PIPELINE
from app.graph.state import WorkflowState
from app.graph.versioning import PACKAGE_FIELDS
from app.harness.checkpoints import request_approval, save_checkpoint
from app.harness.registry import AgentName

IDEA = "API approval test campaign"
_SCORE_DIMENSIONS = (
    "brief_alignment",
    "audience_fit",
    "copy_quality",
    "visual_quality",
    "compliance_risk",
)


async def seed_at_gate(
    factory: async_sessionmaker[AsyncSession],
) -> tuple[UUID, UUID]:
    """Create a campaign with version 1 and a run paused at the human gate."""
    async with factory() as session:
        campaign = await campaigns.create(session, idea=IDEA)
        run = await runs.create(session, campaign_id=campaign.id)
        state = WorkflowState(idea=IDEA, versions=[1], status="awaiting_approval")
        await versions.create(
            session,
            campaign_id=campaign.id,
            package={field: None for field in PACKAGE_FIELDS},
        )
        await save_checkpoint(session, run.id, "reviewer", state)
        await request_approval(session, run.id)
        await session.commit()
        return run.id, campaign.id


class StubAgent:
    """Return a scripted score for the reviewer and fail if any other node runs."""

    context_budget = 4000

    def __init__(self, name: AgentName, output: CreativeScore | None = None) -> None:
        self.name = name
        self.output = output

    async def run(
        self,
        state: WorkflowState,
        llm: LLMClient,
        emit: EventEmitter | None = None,
        tools: ToolInvoker | None = None,
        *,
        settings: Settings | None = None,
    ) -> CreativeScore:
        del state, llm, emit, tools, settings
        if self.output is None:
            raise AssertionError(f"{self.name} should not run")
        return self.output


def reviewer_services(value: float = 9.0) -> WorkflowServices:
    """Build services whose only real agent is a scripted reviewer."""
    agents: dict[AgentName, StubAgent] = {name: StubAgent(name) for name in PIPELINE}
    agents["reviewer"] = StubAgent("reviewer", _score(value))
    return WorkflowServices(
        agents=agents,
        llm=DEFAULT_WORKFLOW_SERVICES.llm,
        tools={},
        emit=DEFAULT_WORKFLOW_SERVICES.emit,
    )


def _score(value: float) -> CreativeScore:
    dimensions = {
        name: {"score": value, "justification": f"{name} is strong."} for name in _SCORE_DIMENSIONS
    }
    return CreativeScore(**dimensions, total=value * 10)
