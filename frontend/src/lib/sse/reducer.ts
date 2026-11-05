import type { AgentName, SseEvent } from "@/lib/schemas";
import type { AgentRunState, RunState } from "./run-state";

export { AGENT_ORDER, createRunState } from "./run-state";
export type {
  AgentRunState, AgentStatus, HandoffRecord, RunErrorRecord, RunState,
  RunStatus, ToolCallRecord,
} from "./run-state";

function withAgent(
  state: RunState,
  agent: AgentName,
  patch: Partial<AgentRunState>,
): RunState {
  return {
    ...state,
    agents: { ...state.agents, [agent]: { ...state.agents[agent], ...patch } },
  };
}

/** A completed or failed run stays terminal even if late events arrive. */
function activeStatus(status: RunState["status"]): RunState["status"] {
  return status === "completed" || status === "failed" ? status : "running";
}

/**
 * Folds one SSE event into run state. Events are applied in arrival order and
 * an event id seen before is ignored, so reconnects may replay safely.
 */
export function applySseEvent(state: RunState, event: SseEvent): RunState {
  if (state.seenEventIds.includes(event.id)) {
    return state;
  }

  const base: RunState = {
    ...state,
    lastEventId: event.id,
    seenEventIds: [...state.seenEventIds, event.id],
  };
  const agent = event.data.agent;

  switch (event.event) {
    case "agent_started":
      return withAgent(
        { ...base, status: activeStatus(state.status), currentAgent: agent },
        agent,
        { status: "running", attempt: 1, maxAttempts: 1 },
      );
    case "agent_handoff":
      return {
        ...withAgent(base, event.data.from, { status: "done" }),
        status: activeStatus(state.status),
        currentAgent: event.data.to,
        handoffs: [
          ...state.handoffs,
          {
            id: event.id,
            from: event.data.from,
            to: event.data.to,
            timestamp: event.data.timestamp,
          },
        ],
      };
    case "tool_called": {
      const next: RunState = {
        ...base,
        status: activeStatus(state.status),
        toolCalls: [
          ...state.toolCalls,
          {
            id: event.id,
            agent,
            tool: event.data.tool,
            durationMs: event.data.duration_ms,
            status: event.data.status,
            timestamp: event.data.timestamp,
          },
        ],
      };
      const previous = state.agents[agent].status;
      return previous === "waiting" || previous === "failed"
        ? withAgent(next, agent, { status: "running" })
        : next;
    }
    case "validation_failed":
      return withAgent(base, agent, {
        status: "failed",
        validationFailures: [
          ...state.agents[agent].validationFailures,
          event.data.reason,
        ],
      });
    case "retrying":
      return withAgent(base, agent, {
        status: "retrying",
        attempt: Math.min(event.data.attempt + 1, event.data.max_attempts),
        maxAttempts: event.data.max_attempts,
      });
    case "awaiting_approval":
      return withAgent(
        {
          ...base,
          status: "awaiting_approval",
          currentAgent: agent,
          version: event.data.version,
        },
        agent,
        { status: "done" },
      );
    case "completed":
      return withAgent(
        {
          ...base,
          status: "completed",
          currentAgent: agent,
          version: event.data.version,
          score: event.data.score,
        },
        agent,
        { status: "done" },
      );
    case "error": {
      const next = withAgent(
        {
          ...base,
          errors: [
            ...state.errors,
            {
              id: event.id,
              agent,
              message: event.data.message,
              recoverable: event.data.recoverable,
            },
          ],
        },
        agent,
        { status: "failed" },
      );
      return event.data.recoverable ? next : { ...next, status: "failed" };
    }
  }
}

export function applySseEvents(
  state: RunState,
  events: readonly SseEvent[],
): RunState {
  return events.reduce(applySseEvent, state);
}
