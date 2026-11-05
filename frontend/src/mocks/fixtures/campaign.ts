import type {
  CampaignPackage,
  CampaignSummary,
  VersionDiff,
  VersionSummary,
} from "@/lib/schemas";
import { haircarePackage, revisedPackage } from "./package";

export const campaignId = "7c9e6679-7425-40de-944b-e07fc1f90ae7";
export const runId = "0f8fad5b-d9cb-469f-a165-70867728950e";
export const revisionRunId = "5f2c1d3a-8b6e-4f0a-9c7d-2e1b3a4c5d6e";
export const versionOneId = "1f2e3d4c-5b6a-4978-8a9b-0c1d2e3f4a5b";

export const createdAt = "2026-11-05T09:00:00.000Z";
export const updatedAt = "2026-11-05T09:04:12.000Z";
export const revisedAt = "2026-11-05T09:10:30.000Z";

export const seedIdea =
  "Create an advertising campaign for a fictional hair-care product targeting adults aged 25 to 40";

export const campaignSummary: CampaignSummary = {
  id: campaignId,
  idea: seedIdea,
  status: "awaiting_approval",
  latest_version: 1,
  latest_score: 86,
  active_run_id: runId,
  created_at: createdAt,
  updated_at: updatedAt,
};

export const versionSummaryOne: VersionSummary = {
  version: 1,
  parent_version_id: null,
  created_at: createdAt,
  score: 86,
};

export const versionSummaryTwo: VersionSummary = {
  version: 2,
  parent_version_id: versionOneId,
  created_at: revisedAt,
  score: 91,
};

export const versionOne: CampaignPackage = haircarePackage;
export const versionTwo: CampaignPackage = revisedPackage;

export const revisionDiff: VersionDiff = {
  from: 1,
  to: 2,
  changes: [
    {
      path: "copy.variants.0.headline",
      before: haircarePackage.copy.variants[0].headline,
      after: revisedPackage.copy.variants[0].headline,
    },
    {
      path: "score.copy_quality.score",
      before: 8,
      after: 9,
    },
    {
      path: "score.total",
      before: 86,
      after: 91,
    },
  ],
};
