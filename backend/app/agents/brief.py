"""Brief Agent: turn a vague campaign idea into executable direction."""

from app.agents.base import BaseAgent
from app.agents.outputs import CampaignBrief
from app.harness.registry import AgentName
from app.harness.validators import BriefSemanticValidator

__all__ = ["BriefAgent"]


class BriefAgent(BaseAgent[CampaignBrief]):
    """Structure the user's idea without inventing claims or mutating state."""

    name: AgentName = "brief"
    output_model = CampaignBrief
    prompt_name = "brief"
    validators = (BriefSemanticValidator(),)
