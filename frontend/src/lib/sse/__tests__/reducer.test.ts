import { describe, expect, it } from "vitest";
import {
  AGENT_ORDER,
  applySseEvent,
  applySseEvents,
  createRunState,
} from "@/lib/sse/reducer";
import { replay, runId, scripted, statuses } from "./support";

describe("createRunState", () => {
  it("starts idle with every agent waiting and no attempts", () => {
    const state = createRunState(runId);
    expect(state.status).toBe("idle");
    expect(state.currentAgent).toBeNull();
    expect(state.lastEventId).toBeNull();
    expect(state.handoffs).toEqual([]);
    expect(state.toolCalls).toEqual([]);
    for (const agent of AGENT_ORDER) {
      expect(state.agents[agent]).toMatchObject({
        status: "waiting",
        attempt: 0,
        validationFailures: [],
      });
    }
  });
});

describe("scripted happy path", () => {
  const state = replay();

  it("ends awaiting approval with each stage done", () => {
    expect(state.status).toBe("awaiting_approval");
    expect(state.currentAgent).toBe("reviewer");
    expect(state.version).toBe(1);
    expect(state.lastEventId).toBe("20");
    expect(statuses(state)).toEqual({
      brief: "done",
      research: "done",
      copywriter: "done",
      creative_director: "done",
      designer: "done",
      compliance: "done",
      reviewer: "done",
      supervisor: "waiting",
    });
  });

  it("records handoffs in arrival order", () => {
    expect(state.handoffs.map(({ from, to }) => `${from}->${to}`)).toEqual([
      "brief->research",
      "research->copywriter",
      "copywriter->creative_director",
      "creative_director->designer",
      "designer->compliance",
      "compliance->reviewer",
    ]);
  });

  it("records tool calls with agent, duration and status", () => {
    expect(state.toolCalls).toHaveLength(4);
    expect(state.toolCalls.map((call) => call.tool)).toEqual([
      "policy_lookup",
      "policy_lookup",
      "generate_image",
      "policy_lookup",
    ]);
    expect(state.toolCalls[2]).toMatchObject({
      agent: "designer",
      durationMs: 4200,
      status: "success",
    });
  });
});

describe("duplicate event ids", () => {
  it("returns the same state for an event already applied", () => {
    const state = replay();
    expect(applySseEvent(state, scripted[5])).toBe(state);
  });

  it("keeps the run replayable when the full stream is replayed", () => {
    const once = replay();
    const twice = applySseEvents(once, scripted);
    expect(twice).toBe(once);
    expect(twice.toolCalls).toHaveLength(4);
    expect(twice.handoffs).toHaveLength(6);
    expect(twice.seenEventIds).toHaveLength(scripted.length);
  });
});
