import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { API_BASE_URL } from "@/lib/api/client";
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

describe("useRunStream", () => {
  it("reports connecting, then opens the run stream", () => {
    const { result } = renderHook(() => useRunStream(runId));
    expect(result.current.status).toBe("connecting");
    expect(FakeEventSource.instances[0].url).toBe(
      `${API_BASE_URL}/runs/${runId}/stream`,
    );

    act(() => FakeEventSource.instances[0].open());
    expect(result.current.status).toBe("open");
  });

  it("applies events in arrival order and tracks the last id", () => {
    const { result, source } = setup();
    act(() => {
      for (const event of scripted.slice(0, 5)) source.emitEvent(event);
    });

    expect(result.current.state.lastEventId).toBe("5");
    expect(result.current.state.agents.brief.status).toBe("done");
    expect(result.current.state.agents.research.status).toBe("done");
    expect(result.current.state.agents.copywriter.status).toBe("running");
    expect(result.current.state.handoffs).toHaveLength(2);
  });

  it("reconnects with the last event id after a drop", () => {
    const { result, source } = setup();
    act(() => {
      for (const event of scripted.slice(0, 3)) source.emitEvent(event);
    });
    expect(result.current.state.lastEventId).toBe("3");

    act(() => source.fail());
    expect(source.closed).toBe(true);
    expect(result.current.status).toBe("reconnecting");
    expect(FakeEventSource.instances).toHaveLength(1);

    act(() => vi.advanceTimersByTime(1000));
    expect(FakeEventSource.instances).toHaveLength(2);
    const resumed = FakeEventSource.instances[1];
    expect(resumed.url).toBe(
      `${API_BASE_URL}/runs/${runId}/stream?last_event_id=3`,
    );

    act(() => {
      resumed.open();
      for (const event of scripted) resumed.emitEvent(event);
    });
    expect(result.current.status).toBe("open");
    expect(result.current.state.lastEventId).toBe("20");
    expect(result.current.state.toolCalls).toHaveLength(4);
    expect(result.current.state.handoffs).toHaveLength(6);
  });
});
