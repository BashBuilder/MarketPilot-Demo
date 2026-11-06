import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FailureNotice } from "../FailureNotice";

describe("FailureNotice", () => {
  it("shows a validation failure with its full reason", () => {
    render(
      <FailureNotice
        kind="validation_failed"
        agent="copywriter"
        reason="Email variant is missing a call to action."
        attempt={1}
        maxAttempts={3}
        timestamp="2026-11-05T09:00:06.000Z"
      />,
    );

    const notice = screen.getByRole("status");
    expect(notice).toHaveAttribute("data-kind", "validation_failed");
    expect(screen.getByText("Validation failed · Copywriter")).toBeVisible();
    expect(
      screen.getByText("Email variant is missing a call to action."),
    ).toBeVisible();
    expect(screen.getByText("Attempt 1 of 3")).toBeVisible();
    expect(screen.getByText("09:00:06 UTC")).toBeVisible();
  });

  it("shows a retry with the attempt count and reason", () => {
    render(
      <FailureNotice
        kind="retrying"
        agent="copywriter"
        reason="Retrying with the validation error attached."
        attempt={2}
        maxAttempts={3}
        timestamp="2026-11-05T09:00:07.000Z"
      />,
    );

    expect(
      screen.getByRole("status", {
        name: "Retrying Copywriter, Attempt 2 of 3",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Retrying Copywriter")).toBeVisible();
    expect(screen.getByText("Attempt 2 of 3")).toBeVisible();
    expect(
      screen.getByText("Retrying with the validation error attached."),
    ).toBeVisible();
  });

  it("keeps the attempt count visible when no reason is supplied", () => {
    render(
      <FailureNotice
        kind="retrying"
        agent="designer"
        attempt={1}
        maxAttempts={2}
      />,
    );

    expect(
      screen.getByRole("status", { name: "Retrying Designer, Attempt 1 of 2" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Attempt 1 of 2")).toBeVisible();
  });
});
