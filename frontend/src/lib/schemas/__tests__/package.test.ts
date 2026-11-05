import { describe, expect, it } from "vitest";
import type { ZodType } from "zod";
import {
  asset,
  audienceResearch,
  campaignBrief,
  campaignPackage,
  complianceReport,
  copyVariant,
  creativeDirection,
  creativeScore,
} from "@/lib/schemas";
import { haircarePackage } from "@/mocks/fixtures";

const invalidCases: Array<[string, ZodType, unknown]> = [
  ["brief", campaignBrief, { ...haircarePackage.brief, product: "" }],
  ["research", audienceResearch, { ...haircarePackage.research, segments: [] }],
  ["copy variant", copyVariant, { ...haircarePackage.copy[0], cta: "" }],
  ["direction", creativeDirection, { ...haircarePackage.direction, image_prompts: [] }],
  ["asset", asset, { ...haircarePackage.assets[0], seed: 1.5 }],
  [
    "compliance",
    complianceReport,
    { items: [{ claim: "A claim", status: "maybe", reason: "Unsure" }] },
  ],
  [
    "score",
    creativeScore,
    { dimensions: haircarePackage.score.dimensions, total: 101 },
  ],
];

describe("campaign package schemas", () => {
  it("parses a complete package", () => {
    expect(campaignPackage.safeParse(haircarePackage).success).toBe(true);
  });

  it("rejects a package with an empty copy list", () => {
    expect(
      campaignPackage.safeParse({ ...haircarePackage, copy: [] }).success,
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
