import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { SseEvent } from "@/lib/schemas";
import { isTerminalEvent, useRunStream } from "@/lib/sse/useRunStream";
import { buildScriptedRun, runId } from "@/mocks/fixtures";
import { FakeEventSource } from "./fake-event-source";

const scripted = buildScriptedRun(runId);
const at = "2026-11-05T09:05:00.000Z";

const awaitingApproval = scripted[19];
const completed: SseEvent = {
  id: "21",
  event: "completed",
  data: {
    run_id: runId,
    timestamp: at,
    agent: "reviewer",
    version: 1,
    score: 86,
  },
};
const fatalError: SseEvent = {
  id: "22",
  event: "error",
  data: {
    run_id: runId,
    timestamp: at,
    agent: "designer",
    message: "Image provider failed",
    recoverable: false,
  },
};
const recoverableError: SseEvent = {
  id: "23",
  event: "error",
  data: {
    run_id: runId,
    timestamp: at,
    agent: "designer",
    message: "Image provider timed out",
    recoverable: true,
  },
};

function setup() {
  const view = renderHook(() => useRunStream(runId));
  const source = FakeEventSource.instances[0];
  act(() => source.open());
  return { ...view, source };
}

beforeEach(() => {
  FakeEventSource.instances = [];
  vi.useFakeTimers();
  vi.stubGlobal("EventSource", FakeEventSource);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("isTerminalEvent", () => {
  it("recognises the events that end a run stream", () => {
    expect(isTerminalEvent(awaitingApproval)).toBe(true);
    expect(isTerminalEvent(completed)).toBe(true);
    expect(isTerminalEvent(fatalError)).toBe(true);
    expect(isTerminalEvent(recoverableError)).toBe(false);
    expect(isTerminalEvent(scripted[0])).toBe(false);
  });
});

describe("useRunStream terminal events", () => {
  const cases: Array<[string, SseEvent, string]> = [
    ["awaiting_approval", awaitingApproval, "awaiting_approval"],
    ["completed", completed, "completed"],
    ["a non-recoverable error", fatalError, "failed"],
  ];

  it.each(cases)(
    "closes and does not reconnect after %s",
    (_label, terminalEvent, runStatus) => {
      const { result, source } = setup();

      act(() => source.emitEvent(terminalEvent));

      expect(source.closed).toBe(true);
      expect(result.current.status).toBe("closed");
      expect(result.current.state.status).toBe(runStatus);

      // A server close also fires onerror; it must not schedule a reconnect.
      act(() => source.fail());
      act(() => vi.advanceTimersByTime(60_000));

      expect(FakeEventSource.instances).toHaveLength(1);
      expect(result.current.status).toBe("closed");
    },
  );

  it("still reconnects after a drop following a recoverable error", () => {
    const { result, source } = setup();

    act(() => source.emitEvent(recoverableError));
    expect(source.closed).toBe(false);
    expect(result.current.status).toBe("open");

    act(() => source.fail());
    expect(result.current.status).toBe("reconnecting");

    act(() => vi.advanceTimersByTime(1000));
    expect(FakeEventSource.instances).toHaveLength(2);
  });
});
