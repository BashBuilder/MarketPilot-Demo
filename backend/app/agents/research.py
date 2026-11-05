"""Research Agent: retrieve attributable evidence, then write audience research."""

import json

from pydantic import TypeAdapter

from app.agents.base import AgentPreparation, BaseAgent, ToolInvoker
from app.agents.outputs import AudienceResearch
from app.core.errors import ToolError
from app.graph.state import WorkflowState
from app.harness.registry import AgentName
from app.harness.validators import ResearchSourceValidator
from app.tools.search_models import SearchArgs, SearchResult
from app.tools.search_tools import SEARCH_TOOL_NAME

__all__ = ["ResearchAgent"]

_SEARCH_RESULTS = TypeAdapter(list[SearchResult])


class ResearchAgent(BaseAgent[AudienceResearch]):
    """Ground research in search results and reject invented citations."""

    name: AgentName = "research"
    output_model = AudienceResearch
    prompt_name = "research"

    async def prepare(
        self, state: WorkflowState, tools: ToolInvoker | None
    ) -> AgentPreparation[AudienceResearch]:
        if tools is None:
            raise ToolError("research requires the search tool middleware")

        args = SearchArgs(query=state.idea[:500], max_results=5)
        raw = await tools.call(SEARCH_TOOL_NAME, args.model_dump())
        results = _SEARCH_RESULTS.validate_python(raw)
        context = json.dumps(
            [result.model_dump(mode="json") for result in results],
            ensure_ascii=False,
            sort_keys=True,
        )
        retrieved = (str(result.source_url) for result in results)
        return AgentPreparation(
            context=context,
            validators=(ResearchSourceValidator(retrieved),),
        )
