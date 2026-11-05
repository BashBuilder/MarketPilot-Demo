import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ErrorState } from "../error-state";

describe("ErrorState", () => {
  it("announces the error and calls retry", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();

    render(
      <ErrorState
        title="We couldn't load this campaign"
        description="The package may still be generating."
        onRetry={onRetry}
      />,
    );

    const alert = screen.getByRole("alert");
    expect(
      screen.getByRole("heading", {
        level: 2,
        name: "We couldn't load this campaign",
      }),
    ).toBeInTheDocument();
    expect(alert).toHaveTextContent("The package may still be generating.");

    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("uses a default title and omits retry when no handler is given", () => {
    render(<ErrorState description="Check the connection and reload." />);

    expect(screen.getByRole("alert")).toHaveTextContent("Something went wrong");
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("supports a custom retry label", () => {
    render(<ErrorState onRetry={() => undefined} retryLabel="Reload run" />);

    expect(
      screen.getByRole("button", { name: "Reload run" }),
    ).toBeInTheDocument();
  });
});
