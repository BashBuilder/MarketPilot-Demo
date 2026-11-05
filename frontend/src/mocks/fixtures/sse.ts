import type { AgentName, SseEvent } from "@/lib/schemas";

const startedAt = Date.parse("2026-11-05T09:00:00.000Z");

function at(seconds: number): string {
  return new Date(startedAt + seconds * 1000).toISOString();
}

function started(
  id: string,
  run: string,
  agent: AgentName,
  seconds: number,
): SseEvent {
  return {
    id,
    event: "agent_started",
    data: { run_id: run, timestamp: at(seconds), agent },
  };
}

function handoff(
  id: string,
  run: string,
  from: AgentName,
  to: AgentName,
  seconds: number,
): SseEvent {
  return {
    id,
    event: "agent_handoff",
    data: { run_id: run, timestamp: at(seconds), agent: from, from, to },
  };
}

function toolCalled(
  id: string,
  run: string,
  agent: AgentName,
  tool: string,
  durationMs: number,
  seconds: number,
): SseEvent {
  return {
    id,
    event: "tool_called",
    data: {
      run_id: run,
      timestamp: at(seconds),
      agent,
      tool,
      duration_ms: durationMs,
      status: "success",
    },
  };
}

/**
 * A deterministic run that exercises the UI states the timeline must render:
 * handoffs, tool calls, a validation failure with a retry, and the approval gate.
 */
export function buildScriptedRun(run: string, version = 1): SseEvent[] {
  return [
    started("1", run, "brief", 0),
    handoff("2", run, "brief", "research", 1),
    started("3", run, "research", 1),
    handoff("4", run, "research", "copywriter", 3),
    started("5", run, "copywriter", 3),
    toolCalled("6", run, "copywriter", "policy_lookup", 120, 5),
    {
      id: "7",
      event: "validation_failed",
      data: {
        run_id: run,
        timestamp: at(6),
        agent: "copywriter",
        reason: "Email variant is missing a call to action.",
      },
    },
    {
      id: "8",
      event: "retrying",
      data: {
        run_id: run,
        timestamp: at(6),
        agent: "copywriter",
        attempt: 1,
        max_attempts: 3,
      },
    },
    toolCalled("9", run, "copywriter", "policy_lookup", 95, 8),
    handoff("10", run, "copywriter", "creative_director", 9),
    started("11", run, "creative_director", 9),
    handoff("12", run, "creative_director", "designer", 12),
    started("13", run, "designer", 12),
    toolCalled("14", run, "designer", "generate_image", 4200, 18),
    handoff("15", run, "designer", "compliance", 19),
    started("16", run, "compliance", 19),
    toolCalled("17", run, "compliance", "policy_lookup", 80, 21),
    handoff("18", run, "compliance", "reviewer", 22),
    started("19", run, "reviewer", 22),
    {
      id: "20",
      event: "awaiting_approval",
      data: { run_id: run, timestamp: at(24), agent: "reviewer", version },
    },
  ];
}

export function serializeSse(events: SseEvent[]): string {
  return events
    .map(
      (event) =>
        `id: ${event.id}\nevent: ${event.event}\ndata: ${JSON.stringify(event.data)}\n\n`,
    )
    .join("");
}
