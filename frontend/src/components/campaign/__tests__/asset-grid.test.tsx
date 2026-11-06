import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { resolveAssetUrl } from "@/lib/assets/asset-url";
import { haircarePackage } from "@/mocks/fixtures";
import { haircareDirection } from "@/mocks/fixtures/package-visuals";
import { AssetGrid } from "../AssetGrid";

const assets = haircarePackage.assets.assets;
const firstAlt = haircareDirection.image_prompts[0];

describe("AssetGrid", () => {
  it("renders assets with alt text taken from the creative direction", () => {
    render(<AssetGrid assets={assets} direction={haircareDirection} />);

    const image = screen.getByRole("img", { name: firstAlt });

    expect(image).toHaveAttribute("src", resolveAssetUrl(assets[0].uri));
    expect(
      screen.getByRole("heading", { level: 2, name: "Campaign assets" }),
    ).toBeInTheDocument();
  });

  it("reveals prompt, model and seed from the asset details toggle", async () => {
    const user = userEvent.setup();
    const { prompt, model, seed } = assets[0];

    render(<AssetGrid assets={assets} direction={haircareDirection} />);

    const summary = screen.getByText("Asset details");
    const details = summary.closest("details");

    if (!details) throw new Error("Asset details toggle was not rendered");
    expect(details).not.toHaveAttribute("open");
    expect(screen.getByText(prompt)).toBeInTheDocument();
    expect(screen.getByText(model)).toBeInTheDocument();
    expect(screen.getByText(String(seed))).toBeInTheDocument();

    await user.click(summary);

    expect(details).toHaveAttribute("open");
  });

  it("replaces a broken image with an accessible fallback", () => {
    render(<AssetGrid assets={assets} direction={haircareDirection} />);

    fireEvent.error(screen.getByRole("img", { name: firstAlt }));

    expect(screen.getByText("Preview unavailable")).toBeInTheDocument();
    expect(document.querySelector("img")).toBeNull();
    expect(screen.getByRole("img", { name: firstAlt })).toBeInTheDocument();
    expect(screen.getByText(firstAlt)).toBeInTheDocument();
  });

  it("shows an empty state when there are no assets", () => {
    const { rerender } = render(
      <AssetGrid assets={undefined} direction={haircareDirection} />,
    );

    expect(
      screen.getByRole("heading", { name: "No assets yet" }),
    ).toBeInTheDocument();

    rerender(<AssetGrid assets={[]} direction={haircareDirection} />);

    expect(
      screen.getByRole("heading", { name: "No assets yet" }),
    ).toBeInTheDocument();
  });

  it("renders backend text as plain text, never as HTML", () => {
    const prompt = '<img src="x" onerror="alert(1)">';

    render(
      <AssetGrid
        assets={[{ ...assets[0], prompt }]}
        direction={haircareDirection}
      />,
    );

    expect(screen.getByText(prompt)).toBeInTheDocument();
    expect(document.querySelectorAll("img")).toHaveLength(1);
  });
});
