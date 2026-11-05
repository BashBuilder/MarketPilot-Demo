import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SkipLink } from "../skip-link";

describe("SkipLink", () => {
  it("targets the main landmark and reveals itself on focus", () => {
    render(<SkipLink />);

    const link = screen.getByRole("link", { name: "Skip to content" });
    expect(link).toHaveAttribute("href", "#main-content");
    expect(link).toHaveClass("sr-only", "focus:not-sr-only");
    expect(link).toHaveClass("focus-visible:ring-2");
  });
});
