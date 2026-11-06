import { act, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FakeEventSource } from "@/lib/sse/__tests__/fake-event-source";
import { buildScriptedRun, campaignId, runId } from "@/mocks/fixtures";
import { LiveRunView } from "../live-run-view";

const scripted = buildScriptedRun(runId);

function setup() {
  const view = render(<LiveRunView campaignId={campaignId} runId={runId} />);
  const source = FakeEventSource.instances[0];
  if (!source) {
    throw new Error("The live view did not open an EventSource");
  }
  act(() => source.open());
  return { ...view, source };
}

beforeEach(() => {
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("LiveRunView", () => {
  it("replays the scripted run to the approval gate", () => {
    const { source } = setup();

    act(() => {
      for (const event of scripted) source.emitEvent(event);
    });

    expect(
      screen.getByRole("heading", { level: 1, name: "Ready for your review" }),
    ).toBeInTheDocument();

    const approval = screen.getByRole("region", {
      name: "Version 1 is waiting for approval",
    });
    expect(
      within(approval).getByRole("link", { name: "Review version 1" }),
    ).toHaveAttribute("href", `/campaigns/${campaignId}/versions/1`);

    const timeline = screen.getByRole("list", { name: "Agent pipeline" });
    expect(within(timeline).getAllByRole("listitem")).toHaveLength(8);
    expect(within(timeline).getAllByText("Done")).toHaveLength(7);
    expect(screen.getByText("Supervisor").closest("li")).toHaveAttribute(
      "data-status",
      "waiting",
    );

    const failures = screen.getByRole("region", { name: "Run failures" });
    expect(
      within(failures).getByText(
        "Email variant is missing a call to action.",
      ),
    ).toBeVisible();

    const handoffs = screen.getByRole("region", { name: "Handoffs" });
    expect(within(handoffs).getAllByRole("listitem")).toHaveLength(6);

    const tools = screen.getByRole("region", { name: "Tool calls" });
    expect(within(tools).getAllByRole("listitem")).toHaveLength(4);

    expect(
      screen.queryByText("Reconnecting to the live stream…"),
    ).not.toBeInTheDocument();
  });

  it("shows a reconnecting indicator when the stream drops", () => {
    vi.useFakeTimers();
    const { source } = setup();

    act(() => source.fail());

    expect(screen.getByRole("status")).toHaveTextContent(
      "Reconnecting to the live stream…",
    );
  });

  it("surfaces a fatal stream error in the ErrorState", () => {
    const { source } = setup();

    act(() => {
      source.emitEvent({
        id: "fatal-1",
        event: "error",
        data: {
          run_id: runId,
          timestamp: "2026-11-05T09:05:00.000Z",
          agent: "brief",
          message: "The model provider is unavailable.",
          recoverable: false,
        },
      });
    });

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("The run stopped");
    expect(alert).toHaveTextContent(
      "Brief: The model provider is unavailable.",
    );
  });

  it("surfaces malformed stream frames without crashing", () => {
    const { source } = setup();

    act(() => source.emitRaw("agent_started", "{not json", "bad-1"));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Some stream data could not be read",
    );
  });
});
