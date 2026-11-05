import { describe, expect, it } from "vitest";
import { applySseEvent } from "@/lib/sse/reducer";
import { at, replay, runId, scripted } from "./support";

describe("validation failure and retry", () => {
  it("shows the failure, then the in-flight retry attempt", () => {
    const failed = replay(scripted.slice(0, 7));
    expect(failed.agents.copywriter.status).toBe("failed");
    expect(failed.agents.copywriter.validationFailures).toEqual([
      "Email variant is missing a call to action.",
    ]);

    const retrying = applySseEvent(failed, scripted[7]);
    expect(retrying.agents.copywriter.status).toBe("retrying");
    expect(retrying.agents.copywriter.attempt).toBe(2);
    expect(retrying.agents.copywriter.maxAttempts).toBe(3);

    const working = applySseEvent(retrying, scripted[8]);
    expect(working.agents.copywriter.status).toBe("retrying");
  });

  it("finishes the agent without losing the retry count", () => {
    const done = replay();
    expect(done.agents.copywriter.status).toBe("done");
    expect(done.agents.copywriter.attempt).toBe(2);
  });

  it("resets the attempt counter when the agent starts again", () => {
    const restarted = applySseEvent(replay(), {
      id: "30",
      event: "agent_started",
      data: { run_id: runId, timestamp: at, agent: "copywriter" },
    });
    expect(restarted.agents.copywriter).toMatchObject({
      status: "running",
      attempt: 1,
      maxAttempts: 1,
    });
  });
});

describe("terminal events", () => {
  it("captures the final version and score from completed", () => {
    const state = applySseEvent(replay(), {
      id: "21",
      event: "completed",
      data: {
        run_id: runId,
        timestamp: at,
        agent: "reviewer",
        version: 2,
        score: 86,
      },
    });
    expect(state.status).toBe("completed");
    expect(state.version).toBe(2);
    expect(state.score).toBe(86);
  });

  it("fails the run on a non-recoverable error", () => {
    const state = applySseEvent(replay(scripted.slice(0, 1)), {
      id: "22",
      event: "error",
      data: {
        run_id: runId,
        timestamp: at,
        agent: "brief",
        message: "DeepSeek timed out",
        recoverable: false,
      },
    });
    expect(state.status).toBe("failed");
    expect(state.agents.brief.status).toBe("failed");
    expect(state.errors).toEqual([
      {
        id: "22",
        agent: "brief",
        message: "DeepSeek timed out",
        recoverable: false,
      },
    ]);
  });

  it("stays running after a recoverable error", () => {
    const state = applySseEvent(replay(scripted.slice(0, 1)), {
      id: "23",
      event: "error",
      data: {
        run_id: runId,
        timestamp: at,
        agent: "brief",
        message: "Retrying the model call",
        recoverable: true,
      },
    });
    expect(state.status).toBe("running");
    expect(state.agents.brief.status).toBe("failed");
  });
});
