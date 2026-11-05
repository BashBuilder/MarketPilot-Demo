import { z } from "zod";
import { campaignStatus, isoDateTime, text, uuid } from "./common";

export const campaignSummary = z.object({
  id: uuid,
  idea: text,
  status: campaignStatus,
  latest_version: z.number().int().positive().nullable(),
  latest_score: z.number().min(0).max(100).nullable(),
  active_run_id: uuid.nullable(),
  created_at: isoDateTime,
  updated_at: isoDateTime,
});

export const campaignList = z.array(campaignSummary);

/** The backend returns the same summary shape from list and detail. */
export const campaignDetail = campaignSummary;

export const versionSummary = z.object({
  version: z.number().int().positive(),
  parent_version_id: uuid.nullable(),
  score: z.number().min(0).max(100).nullable(),
  created_at: isoDateTime,
});

export const versionList = z.array(versionSummary);

export const diffChange = z.object({
  path: text,
  before: z.unknown(),
  after: z.unknown(),
});

export const versionDiff = z.object({
  from: z.number().int().positive(),
  to: z.number().int().positive(),
  changes: z.array(diffChange),
});

export type CampaignSummary = z.infer<typeof campaignSummary>;
export type CampaignDetail = CampaignSummary;
export type VersionSummary = z.infer<typeof versionSummary>;
export type VersionDiff = z.infer<typeof versionDiff>;
