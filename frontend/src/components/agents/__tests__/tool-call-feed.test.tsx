import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { ToolCallRecord } from "@/lib/sse/run-state";
import { ToolCallFeed } from "../ToolCallFeed";

const calls: ToolCallRecord[] = [
  {
    id: "6",
    agent: "copywriter",
    tool: "policy_lookup",
    durationMs: 120,
    status: "success",
    timestamp: "2026-11-05T09:00:05.000Z",
  },
  {
    id: "14",
    agent: "designer",
    tool: "generate_image",
    durationMs: 4200,
    status: "error",
    timestamp: "2026-11-05T09:00:18.000Z",
  },
];

function detailsFor(tool: string): HTMLDetailsElement {
  const details = screen.getByText(tool).closest("details");
  if (!(details instanceof HTMLDetailsElement)) {
    throw new Error(`Missing details row for ${tool}`);
  }
  return details;
}

function summaryFor(tool: string): HTMLElement {
  const summary = screen.getByText(tool).closest("summary");
  if (!(summary instanceof HTMLElement)) {
    throw new Error(`Missing summary row for ${tool}`);
  }
  return summary;
}

describe("ToolCallFeed", () => {
  it("renders a polite feed with compact tool rows", () => {
    render(<ToolCallFeed calls={calls} />);

    const feed = screen.getByRole("region", { name: "Tool calls" });
    expect(feed).toHaveAttribute("aria-live", "polite");

    expect(screen.getByText("policy_lookup")).toBeInTheDocument();
    expect(
      within(summaryFor("policy_lookup")).getByText("120 ms"),
    ).toBeInTheDocument();
    expect(
      within(summaryFor("generate_image")).getByText("4.2 s"),
    ).toBeInTheDocument();
    expect(
      within(summaryFor("policy_lookup")).getByText("Success"),
    ).toBeInTheDocument();
    expect(
      within(summaryFor("generate_image")).getByText("Error"),
    ).toBeInTheDocument();
  });

  it("shows a guardrail-denied tool call", () => {
    render(
      <ToolCallFeed
        calls={[{ ...calls[0], id: "denied", status: "denied" }]}
      />,
    );

    expect(
      within(summaryFor("policy_lookup")).getByText("Denied"),
    ).toBeInTheDocument();
  });

  it("expands a row to show agent, status and recorded time", async () => {
    const user = userEvent.setup();
    render(<ToolCallFeed calls={calls} />);

    const details = detailsFor("policy_lookup");
    expect(details.open).toBe(false);

    await user.click(screen.getByText("policy_lookup"));

    expect(details.open).toBe(true);
    expect(within(details).getByText("Copywriter")).toBeInTheDocument();
    expect(within(details).getByText("Recorded")).toBeInTheDocument();
    expect(within(details).getByText("09:00:05 UTC")).toHaveAttribute(
      "datetime",
      "2026-11-05T09:00:05.000Z",
    );
  });

  it("keeps a failed tool call visible in the compact row", () => {
    render(<ToolCallFeed calls={[calls[1]]} />);

    expect(
      within(summaryFor("generate_image")).getByText("Error"),
    ).toHaveClass("text-destructive");
    expect(screen.getByText("generate_image")).toBeInTheDocument();
  });

  it("shows an empty state before the first tool call", () => {
    render(<ToolCallFeed calls={[]} />);

    expect(screen.getByText("No tool calls yet.")).toBeInTheDocument();
  });
});
