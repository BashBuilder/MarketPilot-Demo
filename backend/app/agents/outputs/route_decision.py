"""Routing decision returned by the Supervisor agent."""

from typing import Annotated, Literal

from pydantic import Field

from app.agents.outputs.base import OutputModel

type AgentNode = Literal[
    "brief",
    "research",
    "copywriter",
    "creative_director",
    "designer",
    "compliance",
    "reviewer",
    "human",
    "end",
]


class RouteDecision(OutputModel):
    """The Supervisor's next step.

    ``human`` and ``end`` are terminal targets for escalation and completion;
    the Supervisor itself is never a target because it is the router.
    """

    next_node: AgentNode
    reason: Annotated[str, Field(min_length=5)]
    escalate: bool = False
