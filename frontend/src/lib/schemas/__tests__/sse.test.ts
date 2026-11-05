import { describe, expect, it } from "vitest";
import { sseEvent } from "@/lib/schemas";
import { buildScriptedRun, runId, serializeSse } from "@/mocks/fixtures";

describe("SSE event schema", () => {
  const events = buildScriptedRun(runId);

  it("parses every event in the scripted run", () => {
    for (const event of events) {
      expect(sseEvent.safeParse(event).success).toBe(true);
    }
  });

  it("covers the required event types", () => {
    expect(new Set(events.map((event) => event.event))).toEqual(
      new Set([
        "agent_started",
        "agent_handoff",
        "tool_called",
        "validation_failed",
        "retrying",
        "awaiting_approval",
      ]),
    );
  });

  it("keeps event ids unique and ordered", () => {
    const ids = events.map((event) => event.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(ids).toEqual(ids.map((_id, index) => String(index + 1)));
  });

  it("parses a completed event and an error event", () => {
    expect(
      sseEvent.safeParse({
        id: "21",
        event: "completed",
        data: {
          run_id: runId,
          timestamp: "2026-11-05T09:05:00.000Z",
          agent: "reviewer",
          version: 1,
          score: 86,
        },
      }).success,
    ).toBe(true);

    expect(
      sseEvent.safeParse({
        id: "22",
        event: "error",
        data: {
          run_id: runId,
          timestamp: "2026-11-05T09:05:00.000Z",
          agent: "designer",
          message: "Image provider timed out",
          recoverable: true,
        },
      }).success,
    ).toBe(true);
  });

  it("parses the human approval actor and a nullable completed score", () => {
    expect(
      sseEvent.safeParse({
        id: "30",
        event: "completed",
        data: {
          run_id: runId,
          timestamp: "2026-11-05T09:05:00.000Z",
          agent: "human",
          version: 1,
          score: null,
        },
      }).success,
    ).toBe(true);
    expect(
      sseEvent.safeParse({
        id: "31",
        event: "agent_handoff",
        data: {
          run_id: runId,
          timestamp: "2026-11-05T09:05:00.000Z",
          agent: "reviewer",
          from: "reviewer",
          to: "human",
        },
      }).success,
    ).toBe(true);
  });

  it("parses a denied tool call", () => {
    expect(
      sseEvent.safeParse({
        id: "32",
        event: "tool_called",
        data: {
          run_id: runId,
          timestamp: "2026-11-05T09:05:00.000Z",
          agent: "designer",
          tool: "generate_image",
          duration_ms: 0,
          status: "denied",
        },
      }).success,
    ).toBe(true);
  });

  it("rejects unknown event names", () => {
    expect(
      sseEvent.safeParse({
        id: "1",
        event: "agent_finished",
        data: {
          run_id: runId,
          timestamp: "2026-11-05T09:00:00.000Z",
          agent: "brief",
        },
      }).success,
    ).toBe(false);
  });

  it("rejects a tool status outside the contract", () => {
    expect(
      sseEvent.safeParse({
        id: "1",
        event: "tool_called",
        data: {
          run_id: runId,
          timestamp: "2026-11-05T09:00:00.000Z",
          agent: "designer",
          tool: "generate_image",
          duration_ms: 10,
          status: "ok",
        },
      }).success,
    ).toBe(false);
  });

  it("rejects a handoff without a destination", () => {
    expect(
      sseEvent.safeParse({
        id: "1",
        event: "agent_handoff",
        data: {
          run_id: runId,
          timestamp: "2026-11-05T09:00:00.000Z",
          agent: "brief",
          from: "brief",
        },
      }).success,
    ).toBe(false);
  });

  it("serializes events with id, event and JSON data", () => {
    const body = serializeSse(events.slice(0, 1));
    expect(body).toContain("id: 1\n");
    expect(body).toContain("event: agent_started\n");
    expect(body).toContain(`data: {"run_id":"${runId}"`);
    expect(body.endsWith("\n\n")).toBe(true);
  });
});
