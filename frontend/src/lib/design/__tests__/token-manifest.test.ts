import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { parseCssBlockTokens } from "../contrast";
import {
  colorTokenGroups,
  fontTokens,
  radiusScale,
  spacingScale,
  trackingScale,
  typeScale,
} from "../token-manifest";

const css = readFileSync(resolve(process.cwd(), "src/app/globals.css"), "utf8");

const lightTokens = parseCssBlockTokens(css, ".light");
const themeTokens = parseCssBlockTokens(css, "@theme");
const inlineThemeTokens = parseCssBlockTokens(css, "@theme inline");

describe("token manifest", () => {
  it("covers every semantic colour token", () => {
    const manifest = colorTokenGroups
      .flatMap((group) => group.tokens)
      .sort();
    const declared = Object.keys(lightTokens)
      .filter((token) => token !== "--radius")
      .sort();

    expect(manifest).toEqual(declared);
  });

  it("covers every type, spacing, tracking, and font token", () => {
    expect(typeScale.map((step) => step.token).sort()).toEqual(
      Object.keys(themeTokens)
        .filter(
          (token) =>
            token.startsWith("--text-") &&
            !token.endsWith("--line-height") &&
            !token.endsWith("--letter-spacing"),
        )
        .sort(),
    );

    expect(spacingScale.map((step) => step.token).sort()).toEqual(
      Object.keys(themeTokens)
        .filter((token) => token.startsWith("--spacing"))
        .sort(),
    );

    expect(trackingScale.map((step) => step.token).sort()).toEqual(
      Object.keys(themeTokens)
        .filter((token) => token.startsWith("--tracking-"))
        .sort(),
    );

    expect(fontTokens.map((font) => font.token).sort()).toEqual(
      Object.keys(themeTokens)
        .filter((token) => token.startsWith("--font-"))
        .sort(),
    );
  });

  it("covers every radius token", () => {
    const manifest = radiusScale.map((step) => step.token).sort();
    const declared = [
      ...Object.keys(lightTokens),
      ...Object.keys(inlineThemeTokens),
    ]
      .filter((token) => token === "--radius" || token.startsWith("--radius-"))
      .sort();

    expect(manifest).toEqual(declared);
  });
});
