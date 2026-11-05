import type { AgentName, SseEvent } from "@/lib/schemas";
import { buildScriptedRun, runId } from "@/mocks/fixtures";
import {
  AGENT_ORDER,
  applySseEvents,
  createRunState,
  type RunState,
} from "@/lib/sse/reducer";

export { runId };

export const scripted = buildScriptedRun(runId);
export const at = "2026-11-05T09:05:00.000Z";

export function replay(events: readonly SseEvent[] = scripted): RunState {
  return applySseEvents(createRunState(runId), events);
}

/** Status per agent, ordered, for readable whole-timeline assertions. */
export function statuses(state: RunState): Record<AgentName, string> {
  return Object.fromEntries(
    AGENT_ORDER.map((agent) => [agent, state.agents[agent].status]),
  ) as Record<AgentName, string>;
}
