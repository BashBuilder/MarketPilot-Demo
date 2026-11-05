import type { AgentName, SseEvent } from "@/lib/schemas";
import type { AgentRunState, RunState } from "./run-state";
import { isAgentName } from "./run-state";

export { AGENT_ORDER, createRunState, isAgentName } from "./run-state";
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
      if (!isAgentName(agent)) {
        return { ...base, status: activeStatus(state.status), currentAgent: agent };
      }
      return withAgent(
        { ...base, status: activeStatus(state.status), currentAgent: agent },
        agent,
        { status: "running", attempt: 1, maxAttempts: 1 },
      );
    case "agent_handoff": {
      const handedOff = isAgentName(event.data.from)
        ? withAgent(base, event.data.from, { status: "done" })
        : base;
      return {
        ...handedOff,
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
    }
    case "tool_called": {
      if (!isAgentName(agent)) return base;
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
      if (!isAgentName(agent)) return base;
      return withAgent(base, agent, {
        status: "failed",
        validationFailures: [
          ...state.agents[agent].validationFailures,
          event.data.reason,
        ],
      });
    case "retrying":
      if (!isAgentName(agent)) return base;
      return withAgent(base, agent, {
        status: "retrying",
        attempt: Math.min(event.data.attempt + 1, event.data.max_attempts),
        maxAttempts: event.data.max_attempts,
      });
    case "awaiting_approval": {
      const next: RunState = {
        ...base,
        status: "awaiting_approval",
        currentAgent: agent,
        version: event.data.version,
      };
      return isAgentName(agent)
        ? withAgent(next, agent, { status: "done" })
        : next;
    }
    case "completed": {
      const next: RunState = {
        ...base,
        status: "completed",
        currentAgent: agent,
        version: event.data.version,
        score: event.data.score,
      };
      return isAgentName(agent)
        ? withAgent(next, agent, { status: "done" })
        : next;
    }
    case "error": {
      const next: RunState = {
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
      };
      const failed = isAgentName(agent)
        ? withAgent(next, agent, { status: "failed" })
        : next;
      return event.data.recoverable ? failed : { ...failed, status: "failed" };
    }
  }
}

export function applySseEvents(
  state: RunState,
  events: readonly SseEvent[],
): RunState {
  return events.reduce(applySseEvent, state);
}
