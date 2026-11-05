import { z } from "zod";
import { text } from "./common";

export const campaignBrief = z.object({
  product: text,
  goal: text,
  audience: text,
  tone: text,
  channels: z.array(text).min(1),
  constraints: z.array(text),
});

export const audienceSegment = z.object({
  name: text,
  description: text,
  pain_points: z.array(text).min(1),
  messaging_angles: z.array(text).min(1),
});

export const audienceResearch = z.object({
  summary: text,
  segments: z.array(audienceSegment).min(1),
});

export const copyVariant = z.object({
  channel: text,
  headline: text,
  description: text,
  cta: text,
});

export const creativeDirection = z.object({
  concept: text,
  style_guide: text,
  composition: text,
  image_prompts: z.array(text).min(1),
  video_prompts: z.array(text).optional(),
  negative_prompts: z.array(text),
});

export const assetKind = z.enum(["image", "video"]);

export const asset = z.object({
  uri: text,
  checksum: text,
  model: text,
  seed: z.number().int(),
  prompt: text,
  kind: assetKind.optional(),
  width: z.number().int().positive().optional(),
  height: z.number().int().positive().optional(),
  alt_text: text.optional(),
});

export const complianceItem = z.object({
  claim: text,
  status: z.enum(["pass", "fail"]),
  reason: text,
  policy: text.optional(),
});

export const complianceReport = z.object({
  passed: z.boolean().optional(),
  items: z.array(complianceItem),
});

export const scoreDimensionKey = z.enum([
  "brief_alignment",
  "audience_fit",
  "copy_quality",
  "visual_quality",
  "compliance_risk",
]);

export const scoreDimension = z.object({
  dimension: scoreDimensionKey,
  score: z.number().min(0).max(10),
  justification: text,
});

export const creativeScore = z.object({
  dimensions: z.array(scoreDimension).min(1),
  total: z.number().min(0).max(100),
  recommendation: text.optional(),
});

export const campaignPackage = z.object({
  brief: campaignBrief,
  research: audienceResearch,
  copy: z.array(copyVariant).min(1),
  direction: creativeDirection,
  assets: z.array(asset),
  compliance: complianceReport,
  score: creativeScore,
});

export type CampaignBrief = z.infer<typeof campaignBrief>;
export type AudienceResearch = z.infer<typeof audienceResearch>;
export type CopyVariant = z.infer<typeof copyVariant>;
export type CreativeDirection = z.infer<typeof creativeDirection>;
export type Asset = z.infer<typeof asset>;
export type ComplianceReport = z.infer<typeof complianceReport>;
export type CreativeScore = z.infer<typeof creativeScore>;
export type CampaignPackage = z.infer<typeof campaignPackage>;
