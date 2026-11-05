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

    const sources = screen.getByRole("heading", { level: 3, name: "Sources" });
    expect(sources).toBeInTheDocument();

    const links = screen.getAllByRole("link", { name: /opens in a new tab/ });
    expect(links).toHaveLength(research.sources.length);

    research.sources.forEach((source, index) => {
      const link = links[index];
      if (!link) throw new Error(`Missing source link for ${source.title}`);

      expect(link).toHaveAttribute("href", source.url);
      expect(link).toHaveAttribute("target", "_blank");
      expect(link).toHaveAttribute("rel", "noopener noreferrer");
      expect(link).toHaveTextContent(source.title);
    });
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
    const sourceTitle = "<strong>Research source</strong>";

    render(
      <ResearchCard
        research={{
          ...haircarePackage.research,
          segments: [{ ...haircarePackage.research.segments[0], name }],
          sources: [{ title: sourceTitle, url: "https://example.com/source" }],
        }}
      />,
    );

    expect(screen.getByText(name)).toBeInTheDocument();
    expect(screen.getByText(sourceTitle)).toBeInTheDocument();
    expect(document.querySelector("em")).toBeNull();
    expect(document.querySelector("strong")).toBeNull();
  });
});
