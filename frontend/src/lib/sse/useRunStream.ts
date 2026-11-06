"use client";

import { useEffect, useState } from "react";
import { sseEvent, type SseEvent, type SseEventType } from "@/lib/schemas";
import { API_BASE_URL } from "@/lib/api/client";
import { applySseEvent, createRunState, type RunState } from "./reducer";
import { withMalformedEvent } from "./run-state";

const EVENT_TYPES: readonly SseEventType[] = [
  "agent_started",
  "agent_handoff",
  "tool_called",
  "validation_failed",
  "retrying",
  "awaiting_approval",
  "completed",
  "error",
];

/** A long model call is normal; only a stream silent this long is a stall. */
export const DEFAULT_STALL_AFTER_MS = 75_000;

export type RunStreamStatus = "connecting" | "open" | "reconnecting" | "closed";

/**
 * Events after which the server ends the stream. Reconnecting would replay a
 * finished run, so the client closes and stays closed; an unexpected drop is
 * the only reason to resume.
 */
export function isTerminalEvent(event: SseEvent): boolean {
  if (event.event === "awaiting_approval" || event.event === "completed") {
    return true;
  }
  return event.event === "error" && !event.data.recoverable;
}

export interface RunStreamOptions {
  /** How long an open stream may stay silent before it is flagged as stalled. */
  stallAfterMs?: number;
}

export interface RunStream {
  state: RunState;
  status: RunStreamStatus;
  stalled: boolean;
}

type ParseResult =
  | { ok: true; event: SseEvent }
  | { ok: false; reason: string };

export function runStreamUrl(runId: string): string {
  return `${API_BASE_URL}/runs/${encodeURIComponent(runId)}/stream`;
}

function parseEvent(
  type: SseEventType,
  message: MessageEvent<string>,
): ParseResult {
  let data: unknown;
  try {
    data = JSON.parse(message.data);
  } catch {
    return { ok: false, reason: "Event data was not valid JSON" };
  }

  const parsed = sseEvent.safeParse({
    id: message.lastEventId,
    event: type,
    data,
  });
  if (!parsed.success) {
    return {
      ok: false,
      reason: parsed.error.issues.map((issue) => issue.message).join("; "),
    };
  }
  return { ok: true, event: parsed.data };
}

/**
 * Opens the run's SSE stream, validates every event and folds it into a pure
 * run state. Bad payloads are recorded, never thrown, so one bad frame cannot
 * take the live view down.
 *
 * Unexpected drops are left to the browser's native EventSource reconnect so
 * the Last-Event-ID header is sent automatically. Closing and reopening with a
 * query parameter would drop that cursor.
 */
export function useRunStream(
  runId: string,
  { stallAfterMs = DEFAULT_STALL_AFTER_MS }: RunStreamOptions = {},
): RunStream {
  const [state, setState] = useState<RunState>(() => createRunState(runId));
  const [status, setStatus] = useState<RunStreamStatus>("connecting");
  const [stalled, setStalled] = useState(false);

  // Pointing the hook at another run resets derived state during render, which
  // React supports for prop changes and keeps the effect free of cascades.
  if (state.runId !== runId) {
    setState(createRunState(runId));
    setStatus("connecting");
    setStalled(false);
  }

  useEffect(() => {
    let disposed = false;
    let terminal = false;
    let stallTimer: ReturnType<typeof setTimeout> | null = null;

    const clearStallTimer = () => {
      if (stallTimer !== null) {
        clearTimeout(stallTimer);
        stallTimer = null;
      }
    };

    const armStallTimer = () => {
      clearStallTimer();
      setStalled(false);
      if (stallAfterMs <= 0) return;
      stallTimer = setTimeout(() => setStalled(true), stallAfterMs);
    };

    const closeAsTerminal = (stream: EventSource) => {
      terminal = true;
      clearStallTimer();
      setStalled(false);
      stream.close();
      setStatus("closed");
    };

    const stream = new EventSource(runStreamUrl(runId));

    stream.onopen = () => {
      setStatus("open");
      armStallTimer();
    };

    stream.onerror = () => {
      if (disposed || terminal) return;
      clearStallTimer();
      setStalled(false);
      setStatus("reconnecting");
    };

    for (const type of EVENT_TYPES) {
      stream.addEventListener(type, (raw: Event) => {
        const message = raw as MessageEvent<string>;
        armStallTimer();
        const result = parseEvent(type, message);
        if (!result.ok) {
          setState((previous) =>
            withMalformedEvent(previous, message.data, result.reason),
          );
          return;
        }
        setState((previous) => applySseEvent(previous, result.event));
        if (isTerminalEvent(result.event)) {
          closeAsTerminal(stream);
        }
      });
    }

    return () => {
      disposed = true;
      clearStallTimer();
      stream.close();
    };
  }, [runId, stallAfterMs]);

  return { state, status, stalled };
}
