import type { CampaignPackage } from "@/lib/schemas";
import {
  haircareBrief,
  haircareCopy,
  haircareResearch,
} from "./package-copy";
import {
  haircareAssets,
  haircareCompliance,
  haircareDirection,
  haircareScore,
} from "./package-visuals";

// `satisfies` keeps the fixture's non-null section types after the contract
// allowed partially produced versions, so mock code can still read sections
// directly; the schema still validates the shape.
export const haircarePackage = {
  brief: haircareBrief,
  research: haircareResearch,
  copy: { variants: haircareCopy },
  direction: haircareDirection,
  assets: { assets: haircareAssets },
  compliance: haircareCompliance,
  score: haircareScore,
} satisfies CampaignPackage;

export const revisedPackage = {
  ...haircarePackage,
  copy: {
    variants: haircareCopy.map((variant, index) =>
      index === 0
        ? { ...variant, headline: "Shine that lasts past the commute" }
        : variant,
    ),
  },
  score: {
    ...haircareScore,
    copy_quality: {
      score: 9,
      justification:
        "The revised hook is more distinctive while staying within the claims policy.",
    },
    total: 91,
  },
} satisfies CampaignPackage;
