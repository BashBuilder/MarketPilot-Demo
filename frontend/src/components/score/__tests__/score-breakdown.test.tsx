import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { scoreDimensionKeys } from "@/lib/schemas";
import { haircarePackage } from "@/mocks/fixtures";
import { ScoreBreakdown } from "../ScoreBreakdown";

const { score } = haircarePackage;

describe("ScoreBreakdown", () => {
  it("renders the weighted total, dimension scores and justifications", () => {
    render(<ScoreBreakdown score={score} />);

    expect(
      screen.getByRole("heading", { level: 2, name: "Creative score" }),
    ).toBeInTheDocument();
    expect(screen.getByText(String(score.total))).toBeInTheDocument();

    for (const key of scoreDimensionKeys) {
      const row = document.querySelector<HTMLElement>(
        `[data-dimension="${key}"]`,
      );
      if (!row) throw new Error(`Missing score row for ${key}`);

      expect(
        within(row).getByText(score[key].justification),
      ).toBeInTheDocument();
      expect(
        within(row).getByText(String(score[key].score)),
      ).toBeInTheDocument();
    }
  });

  it("gives the chart a text alternative", () => {
    render(<ScoreBreakdown score={score} />);

    const chart = screen.getByRole("img", { name: /Score breakdown/ });
    const label = chart.getAttribute("aria-label");

    expect(label).toContain("Brief alignment 9 out of 10");
    expect(label).toContain("Weighted total 86 out of 100");
  });

  it("shows an empty state when the score is missing", () => {
    render(<ScoreBreakdown score={undefined} />);

    expect(
      screen.getByRole("heading", { name: "No score yet" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Reviewer agent/)).toBeInTheDocument();
  });

  it("renders justification text as plain text, never as HTML", () => {
    const justification = "<em>Sharper hook needed</em>";

    render(
      <ScoreBreakdown
        score={{
          ...score,
          copy_quality: { ...score.copy_quality, justification },
        }}
      />,
    );

    expect(screen.getByText(justification)).toBeInTheDocument();
    expect(document.querySelector("em")).toBeNull();
  });
});
