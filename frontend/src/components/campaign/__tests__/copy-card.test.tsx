import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { CopyVariant } from "@/lib/schemas";
import { haircarePackage } from "@/mocks/fixtures";
import { CopyCard } from "../CopyCard";

describe("CopyCard", () => {
  it("renders every variant from the package fixture grouped by channel", () => {
    const copy = haircarePackage.copy.variants;

    render(<CopyCard copy={copy} />);

    expect(
      screen.getByRole("heading", { level: 2, name: "Copy variants" }),
    ).toBeInTheDocument();

    const channels = new Set(copy.map((variant) => variant.channel));
    for (const channel of channels) {
      expect(
        screen.getByRole("heading", { level: 3, name: channel }),
      ).toBeInTheDocument();
    }

    for (const variant of copy) {
      expect(screen.getByText(variant.headline)).toBeInTheDocument();
      expect(screen.getByText(variant.description)).toBeInTheDocument();
      expect(
        screen.getByText(`CTA: ${variant.cta}`),
      ).toBeInTheDocument();
    }
  });

  it("groups multiple variants under the same channel heading", () => {
    const variants: CopyVariant[] = [
      {
        channel: "email",
        headline: "First email hook",
        description: "First email body",
        cta: "Shop now",
      },
      {
        channel: "email",
        headline: "Second email hook",
        description: "Second email body",
        cta: "Shop now",
      },
    ];

    render(<CopyCard copy={variants} />);

    expect(
      screen.getAllByRole("heading", { level: 3, name: "email" }),
    ).toHaveLength(1);
    expect(screen.getByText("First email hook")).toBeInTheDocument();
    expect(screen.getByText("Second email hook")).toBeInTheDocument();
  });

  it("shows an empty state when copy is missing or empty", () => {
    const { rerender } = render(<CopyCard copy={undefined} />);

    expect(
      screen.getByRole("heading", { name: "No copy yet" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Copywriter agent/)).toBeInTheDocument();

    rerender(<CopyCard copy={[]} />);

    expect(
      screen.getByRole("heading", { name: "No copy yet" }),
    ).toBeInTheDocument();
  });

  it("renders backend text as plain text, never as HTML", () => {
    const headline = "<script>alert('copy')</script>";

    render(
      <CopyCard
        copy={[{ ...haircarePackage.copy.variants[0], headline }]}
      />,
    );

    expect(screen.getByText(headline)).toBeInTheDocument();
    expect(document.querySelector("script")).toBeNull();
  });
});
