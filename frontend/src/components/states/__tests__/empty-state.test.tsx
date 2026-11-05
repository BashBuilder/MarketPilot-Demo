import { render, screen } from "@testing-library/react";
import { Inbox } from "lucide-react";
import { describe, expect, it } from "vitest";
import { EmptyState } from "../empty-state";

describe("EmptyState", () => {
  it("renders the title, description, icon, and action", () => {
    render(
      <EmptyState
        title="No campaigns yet"
        description="Start with a brief and let the agents build the first package."
        icon={<Inbox data-testid="empty-icon" />}
        action={<button type="button">Create a campaign</button>}
      />,
    );

    expect(
      screen.getByRole("heading", { level: 2, name: "No campaigns yet" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Start with a brief and let the agents build the first package.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByTestId("empty-icon")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Create a campaign" }),
    ).toBeInTheDocument();
  });

  it("supports a lower heading level for nested layouts", () => {
    render(<EmptyState headingLevel="h3" title="No versions" />);

    expect(
      screen.getByRole("heading", { level: 3, name: "No versions" }),
    ).toBeInTheDocument();
  });
});
