import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useRunStream } from "@/lib/sse/useRunStream";
import { buildScriptedRun, runId } from "@/mocks/fixtures";
import { FakeEventSource } from "./fake-event-source";

const scripted = buildScriptedRun(runId);

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

describe("useRunStream error handling", () => {
  it("logs malformed events as state errors without throwing", () => {
    const { result, source } = setup();
    act(() => {
      source.emitRaw("agent_started", "{not json", "bad-1");
      source.emitRaw("agent_started", JSON.stringify({ run_id: runId }), "bad-2");
    });

    expect(result.current.state.malformedEvents).toHaveLength(2);
    expect(result.current.state.malformedEvents[0].reason).toContain("JSON");
    expect(result.current.state.lastEventId).toBeNull();
    expect(result.current.state.status).toBe("idle");
    expect(result.current.status).toBe("open");

    act(() => source.emitEvent(scripted[0]));
    expect(result.current.state.agents.brief.status).toBe("running");
    expect(result.current.state.lastEventId).toBe("1");
  });
});

describe("useRunStream cleanup", () => {
  it("closes the open stream on unmount", () => {
    const { source, unmount } = setup();
    unmount();
    expect(source.closed).toBe(true);
  });

  it("leaves the dropped stream to the browser and closes it on unmount", () => {
    const { result, source, unmount } = setup();
    act(() => source.fail());
    expect(result.current.status).toBe("reconnecting");
    expect(source.closed).toBe(false);

    unmount();
    expect(source.closed).toBe(true);
    act(() => vi.advanceTimersByTime(60_000));
    expect(FakeEventSource.instances).toHaveLength(1);
  });
});
