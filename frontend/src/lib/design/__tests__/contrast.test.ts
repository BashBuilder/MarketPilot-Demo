import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  contrastRatio,
  parseCssBlockTokens,
  parseOklch,
  resolveToken,
  tokenContrast,
} from "../contrast";

const css = readFileSync(resolve(process.cwd(), "src/app/globals.css"), "utf8");

const lightTokens = parseCssBlockTokens(css, ".light");
const darkTokens = parseCssBlockTokens(css, ".dark");
const themeTokens = parseCssBlockTokens(css, "@theme");

const textPairs = [
  ["foreground", "background"],
  ["foreground", "card"],
  ["card-foreground", "card"],
  ["popover-foreground", "popover"],
  ["muted-foreground", "background"],
  ["muted-foreground", "card"],
  ["muted-foreground", "muted"],
  ["secondary-foreground", "secondary"],
  ["primary-foreground", "primary"],
  ["brand-foreground", "brand"],
  ["accent-foreground", "accent"],
  ["destructive", "background"],
  ["destructive", "card"],
  ["sidebar-foreground", "sidebar"],
  ["sidebar-accent-foreground", "sidebar-accent"],
  ["sidebar-primary-foreground", "sidebar-primary"],
] as const;

const nonTextPairs = [
  ["ring", "background"],
  ["input", "background"],
  ["input", "card"],
  ["sidebar-ring", "sidebar"],
] as const;

describe.each([
  ["light", lightTokens],
  ["dark", darkTokens],
] as const)("%s theme", (_name, tokens) => {
  it.each(textPairs)(
    "%s on %s meets WCAG AA for normal text",
    (foreground, background) => {
      expect(tokenContrast(tokens, foreground, background)).toBeGreaterThanOrEqual(
        4.5,
      );
    },
  );

  it.each(nonTextPairs)(
    "%s on %s meets the 3:1 UI contrast threshold",
    (foreground, background) => {
      expect(tokenContrast(tokens, foreground, background)).toBeGreaterThanOrEqual(
        3,
      );
    },
  );
});

describe("semantic tokens", () => {
  it("defines the same colour tokens in both themes", () => {
    const lightColourTokens = Object.keys(lightTokens).filter(
      (name) => name !== "--radius",
    );
    const darkColourTokens = Object.keys(darkTokens).filter(
      (name) => name !== "--radius",
    );

    expect(darkColourTokens.sort()).toEqual(lightColourTokens.sort());
  });

  it("keeps the accent as the only saturated brand colour", () => {
    expect(resolveToken(lightTokens, "primary")).toBe(
      resolveToken(lightTokens, "brand"),
    );
    expect(resolveToken(lightTokens, "ring")).toBe(
      resolveToken(lightTokens, "brand"),
    );
    expect(resolveToken(darkTokens, "primary")).toBe(
      resolveToken(darkTokens, "brand"),
    );
  });
});

describe("type scale", () => {
  const steps = [
    "--text-2xs",
    "--text-xs",
    "--text-sm",
    "--text-base",
    "--text-lg",
    "--text-xl",
    "--text-2xl",
    "--text-3xl",
    "--text-4xl",
    "--text-5xl",
    "--text-6xl",
    "--text-7xl",
  ];

  it("increases monotonically", () => {
    const sizes = steps.map((name) => Number.parseFloat(themeTokens[name]));

    for (let index = 1; index < sizes.length; index += 1) {
      expect(sizes[index]).toBeGreaterThan(sizes[index - 1]);
    }
  });

  it("defines a line height for every named step", () => {
    for (const name of steps) {
      expect(themeTokens[`${name}--line-height`]).toBeDefined();
    }
    expect(themeTokens["--text-display--line-height"]).toBeDefined();
  });
});

describe("spacing scale", () => {
  const steps = [
    "--spacing-3xs",
    "--spacing-2xs",
    "--spacing-xs",
    "--spacing-sm",
    "--spacing-md",
    "--spacing-lg",
    "--spacing-xl",
    "--spacing-2xl",
    "--spacing-3xl",
    "--spacing-4xl",
  ];

  it("uses a 4px base grid", () => {
    expect(themeTokens["--spacing"]).toBe("0.25rem");
  });

  it("increases monotonically", () => {
    const sizes = steps.map((name) => Number.parseFloat(themeTokens[name]));

    for (let index = 1; index < sizes.length; index += 1) {
      expect(sizes[index]).toBeGreaterThan(sizes[index - 1]);
    }
  });
});

describe("contrast helpers", () => {
  it("returns 21:1 for black on white", () => {
    expect(
      contrastRatio(parseOklch("oklch(1 0 0)"), parseOklch("oklch(0 0 0)")),
    ).toBeCloseTo(21, 5);
  });

  it("rejects malformed colour values", () => {
    expect(() => parseOklch("#fff")).toThrow("Unsupported colour value");
  });

  it("rejects circular token references", () => {
    expect(() =>
      resolveToken({ "--a": "var(--b)", "--b": "var(--a)" }, "--a"),
    ).toThrow("Circular token reference");
  });
});
