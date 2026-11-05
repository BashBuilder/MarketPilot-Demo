import type {
  CampaignDetail,
  CampaignSummary,
  CampaignVersion,
  VersionDiff,
  VersionSummary,
} from "@/lib/schemas";
import { haircarePackage, revisedPackage } from "./package";

export const campaignId = "7c9e6679-7425-40de-944b-e07fc1f90ae7";
export const runId = "0f8fad5b-d9cb-469f-a165-70867728950e";
export const revisionRunId = "5f2c1d3a-8b6e-4f0a-9c7d-2e1b3a4c5d6e";

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
  created_at: createdAt,
  updated_at: updatedAt,
};

export const campaignDetail: CampaignDetail = {
  ...campaignSummary,
  latest_package: haircarePackage,
};

export const versionSummaryOne: VersionSummary = {
  version: 1,
  parent_version: null,
  created_at: createdAt,
  total_score: 86,
  run_status: "awaiting_approval",
};

export const versionSummaryTwo: VersionSummary = {
  version: 2,
  parent_version: 1,
  created_at: revisedAt,
  total_score: 91,
  run_status: "awaiting_approval",
};

export const versionOne: CampaignVersion = {
  campaign_id: campaignId,
  version: 1,
  parent_version: null,
  created_at: createdAt,
  package: haircarePackage,
  run_id: runId,
  run_status: "awaiting_approval",
};

export const versionTwo: CampaignVersion = {
  campaign_id: campaignId,
  version: 2,
  parent_version: 1,
  created_at: revisedAt,
  package: revisedPackage,
  run_id: revisionRunId,
  run_status: "awaiting_approval",
};

export const revisionDiff: VersionDiff = {
  from_version: 1,
  to_version: 2,
  changes: [
    {
      field: "copy[0].headline",
      before: haircarePackage.copy[0].headline,
      after: revisedPackage.copy[0].headline,
    },
    {
      field: "score.copy_quality.score",
      before: 8,
      after: 9,
    },
    {
      field: "score.total",
      before: 86,
      after: 91,
    },
  ],
};
