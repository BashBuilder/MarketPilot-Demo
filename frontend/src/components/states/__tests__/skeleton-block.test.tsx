import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SkeletonBlock } from "../skeleton-block";

describe("SkeletonBlock", () => {
  it("is decorative and merges shape classes", () => {
    render(<SkeletonBlock data-testid="skeleton" className="h-4 w-1/2" />);

    const skeleton = screen.getByTestId("skeleton");
    expect(skeleton).toHaveAttribute("aria-hidden", "true");
    expect(skeleton).toHaveAttribute("data-slot", "skeleton");
    expect(skeleton).toHaveClass(
      "motion-safe:animate-pulse",
      "rounded-md",
      "bg-muted",
      "h-4",
      "w-1/2",
    );
  });
});
