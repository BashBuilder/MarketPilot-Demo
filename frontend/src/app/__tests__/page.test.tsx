import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import LandingPage from "../page";

describe("LandingPage", () => {
  it("introduces the product with a single top-level heading", () => {
    render(<LandingPage />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Campaigns, composed by a team of agents.",
      }),
    ).toBeInTheDocument();
  });

  it("routes visitors to the campaign workspace", () => {
    render(<LandingPage />);

    expect(screen.getByRole("link", { name: "Open campaigns" })).toHaveAttribute(
      "href",
      "/campaigns",
    );
    expect(
      screen.getByRole("link", { name: "Browse campaigns" }),
    ).toHaveAttribute("href", "/campaigns");
  });

  it("offers to start a campaign from either call to action", () => {
    render(<LandingPage />);

    const links = screen.getAllByRole("link", { name: "Start a campaign" });
    expect(links).toHaveLength(2);
    for (const link of links) {
      expect(link).toHaveAttribute("href", "/campaigns/new");
    }
  });

  it("previews the agent pipeline in order", () => {
    render(<LandingPage />);

    const pipeline = screen.getByRole("list", { name: "Pipeline steps" });
    const items = within(pipeline).getAllByRole("listitem");

    expect(items).toHaveLength(8);
    [
      "Brief",
      "Research",
      "Copywriter",
      "Creative Director",
      "Designer",
      "Compliance",
      "Reviewer",
      "You",
    ].forEach((name, index) => {
      expect(within(items[index]).getByText(name)).toBeInTheDocument();
    });
  });
});
