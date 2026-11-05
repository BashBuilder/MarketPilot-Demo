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

export const haircarePackage: CampaignPackage = {
  brief: haircareBrief,
  research: haircareResearch,
  copy: haircareCopy,
  direction: haircareDirection,
  assets: haircareAssets,
  compliance: haircareCompliance,
  score: haircareScore,
};

export const revisedPackage: CampaignPackage = {
  ...haircarePackage,
  copy: haircareCopy.map((variant, index) =>
    index === 0
      ? { ...variant, headline: "Shine that lasts past the commute" }
      : variant,
  ),
  score: {
    ...haircareScore,
    copy_quality: {
      score: 9,
      justification:
        "The revised hook is more distinctive while staying within the claims policy.",
    },
    total: 91,
  },
};
