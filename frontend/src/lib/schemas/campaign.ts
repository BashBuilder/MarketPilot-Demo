import { z } from "zod";
import {
  campaignStatus,
  isoDateTime,
  runStatus,
  text,
  uuid,
} from "./common";
import { campaignPackage } from "./package";

export const campaignSummary = z.object({
  id: uuid,
  idea: text,
  status: campaignStatus,
  latest_version: z.number().int().positive().nullable(),
  latest_score: z.number().min(0).max(100).nullable(),
  created_at: isoDateTime,
  updated_at: isoDateTime,
});

export const campaignDetail = campaignSummary.extend({
  latest_package: campaignPackage.nullable(),
});

export const campaignList = z.array(campaignSummary);

export const versionSummary = z.object({
  version: z.number().int().positive(),
  parent_version: z.number().int().positive().nullable(),
  created_at: isoDateTime,
  total_score: z.number().min(0).max(100).nullable(),
});

export const versionList = z.array(versionSummary);

export const campaignVersion = z.object({
  campaign_id: uuid,
  version: z.number().int().positive(),
  parent_version: z.number().int().positive().nullable(),
  created_at: isoDateTime,
  package: campaignPackage,
  run_id: uuid,
  run_status: runStatus,
});

export const diffChange = z.object({
  field: text,
  before: z.unknown(),
  after: z.unknown(),
});

export const versionDiff = z.object({
  from_version: z.number().int().positive(),
  to_version: z.number().int().positive(),
  changes: z.array(diffChange),
});

export type CampaignSummary = z.infer<typeof campaignSummary>;
export type CampaignDetail = z.infer<typeof campaignDetail>;
export type VersionSummary = z.infer<typeof versionSummary>;
export type CampaignVersion = z.infer<typeof campaignVersion>;
export type VersionDiff = z.infer<typeof versionDiff>;
