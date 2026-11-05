import { z } from "zod";

/** Backend timestamps are ISO-8601 strings with an explicit offset or `Z`. */
export const isoDateTime = z.iso.datetime({ offset: true });

export const uuid = z.uuid();

export const text = z.string().min(1);

export const agentName = z.enum([
  "brief",
  "research",
  "copywriter",
  "creative_director",
  "designer",
  "compliance",
  "reviewer",
  "supervisor",
]);

export type AgentName = z.infer<typeof agentName>;

/** Status of a single workflow run, as exposed on a version. */
export const runStatus = z.enum([
  "running",
  "awaiting_approval",
  "approved",
  "revision_requested",
  "failed",
]);

export type WorkflowRunStatus = z.infer<typeof runStatus>;

/** Mirrors the backend `WorkflowState.status` enum. */
export const campaignStatus = z.enum([
  "pending",
  "running",
  "awaiting_approval",
  "approved",
  "revising",
  "completed",
  "failed",
]);

export type CampaignStatus = z.infer<typeof campaignStatus>;
