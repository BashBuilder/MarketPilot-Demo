import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { HandoffRecord } from "@/lib/sse/run-state";
import { HandoffNote } from "../HandoffNote";

const handoff: HandoffRecord = {
  id: "2",
  from: "brief",
  to: "research",
  timestamp: "2026-11-05T09:00:01.000Z",
};

describe("HandoffNote", () => {
  it("announces the handoff from one agent to the next", () => {
    render(<HandoffNote handoff={handoff} />);

    expect(screen.getByText("handed off to")).toBeInTheDocument();
    expect(screen.getByText("Brief").parentElement).toHaveTextContent(
      "Brief handed off to Research",
    );
  });

  it("exposes the handoff ids and a machine-readable timestamp", () => {
    const { container } = render(<HandoffNote handoff={handoff} />);

    expect(container.firstElementChild).toHaveAttribute(
      "data-agent-from",
      "brief",
    );
    expect(container.firstElementChild).toHaveAttribute(
      "data-agent-to",
      "research",
    );
    expect(screen.getByText("09:00:01 UTC")).toHaveAttribute(
      "datetime",
      "2026-11-05T09:00:01.000Z",
    );
  });
});
