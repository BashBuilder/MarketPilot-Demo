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

  it("leaves an unexpected drop to the native EventSource reconnect", () => {
    const { result, source } = setup();
    act(() => {
      for (const event of scripted.slice(0, 3)) source.emitEvent(event);
    });
    expect(result.current.state.lastEventId).toBe("3");

    act(() => source.fail());
    expect(source.closed).toBe(false);
    expect(result.current.status).toBe("reconnecting");

    // The browser reopens the same EventSource and sends Last-Event-ID itself,
    // so the client must not create a second connection.
    act(() => vi.advanceTimersByTime(60_000));
    expect(FakeEventSource.instances).toHaveLength(1);

    act(() => source.open());
    expect(result.current.status).toBe("open");

    act(() => {
      // A replay includes the events already seen; deduplication keeps them
      // from being applied twice.
      for (const event of scripted) source.emitEvent(event);
    });
    // The replay ends at the approval gate, so the stream closes.
    expect(result.current.status).toBe("closed");
    expect(source.closed).toBe(true);
    expect(result.current.state.lastEventId).toBe("20");
    expect(result.current.state.toolCalls).toHaveLength(4);
    expect(result.current.state.handoffs).toHaveLength(6);
  });

  it("flags a silent open stream, then clears the flag on activity", () => {
    const { result } = renderHook(() =>
      useRunStream(runId, { stallAfterMs: 5_000 }),
    );
    const source = FakeEventSource.instances[0];
    act(() => source.open());

    act(() => vi.advanceTimersByTime(4_999));
    expect(result.current.stalled).toBe(false);

    act(() => vi.advanceTimersByTime(1));
    expect(result.current.stalled).toBe(true);

    act(() => source.emitEvent(scripted[0]));
    expect(result.current.stalled).toBe(false);

    act(() => vi.advanceTimersByTime(5_000));
    expect(result.current.stalled).toBe(true);

    // A reconnect pauses the stall timer and a native reopen starts it again.
    act(() => source.fail());
    expect(result.current.stalled).toBe(false);
    expect(result.current.status).toBe("reconnecting");

    act(() => source.open());
    act(() => vi.advanceTimersByTime(5_000));
    expect(result.current.stalled).toBe(true);
  });
});
