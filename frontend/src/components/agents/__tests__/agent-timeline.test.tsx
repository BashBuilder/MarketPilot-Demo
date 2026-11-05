import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { AgentName } from "@/lib/schemas";
import type { AgentRunState, AgentStatus } from "@/lib/sse/run-state";
import { AGENT_ORDER, createRunState } from "@/lib/sse/run-state";
import { AgentTimeline } from "../AgentTimeline";

function agentsWith(
  patch: Partial<Record<AgentName, Partial<AgentRunState>>>,
): Record<AgentName, AgentRunState> {
  const { agents } = createRunState("run-test");

  for (const agent of AGENT_ORDER) {
    const agentPatch = patch[agent];
    if (agentPatch) {
      agents[agent] = { ...agents[agent], ...agentPatch };
    }
  }

  return agents;
}

function briefItem(): HTMLElement {
  const items = screen.getAllByRole("listitem");
  const brief = items[0];
  if (!brief) {
    throw new Error("Brief row is missing");
  }
  return brief;
}

describe("AgentTimeline", () => {
  it("renders the eight agents in pipeline order with descriptions", () => {
    render(<AgentTimeline agents={agentsWith({})} />);

    const list = screen.getByRole("list", { name: "Agent pipeline" });
    const items = within(list).getAllByRole("listitem");

    expect(items.map((item) => item.getAttribute("data-agent"))).toEqual([
      ...AGENT_ORDER,
    ]);
    expect(within(list).getByText("Brief")).toBeInTheDocument();
    expect(
      within(list).getByText("Turns the campaign idea into a structured brief."),
    ).toBeInTheDocument();
    expect(within(list).getByText("Supervisor")).toBeInTheDocument();
    expect(
      within(list).getByText("Routes the run and escalates when needed."),
    ).toBeInTheDocument();
  });

  it("marks the list as a polite live region", () => {
    render(<AgentTimeline agents={agentsWith({})} />);

    expect(
      screen.getByRole("list", { name: "Agent pipeline" }),
    ).toHaveAttribute("aria-live", "polite");
  });

  it.each<[AgentStatus, string]>([
    ["waiting", "Waiting"],
    ["running", "Running"],
    ["failed", "Failed"],
    ["done", "Done"],
  ])("renders the %s status", (status, label) => {
    render(<AgentTimeline agents={agentsWith({ brief: { status } })} />);

    expect(within(briefItem()).getByText(label)).toBeInTheDocument();
  });

  it("shows the attempt count while retrying", () => {
    render(
      <AgentTimeline
        agents={agentsWith({
          brief: { status: "retrying", attempt: 2, maxAttempts: 3 },
        })}
      />,
    );

    expect(
      within(briefItem()).getByText("Retrying · attempt 2 of 3"),
    ).toBeInTheDocument();
  });

  it("shows no attempt count for other statuses", () => {
    render(<AgentTimeline agents={agentsWith({ brief: { status: "running" } })} />);

    expect(within(briefItem()).queryByText(/attempt/i)).not.toBeInTheDocument();
  });

  it("animates status changes with reduced-motion-safe classes", () => {
    const { rerender } = render(
      <AgentTimeline agents={agentsWith({ brief: { status: "waiting" } })} />,
    );

    rerender(
      <AgentTimeline agents={agentsWith({ brief: { status: "running" } })} />,
    );

    const row = briefItem();
    const badge = within(row).getByText("Running");
    expect(badge).toHaveClass("motion-safe:animate-in");
    expect(badge).toHaveClass("motion-safe:fade-in-0");
    expect(badge).not.toHaveClass("animate-in");
    expect(row).toHaveClass("motion-safe:transition-colors");
    expect(row).not.toHaveClass("transition-colors");
    expect(row).toHaveAttribute("data-status", "running");
  });
});
