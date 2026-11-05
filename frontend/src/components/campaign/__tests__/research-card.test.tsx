import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { haircarePackage } from "@/mocks/fixtures";
import { ResearchCard } from "../ResearchCard";

describe("ResearchCard", () => {
  it("renders the research fields from the package fixture", () => {
    const { research } = haircarePackage;

    render(<ResearchCard research={research} />);

    expect(
      screen.getByRole("heading", { level: 2, name: "Audience research" }),
    ).toBeInTheDocument();

    for (const segment of research.segments) {
      expect(screen.getByText(segment.name)).toBeInTheDocument();
      expect(screen.getByText(segment.description)).toBeInTheDocument();
    }
    for (const painPoint of research.pain_points) {
      expect(screen.getByText(painPoint)).toBeInTheDocument();
    }
    for (const angle of research.messaging_angles) {
      expect(screen.getByText(angle)).toBeInTheDocument();
    }
  });

  it("shows an empty state when the research is missing", () => {
    render(<ResearchCard research={undefined} />);

    expect(
      screen.getByRole("heading", { name: "No research yet" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Research agent/)).toBeInTheDocument();
  });

  it("renders backend text as plain text, never as HTML", () => {
    const name = "<em>Busy professionals</em>";

    render(
      <ResearchCard
        research={{
          ...haircarePackage.research,
          segments: [{ ...haircarePackage.research.segments[0], name }],
        }}
      />,
    );

    expect(screen.getByText(name)).toBeInTheDocument();
    expect(document.querySelector("em")).toBeNull();
  });
});
