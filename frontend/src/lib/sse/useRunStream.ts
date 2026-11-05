"use client";

import { useEffect, useRef, useState } from "react";
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

const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 15000;

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

export interface RunStream {
  state: RunState;
  status: RunStreamStatus;
}

type ParseResult =
  | { ok: true; event: SseEvent }
  | { ok: false; reason: string };

export function runStreamUrl(runId: string, lastEventId: string | null): string {
  const url = `${API_BASE_URL}/runs/${encodeURIComponent(runId)}/stream`;
  // EventSource cannot set request headers, so a manual reconnect carries the
  // cursor in the query string; native reconnects still send Last-Event-ID.
  return lastEventId === null
    ? url
    : `${url}?last_event_id=${encodeURIComponent(lastEventId)}`;
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
 */
export function useRunStream(runId: string): RunStream {
  const [state, setState] = useState<RunState>(() => createRunState(runId));
  const [status, setStatus] = useState<RunStreamStatus>("connecting");
  const lastEventIdRef = useRef<string | null>(null);

  // Pointing the hook at another run resets derived state during render, which
  // React supports for prop changes and keeps the effect free of cascades.
  if (state.runId !== runId) {
    setState(createRunState(runId));
    setStatus("connecting");
  }

  useEffect(() => {
    let disposed = false;
    let source: EventSource | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let attempts = 0;
    let terminal = false;

    lastEventIdRef.current = null;

    const closeAsTerminal = (stream: EventSource) => {
      terminal = true;
      if (retryTimer !== null) {
        clearTimeout(retryTimer);
        retryTimer = null;
      }
      stream.close();
      setStatus("closed");
    };

    const connect = () => {
      if (disposed) return;
      setStatus(attempts > 0 ? "reconnecting" : "connecting");
      const stream = new EventSource(
        runStreamUrl(runId, lastEventIdRef.current),
      );
      source = stream;

      stream.onopen = () => {
        attempts = 0;
        setStatus("open");
      };

      stream.onerror = () => {
        stream.close();
        if (disposed || terminal) return;
        setStatus("reconnecting");
        const delay = Math.min(
          RECONNECT_BASE_MS * 2 ** attempts,
          RECONNECT_MAX_MS,
        );
        attempts += 1;
        retryTimer = setTimeout(connect, delay);
      };

      for (const type of EVENT_TYPES) {
        stream.addEventListener(type, (raw: Event) => {
          const message = raw as MessageEvent<string>;
          const result = parseEvent(type, message);
          if (!result.ok) {
            setState((previous) =>
              withMalformedEvent(previous, message.data, result.reason),
            );
            return;
          }
          lastEventIdRef.current = result.event.id;
          setState((previous) => applySseEvent(previous, result.event));
          if (isTerminalEvent(result.event)) {
            closeAsTerminal(stream);
          }
        });
      }
    };

    connect();

    return () => {
      disposed = true;
      if (retryTimer !== null) clearTimeout(retryTimer);
      source?.close();
    };
  }, [runId]);

  return { state, status };
}
