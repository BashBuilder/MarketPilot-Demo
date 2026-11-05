import { z } from "zod";
import { agentName, uuid } from "./common";

export const createCampaignRequest = z.object({
  idea: z.string().trim().min(1).max(2000),
});

export const createCampaignResponse = z.object({
  campaign_id: uuid,
  run_id: uuid,
});

export const approveRunRequest = z.object({
  comment: z.string().max(2000).optional(),
});

export const reviseRunRequest = z.object({
  comment: z.string().trim().min(1).max(2000),
  target_node: agentName.optional(),
});

export const approveRunResponse = z.object({
  run_id: uuid,
  status: z.literal("approved"),
  version: z.number().int().positive(),
});

export const reviseRunResponse = z.object({
  run_id: uuid,
  status: z.literal("revision_requested"),
  version: z.number().int().positive(),
  new_run_id: uuid,
});

export type CreateCampaignInput = z.infer<typeof createCampaignRequest>;
export type CreateCampaignResult = z.infer<typeof createCampaignResponse>;
export type ApproveRunInput = z.infer<typeof approveRunRequest>;
export type ReviseRunInput = z.infer<typeof reviseRunRequest>;
export type ApproveRunResult = z.infer<typeof approveRunResponse>;
export type ReviseRunResult = z.infer<typeof reviseRunResponse>;
