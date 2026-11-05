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

/**
 * Event envelopes also identify the human approval gate as `human`; pipeline
 * agents remain limited to `agentName`.
 */
export const eventActor = z.union([agentName, z.literal("human")]);

export type EventActor = z.infer<typeof eventActor>;

/** Mirrors the backend `CampaignStatus` enum. */
export const campaignStatus = z.enum([
  "draft",
  "running",
  "awaiting_approval",
  "completed",
  "failed",
]);

export type CampaignStatus = z.infer<typeof campaignStatus>;
