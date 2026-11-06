import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const pathname = vi.hoisted(() => ({ current: "/" }));

vi.mock("next/navigation", () => ({
  usePathname: () => pathname.current,
}));

import { SiteHeader } from "../site-header";

beforeEach(() => {
  pathname.current = "/campaigns";
  window.localStorage.clear();
  document.documentElement.classList.remove("dark");
  document.documentElement.style.colorScheme = "";
});

describe("SiteHeader", () => {
  it("renders the brand, primary navigation, and theme switch", () => {
    render(<SiteHeader />);

    expect(
      screen.getByRole("link", { name: "M MarketPilot home" }),
    ).toHaveAttribute("href", "/");

    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(within(nav).getByRole("link", { name: "Campaigns" })).toHaveAttribute(
      "href",
      "/campaigns",
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

  it("leaves navigation unselected on the landing page", () => {
    pathname.current = "/";

    render(<SiteHeader />);

    expect(
      screen.getByRole("link", { name: "Campaigns" }),
    ).not.toHaveAttribute("aria-current");
    expect(
      screen.getByRole("link", { name: "New campaign" }),
    ).not.toHaveAttribute("aria-current");
  });

  it("keeps the campaigns item selected on a campaign detail route", () => {
    pathname.current = "/campaigns/7c9e6679-7425-40de-944b-e07fc1f90ae7";

    render(<SiteHeader />);

    expect(
      screen.getByRole("link", { name: "Campaigns" }),
    ).toHaveAttribute("aria-current", "page");
  });

  it("keeps every control reachable in keyboard order", async () => {
    const user = userEvent.setup();
    render(<SiteHeader />);

    await user.tab();
    expect(
      screen.getByRole("link", { name: "M MarketPilot home" }),
    ).toHaveFocus();

    await user.tab();
    expect(screen.getByRole("link", { name: "Campaigns" })).toHaveFocus();

    await user.tab();
    expect(screen.getByRole("link", { name: "New campaign" })).toHaveFocus();

    await user.tab();
    expect(screen.getByRole("switch", { name: "Dark theme" })).toHaveFocus();
  });
});
