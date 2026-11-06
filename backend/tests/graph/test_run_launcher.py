"""Launcher integration: a scheduled run reaches a terminal stream event."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from workflow_loop_fakes import IDEA, default_agents
from workflow_run_support import run_settings

from app.database.models import CampaignStatus, RunStatus
from app.database.repositories import campaigns, runs
from app.events.bus import InMemoryEventBus
from app.harness.registry import ToolRegistry
from app.runs.launcher import WorkflowRunLauncher


async def _create_run(factory: async_sessionmaker[AsyncSession]) -> UUID:
    async with factory() as session:
        campaign = await campaigns.create(session, idea=IDEA)
        run = await runs.create(session, campaign_id=campaign.id)
        await session.commit()
        return run.id


def _launcher(
    factory: async_sessionmaker[AsyncSession],
    bus: InMemoryEventBus,
    agents=None,
) -> WorkflowRunLauncher:
    return WorkflowRunLauncher(
        agents=agents or default_agents(),
        llm=object(),
        registry=ToolRegistry(),
        session_factory=factory,
        event_bus=bus,
        settings=run_settings(),
    )


async def test_launcher_drives_the_run_to_the_approval_gate(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await _create_run(session_factory)
    bus = InMemoryEventBus()
    launcher = _launcher(session_factory, bus)

    await launcher.start(run_id)
    await launcher.wait()

    records = await bus.read(run_id, None)
    assert records[-1].event == "awaiting_approval"
    assert records[-1].data["run_id"] == str(run_id)
    async with session_factory() as session:
        stored = await runs.get(session, run_id)
        assert stored is not None
        campaign = await campaigns.get(session, stored.campaign_id)
    assert stored.status is RunStatus.AWAITING_APPROVAL
    assert campaign is not None
    assert campaign.status is CampaignStatus.AWAITING_APPROVAL


async def test_launcher_turns_an_unexpected_error_into_a_terminal_event(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await _create_run(session_factory)
    bus = InMemoryEventBus()
    agents = default_agents()
    agents["brief"].error = RuntimeError("provider exploded")
    launcher = _launcher(session_factory, bus, agents)

    await launcher.start(run_id)
    await launcher.wait()

    records = await bus.read(run_id, None)
    assert records[-1].event == "error"
    assert records[-1].data["recoverable"] is False
    async with session_factory() as session:
        stored = await runs.get(session, run_id)
        assert stored is not None
        campaign = await campaigns.get(session, stored.campaign_id)
    assert stored.status is RunStatus.FAILED
    assert campaign is not None
    assert campaign.status is CampaignStatus.FAILED
