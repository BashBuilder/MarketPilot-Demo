import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { haircarePackage } from "@/mocks/fixtures";
import { BriefCard } from "../BriefCard";

describe("BriefCard", () => {
  it("renders the brief fields from the package fixture", () => {
    const { brief } = haircarePackage;

    render(<BriefCard brief={brief} />);

    expect(
      screen.getByRole("heading", { level: 2, name: "Campaign brief" }),
    ).toBeInTheDocument();
    expect(screen.getByText(brief.product)).toBeInTheDocument();
    expect(screen.getByText(brief.goal)).toBeInTheDocument();
    expect(screen.getByText(brief.audience)).toBeInTheDocument();
    expect(screen.getByText(brief.tone)).toBeInTheDocument();

    for (const channel of brief.channels) {
      expect(screen.getByText(channel)).toBeInTheDocument();
    }
    for (const constraint of brief.constraints) {
      expect(screen.getByText(constraint)).toBeInTheDocument();
    }
  });

  it("shows an empty state when the brief is missing", () => {
    render(<BriefCard brief={undefined} />);

    expect(
      screen.getByRole("heading", { name: "No brief yet" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Brief agent/)).toBeInTheDocument();
  });

  it("renders backend text as plain text, never as HTML", () => {
    const goal = "<strong>Launch the campaign</strong>";

    render(
      <BriefCard brief={{ ...haircarePackage.brief, goal }} />,
    );

    expect(screen.getByText(goal)).toBeInTheDocument();
    expect(document.querySelector("strong")).toBeNull();
  });
});
