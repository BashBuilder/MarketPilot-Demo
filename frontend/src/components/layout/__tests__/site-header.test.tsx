import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const pathname = vi.hoisted(() => ({ current: "/" }));

vi.mock("next/navigation", () => ({
  usePathname: () => pathname.current,
}));

import { SiteHeader } from "../site-header";

beforeEach(() => {
  pathname.current = "/";
  window.localStorage.clear();
  document.documentElement.classList.remove("dark");
  document.documentElement.style.colorScheme = "";
});

describe("SiteHeader", () => {
  it("renders the brand, primary navigation, and theme switch", () => {
    render(<SiteHeader />);

    expect(
      screen.getByRole("link", { name: "MarketPilot home" }),
    ).toHaveAttribute("href", "/");

    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(within(nav).getByRole("link", { name: "Campaigns" })).toHaveAttribute(
      "href",
      "/",
    );
    expect(
      within(nav).getByRole("link", { name: "New campaign" }),
    ).toHaveAttribute("href", "/campaigns/new");

    expect(
      screen.getByRole("switch", { name: "Dark theme" }),
    ).toBeInTheDocument();
  });

  it("marks the current route with aria-current", () => {
    render(<SiteHeader />);

    expect(screen.getByRole("link", { name: "Campaigns" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(
      screen.getByRole("link", { name: "New campaign" }),
    ).not.toHaveAttribute("aria-current");
  });

  it("marks the new campaign route when active", () => {
    pathname.current = "/campaigns/new";

    render(<SiteHeader />);

    expect(
      screen.getByRole("link", { name: "New campaign" }),
    ).toHaveAttribute("aria-current", "page");
    expect(
      screen.getByRole("link", { name: "Campaigns" }),
    ).not.toHaveAttribute("aria-current");
  });

  it("keeps every control reachable in keyboard order", async () => {
    const user = userEvent.setup();
    render(<SiteHeader />);

    await user.tab();
    expect(
      screen.getByRole("link", { name: "MarketPilot home" }),
    ).toHaveFocus();

    await user.tab();
    expect(screen.getByRole("link", { name: "Campaigns" })).toHaveFocus();

    await user.tab();
    expect(screen.getByRole("link", { name: "New campaign" })).toHaveFocus();

    await user.tab();
    expect(screen.getByRole("switch", { name: "Dark theme" })).toHaveFocus();
  });
});
