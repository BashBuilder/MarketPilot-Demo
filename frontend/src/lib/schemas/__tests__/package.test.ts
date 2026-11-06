import { describe, expect, it } from "vitest";
import type { ZodType } from "zod";
import {
  asset,
  audienceResearch,
  audienceSegment,
  campaignBrief,
  campaignPackage,
  complianceItem,
  complianceReport,
  copyVariant,
  creativeDirection,
  creativeScore,
  researchSource,
  scoreDimension,
} from "@/lib/schemas";
import { haircarePackage } from "@/mocks/fixtures";

const invalidCases: Array<[string, ZodType, unknown]> = [
  ["brief", campaignBrief, { ...haircarePackage.brief, product: "" }],
  [
    "audience segment",
    audienceSegment,
    { ...haircarePackage.research.segments[0], description: "" },
  ],
  ["research", audienceResearch, { ...haircarePackage.research, segments: [] }],
  [
    "research without top-level pain points",
    audienceResearch,
    {
      segments: haircarePackage.research.segments,
      messaging_angles: ["Angle"],
      sources: haircarePackage.research.sources,
    },
  ],
  [
    "research without sources",
    audienceResearch,
    { ...haircarePackage.research, sources: [] },
  ],
  [
    "research source with an empty title",
    researchSource,
    { title: "", url: "https://example.com/source" },
  ],
  [
    "research source with a non-http URL",
    researchSource,
    { title: "Unsafe source", url: "javascript:alert(1)" },
  ],
  ["copy variant", copyVariant, { ...haircarePackage.copy.variants[0], cta: "" }],
  ["direction", creativeDirection, { ...haircarePackage.direction, image_prompts: [] }],
  [
    "direction without negative prompts",
    creativeDirection,
    { ...haircarePackage.direction, negative_prompts: [] },
  ],
  ["asset", asset, { ...haircarePackage.assets.assets[0], seed: 1.5 }],
  [
    "asset with a non-hex checksum",
    asset,
    { ...haircarePackage.assets.assets[0], checksum: "not-a-checksum" },
  ],
  [
    "asset with a whitespace uri",
    asset,
    { ...haircarePackage.assets.assets[0], uri: "/mock assets/aurelia.webp" },
  ],
  [
    "compliance item with a non-boolean outcome",
    complianceReport,
    { items: [{ check: "A claim", passed: "maybe", reason: "Unsure" }] },
  ],
  [
    "compliance item without a check",
    complianceItem,
    { passed: true, reason: "No issue." },
  ],
  [
    "score dimension with a multi-line justification",
    scoreDimension,
    { score: 8, justification: "Line one\nLine two" },
  ],
  [
    "score with an out-of-range total",
    creativeScore,
    { ...haircarePackage.score, total: 101 },
  ],
  [
    "score missing a dimension",
    creativeScore,
    {
      ...haircarePackage.score,
      compliance_risk: undefined,
    },
  ],
];

describe("campaign package schemas", () => {
  it("parses a complete backend-shaped package", () => {
    expect(campaignPackage.safeParse(haircarePackage).success).toBe(true);
  });

  it("keeps failed compliance items in the package shape", () => {
    const compliance = {
      items: [{ check: "Guaranteed repair", passed: false, reason: "Absolute claim." }],
    };
    expect(complianceReport.safeParse(compliance).success).toBe(true);
  });

  it("rejects empty copy or asset sets", () => {
    expect(
      campaignPackage.safeParse({
        ...haircarePackage,
        copy: { variants: [] },
      }).success,
    ).toBe(false);
    expect(
      campaignPackage.safeParse({
        ...haircarePackage,
        assets: { assets: [] },
      }).success,
    ).toBe(false);
  });

  it("rejects the old bare-array copy and asset shapes", () => {
    expect(
      campaignPackage.safeParse({
        ...haircarePackage,
        copy: haircarePackage.copy.variants,
      }).success,
    ).toBe(false);
    expect(
      campaignPackage.safeParse({
        ...haircarePackage,
        assets: haircarePackage.assets.assets,
      }).success,
    ).toBe(false);
  });

  it("rejects a package missing a brief field", () => {
    const brief = { ...haircarePackage.brief };
    delete (brief as Partial<typeof brief>).product;
    expect(
      campaignPackage.safeParse({ ...haircarePackage, brief }).success,
    ).toBe(false);
  });

  it.each(invalidCases)("rejects an invalid %s", (_name, schema, invalid) => {
    expect(schema.safeParse(invalid).success).toBe(false);
  });
});
