export interface OklchColor {
  l: number;
  c: number;
  h: number;
  alpha: number;
}

const OKLCH_PATTERN =
  /^oklch\(\s*([+-]?\d*\.?\d+)(%?)\s+([+-]?\d*\.?\d+)\s+([+-]?\d*\.?\d+)(?:deg)?\s*(?:\/\s*([+-]?\d*\.?\d+)(%?)\s*)?\)$/i;

/**
 * Parses the subset of CSS Colour 4 oklch() used by the token layer.
 * Throws instead of guessing so a malformed token fails the contrast test.
 */
export function parseOklch(value: string): OklchColor {
  const match = OKLCH_PATTERN.exec(value.trim());
  if (match === null) {
    throw new Error(`Unsupported colour value: ${value}`);
  }

  const lightness = Number(match[1]) / (match[2] === "%" ? 100 : 1);
  const chroma = Number(match[3]);
  const hue = Number(match[4]);
  const alpha =
    match[5] === undefined
      ? 1
      : Number(match[5]) / (match[6] === "%" ? 100 : 1);

  return { l: lightness, c: chroma, h: hue, alpha };
}

function clampChannel(value: number): number {
  return Math.min(1, Math.max(0, value));
}

function gammaEncode(value: number): number {
  return value <= 0.0031308
    ? 12.92 * value
    : 1.055 * Math.pow(Math.max(value, 0), 1 / 2.4) - 0.055;
}

export function oklchToLinearSrgb(color: OklchColor): [
  number,
  number,
  number,
] {
  const hue = (color.h * Math.PI) / 180;
  const a = color.c * Math.cos(hue);
  const b = color.c * Math.sin(hue);

  const l = color.l + 0.3963377774 * a + 0.2158037573 * b;
  const m = color.l - 0.1055613458 * a - 0.0638541728 * b;
  const s = color.l - 0.0894841775 * a - 1.291485548 * b;

  const l3 = l * l * l;
  const m3 = m * m * m;
  const s3 = s * s * s;

  return [
    clampChannel(4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3),
    clampChannel(-1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3),
    clampChannel(-0.0041960863 * l3 - 0.7034186147 * m3 + 1.707614701 * s3),
  ];
}

export function oklchToSrgb(color: OklchColor): [number, number, number] {
  return oklchToLinearSrgb(color).map(gammaEncode) as [
    number,
    number,
    number,
  ];
}

export function relativeLuminance(color: OklchColor): number {
  const [r, g, b] = oklchToLinearSrgb(color);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrastRatio(a: OklchColor, b: OklchColor): number {
  const first = relativeLuminance(a);
  const second = relativeLuminance(b);
  const lighter = Math.max(first, second);
  const darker = Math.min(first, second);
  return (lighter + 0.05) / (darker + 0.05);
}

function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, "");
}

export function parseDeclarations(source: string): Record<string, string> {
  const declarations: Record<string, string> = {};

  for (const entry of stripComments(source).split(";")) {
    const trimmed = entry.trim();
    if (trimmed.length === 0) continue;

    const separator = trimmed.indexOf(":");
    if (separator === -1) continue;

    const name = trimmed.slice(0, separator).trim();
    const value = trimmed.slice(separator + 1).trim();
    if (name.startsWith("--") && value.length > 0) {
      declarations[name] = value;
    }
  }

  return declarations;
}

/** Reads custom properties from the first matching top-level CSS block. */
export function parseCssBlockTokens(
  css: string,
  selector: string,
): Record<string, string> {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = new RegExp(`${escaped}\\s*\\{([\\s\\S]*?)\\}`).exec(css);
  if (match === null) {
    throw new Error(`CSS block not found: ${selector}`);
  }

  return parseDeclarations(match[1]);
}

export function resolveToken(
  tokens: Record<string, string>,
  name: string,
): string {
  const key = name.startsWith("--") ? name : `--${name}`;

  const resolve = (token: string, seen: ReadonlySet<string>): string => {
    if (seen.has(token)) {
      throw new Error(`Circular token reference: ${token}`);
    }

    const value = tokens[token];
    if (value === undefined) {
      throw new Error(`Unknown token: ${token}`);
    }

    const nextSeen = new Set(seen).add(token);
    return value.replace(/var\(\s*(--[\w-]+)\s*\)/g, (_match, reference) =>
      resolve(reference, nextSeen),
    );
  };

  return resolve(key, new Set());
}

export function tokenContrast(
  tokens: Record<string, string>,
  foreground: string,
  background: string,
): number {
  return contrastRatio(
    parseOklch(resolveToken(tokens, foreground)),
    parseOklch(resolveToken(tokens, background)),
  );
}
