import type { AgentName, EventActor } from "@/lib/schemas";
import { agentName } from "@/lib/schemas";

export const AGENT_ORDER: readonly AgentName[] = agentName.options;

export function isAgentName(value: EventActor): value is AgentName {
  return agentName.safeParse(value).success;
}

export type AgentStatus = "waiting" | "running" | "retrying" | "failed" | "done";

export type RunStatus =
  | "idle"
  | "running"
  | "awaiting_approval"
  | "completed"
  | "failed";

export interface AgentRunState {
  status: AgentStatus;
  /** Attempt in flight, 1-based; a retry raises it without a new start event. */
  attempt: number;
  maxAttempts: number;
  validationFailures: readonly string[];
}

export interface HandoffRecord {
  id: string;
  from: EventActor;
  to: EventActor;
  timestamp: string;
}

export interface ToolCallRecord {
  id: string;
  agent: AgentName;
  tool: string;
  durationMs: number;
  status: "success" | "error" | "denied";
  timestamp: string;
}

export interface RunErrorRecord {
  id: string;
  agent: EventActor;
  message: string;
  recoverable: boolean;
}

export interface MalformedEventRecord {
  raw: string;
  reason: string;
}

export interface RunState {
  runId: string;
  status: RunStatus;
  currentAgent: EventActor | null;
  agents: Record<AgentName, AgentRunState>;
  handoffs: readonly HandoffRecord[];
  toolCalls: readonly ToolCallRecord[];
  errors: readonly RunErrorRecord[];
  malformedEvents: readonly MalformedEventRecord[];
  version: number | null;
  score: number | null;
  seenEventIds: readonly string[];
  lastEventId: string | null;
}

function emptyAgent(): AgentRunState {
  return {
    status: "waiting",
    attempt: 0,
    maxAttempts: 1,
    validationFailures: [],
  };
}

function createAgents(): Record<AgentName, AgentRunState> {
  return {
    brief: emptyAgent(),
    research: emptyAgent(),
    copywriter: emptyAgent(),
    creative_director: emptyAgent(),
    designer: emptyAgent(),
    compliance: emptyAgent(),
    reviewer: emptyAgent(),
    supervisor: emptyAgent(),
  };
}

export function createRunState(runId: string): RunState {
  return {
    runId,
    status: "idle",
    currentAgent: null,
    agents: createAgents(),
    handoffs: [],
    toolCalls: [],
    errors: [],
    malformedEvents: [],
    version: null,
    score: null,
    seenEventIds: [],
    lastEventId: null,
  };
}

/** Keeps a bad stream payload visible without failing the whole run. */
export function withMalformedEvent(
  state: RunState,
  raw: string,
  reason: string,
): RunState {
  return {
    ...state,
    malformedEvents: [...state.malformedEvents, { raw, reason }],
  };
}
