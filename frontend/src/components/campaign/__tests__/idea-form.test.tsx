import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { IDEA_MAX_LENGTH, IdeaForm } from "../IdeaForm";
import { EXAMPLE_PROMPTS } from "../example-prompts";

function setup(onSubmit = vi.fn(async () => {})) {
  const user = userEvent.setup();
  render(<IdeaForm onSubmit={onSubmit} />);
  return { user, onSubmit };
}

function counter() {
  return screen.getByText((_, element) => element?.id === "campaign-idea-count");
}

describe("IdeaForm", () => {
  it("renders a labelled textarea with a live character count", async () => {
    const { user } = setup();
    const textarea = screen.getByLabelText("Campaign idea");

    expect(textarea).toHaveAttribute("maxlength", String(IDEA_MAX_LENGTH));
    expect(counter()).toHaveTextContent(`0 / ${IDEA_MAX_LENGTH}`);

    await user.type(textarea, "Launch");
    expect(counter()).toHaveTextContent(`6 / ${IDEA_MAX_LENGTH}`);
  });

  it("blocks an empty idea and explains what is missing", async () => {
    const { user, onSubmit } = setup();

    await user.click(screen.getByRole("button", { name: "Start campaign" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Describe your campaign idea before starting.",
    );
    expect(screen.getByLabelText("Campaign idea")).toHaveFocus();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("treats whitespace-only input as empty", async () => {
    const { user, onSubmit } = setup();
    await user.type(screen.getByLabelText("Campaign idea"), "   ");

    await user.click(screen.getByRole("button", { name: "Start campaign" }));

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("rejects ideas beyond the length limit", async () => {
    const { user, onSubmit } = setup();
    fireEvent.change(screen.getByLabelText("Campaign idea"), {
      target: { value: "a".repeat(IDEA_MAX_LENGTH + 1) },
    });

    await user.click(screen.getByRole("button", { name: "Start campaign" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      `Keep your idea to ${IDEA_MAX_LENGTH} characters or fewer.`,
    );
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("fills the idea from an example prompt", async () => {
    const { user, onSubmit } = setup();
    const hairCare = EXAMPLE_PROMPTS[0];

    await user.click(screen.getByRole("button", { name: hairCare.label }));

    const textarea = screen.getByLabelText("Campaign idea");
    expect(hairCare.idea).toContain("25 to 40");
    expect(textarea).toHaveValue(hairCare.idea);
    expect(counter()).toHaveTextContent(
      `${hairCare.idea.length} / ${IDEA_MAX_LENGTH}`,
    );
    expect(textarea).toHaveFocus();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("disables the submit button while in flight and blocks a double submit", async () => {
    let finish: (() => void) | undefined;
    const onSubmit = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          finish = resolve;
        }),
    );
    const { user } = setup(onSubmit);
    await user.type(
      screen.getByLabelText("Campaign idea"),
      "Launch a travel mug",
    );

    await user.click(screen.getByRole("button", { name: "Start campaign" }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith("Launch a travel mug");
    const pending = screen.getByRole("button", {
      name: "Starting campaign…",
    });
    expect(pending).toBeDisabled();

    await user.click(pending);
    expect(onSubmit).toHaveBeenCalledTimes(1);

    await act(async () => finish?.());
    expect(
      screen.getByRole("button", { name: "Start campaign" }),
    ).toBeEnabled();
  });

  it("keeps the input and reports an error when the submit rejects", async () => {
    const onSubmit = vi.fn(async () => {
      throw new Error("Service unavailable");
    });
    const { user } = setup(onSubmit);
    await user.type(
      screen.getByLabelText("Campaign idea"),
      "Launch a travel mug",
    );

    await user.click(screen.getByRole("button", { name: "Start campaign" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Service unavailable",
    );
    expect(screen.getByLabelText("Campaign idea")).toHaveValue(
      "Launch a travel mug",
    );
    expect(
      screen.getByRole("button", { name: "Start campaign" }),
    ).toBeEnabled();
  });

  it("submits with Ctrl+Enter from the textarea", async () => {
    const { user, onSubmit } = setup();
    await user.type(
      screen.getByLabelText("Campaign idea"),
      "Launch a travel mug",
    );

    await user.keyboard("{Control>}{Enter}{/Control}");

    expect(onSubmit).toHaveBeenCalledWith("Launch a travel mug");
  });
});
