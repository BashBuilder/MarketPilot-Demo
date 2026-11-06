import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApprovalPanel, type ApprovalPanelProps } from "../ApprovalPanel";

function setup(overrides: Partial<ApprovalPanelProps> = {}) {
  const onApprove = vi.fn();
  const onRevise = vi.fn();
  const user = userEvent.setup();
  const props: ApprovalPanelProps = {
    version: 3,
    onApprove,
    onRevise,
    isPending: false,
    error: null,
    ...overrides,
  };
  const view = render(<ApprovalPanel {...props} />);
  return {
    user,
    onApprove,
    onRevise,
    rerender: (next: Partial<ApprovalPanelProps>) =>
      view.rerender(<ApprovalPanel {...props} {...next} />),
  };
}

function dialog() {
  return screen.getByRole("dialog");
}

describe("ApprovalPanel", () => {
  it("requires an explicit confirm before approving", async () => {
    const { user, onApprove } = setup();

    await user.click(screen.getByRole("button", { name: "Approve" }));

    expect(dialog()).toBeInTheDocument();
    expect(onApprove).not.toHaveBeenCalled();

    await user.type(
      within(dialog()).getByLabelText("Comment (optional)"),
      "  Looks good  ",
    );
    await user.click(
      within(dialog()).getByRole("button", { name: "Approve version 3" }),
    );

    expect(onApprove).toHaveBeenCalledTimes(1);
    expect(onApprove).toHaveBeenCalledWith("Looks good");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("does not approve when the dialog is cancelled", async () => {
    const { user, onApprove } = setup();

    await user.click(screen.getByRole("button", { name: "Approve" }));
    await user.click(within(dialog()).getByRole("button", { name: "Cancel" }));

    expect(onApprove).not.toHaveBeenCalled();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("blocks a revision without a non-empty comment", async () => {
    const { user, onRevise } = setup();

    await user.click(screen.getByRole("button", { name: "Request revision" }));
    const confirm = within(dialog()).getByRole("button", {
      name: "Request revision",
    });

    await user.click(confirm);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Describe what should change",
    );

    await user.type(
      within(dialog()).getByLabelText("What should change?"),
      "   ",
    );
    await user.click(confirm);

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Describe what should change",
    );
    expect(onRevise).not.toHaveBeenCalled();
  });

  it("submits a trimmed comment and the selected target agent", async () => {
    const { user, onRevise } = setup();

    await user.click(screen.getByRole("button", { name: "Request revision" }));
    await user.type(
      within(dialog()).getByLabelText("What should change?"),
      "  Fix the headline claim  ",
    );
    await user.selectOptions(
      within(dialog()).getByLabelText("Target agent (optional)"),
      "Copywriter",
    );
    await user.click(
      within(dialog()).getByRole("button", { name: "Request revision" }),
    );

    expect(onRevise).toHaveBeenCalledWith(
      "Fix the headline claim",
      "copywriter",
    );
  });

  it("disables every control while a submission is pending", async () => {
    const { user, rerender } = setup();

    await user.click(screen.getByRole("button", { name: "Approve" }));
    rerender({ isPending: true });

    expect(within(dialog()).getByLabelText("Comment (optional)")).toBeDisabled();
    expect(
      within(dialog()).getByRole("button", { name: "Approve version 3" }),
    ).toBeDisabled();
    expect(
      within(dialog()).getByRole("button", { name: "Cancel" }),
    ).toBeDisabled();
  });

  it("disables the panel actions while pending", () => {
    setup({ isPending: true });

    expect(
      screen.getByRole("button", { name: "Submitting…" }),
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Request revision" }),
    ).toBeDisabled();
  });

  it("prevents a double submit", async () => {
    const { user, onApprove } = setup();

    await user.click(screen.getByRole("button", { name: "Approve" }));
    const confirm = within(dialog()).getByRole("button", {
      name: "Approve version 3",
    });

    fireEvent.click(confirm);
    fireEvent.click(confirm);

    expect(onApprove).toHaveBeenCalledTimes(1);
  });

  it("shows a submission error with the error state", () => {
    setup({ error: "The run is no longer awaiting approval." });

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Could not submit your review");
    expect(alert).toHaveTextContent("The run is no longer awaiting approval.");
  });
});
