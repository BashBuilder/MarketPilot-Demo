import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { ThemeToggle } from "../theme-toggle";
import { THEME_STORAGE_KEY } from "@/lib/theme";

beforeEach(() => {
  window.localStorage.clear();
  document.documentElement.classList.remove("dark");
  document.documentElement.style.colorScheme = "";
});

describe("ThemeToggle", () => {
  it("switches to dark and persists the choice", async () => {
    const user = userEvent.setup();
    render(<ThemeToggle />);

    const toggle = screen.getByRole("switch", { name: "Dark theme" });
    expect(toggle).toHaveAttribute("aria-checked", "false");

    await user.click(toggle);

    expect(document.documentElement).toHaveClass("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(toggle).toHaveAttribute("aria-checked", "true");
  });

  it("switches back to light", async () => {
    const user = userEvent.setup();
    render(<ThemeToggle />);

    const toggle = screen.getByRole("switch", { name: "Dark theme" });
    await user.click(toggle);
    await user.click(toggle);

    expect(document.documentElement).not.toHaveClass("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
    expect(toggle).toHaveAttribute("aria-checked", "false");
  });

  it("reflects a theme applied before hydration", () => {
    document.documentElement.classList.add("dark");

    render(<ThemeToggle />);

    expect(screen.getByRole("switch", { name: "Dark theme" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });
});
