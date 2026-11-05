import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StyleGuide } from "../style-guide";
import {
  colorTokenGroups,
  fontTokens,
  radiusScale,
  spacingScale,
  trackingScale,
  typeScale,
} from "@/lib/design/token-manifest";

const tokenCategories = [
  {
    attribute: "data-color-token",
    tokens: colorTokenGroups.flatMap((group) => group.tokens),
  },
  {
    attribute: "data-type-token",
    tokens: typeScale.map((step) => step.token),
  },
  {
    attribute: "data-spacing-token",
    tokens: spacingScale.map((step) => step.token),
  },
  {
    attribute: "data-radius-token",
    tokens: radiusScale.map((step) => step.token),
  },
  {
    attribute: "data-tracking-token",
    tokens: trackingScale.map((step) => step.token),
  },
  {
    attribute: "data-font-token",
    tokens: fontTokens.map((font) => font.token),
  },
] as const;

describe("StyleGuide", () => {
  it("renders fixed light and dark previews", () => {
    render(<StyleGuide />);

    const previews = screen.getAllByTestId("theme-preview");
    expect(previews).toHaveLength(2);
    expect(previews[0]).toHaveClass("light");
    expect(previews[1]).toHaveClass("dark");
    expect(
      screen.getByRole("heading", { name: "Light theme" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Dark theme" }),
    ).toBeInTheDocument();
  });

  it("renders every token in both previews", () => {
    const { container } = render(<StyleGuide />);

    for (const category of tokenCategories) {
      for (const token of category.tokens) {
        expect(
          container.querySelectorAll(
            `[${category.attribute}="${token}"]`,
          ),
        ).toHaveLength(2);
      }
    }
  });

  it("renders every state in both previews", () => {
    render(<StyleGuide />);

    expect(screen.getAllByText("No campaigns yet")).toHaveLength(2);
    expect(screen.getAllByText("Loading campaign preview")).toHaveLength(2);
    expect(screen.getAllByRole("alert")).toHaveLength(2);
    expect(screen.getAllByRole("button", { name: "Try again" })).toHaveLength(
      2,
    );
  });
});
