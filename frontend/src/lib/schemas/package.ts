import { z } from "zod";
import { text } from "./common";

export const campaignBrief = z.object({
  product: z.string().min(2),
  goal: z.string().min(5),
  audience: z.string().min(5),
  tone: z.string().min(3),
  channels: z.array(text).min(1),
  constraints: z.array(text).min(1),
});

export const audienceSegment = z.object({
  name: text,
  description: text,
});

export const researchSource = z.object({
  title: text,
  // Only http(s) links may become anchors in the UI; this blocks javascript:
  // and other executable URL schemes from backend data.
  url: z
    .string()
    .url()
    .regex(/^https?:\/\//i, "must be an http(s) URL"),
});

export const audienceResearch = z.object({
  segments: z.array(audienceSegment).min(1),
  pain_points: z.array(text).min(1),
  messaging_angles: z.array(text).min(1),
  sources: z.array(researchSource).min(1),
});

export const copyVariant = z.object({
  channel: text,
  headline: text,
  description: text,
  cta: text,
});

export const creativeDirection = z.object({
  style_guide: text,
  composition: text,
  image_prompts: z.array(text).min(1),
  video_prompts: z.array(text).min(1),
  negative_prompts: z.array(text).min(1),
});

export const asset = z.object({
  uri: z
    .string()
    .min(5)
    .regex(/^\S+$/, "must not contain whitespace"),
  checksum: z.string().regex(/^[0-9a-fA-F]{64}$/, "must be 64 hex characters"),
  model: text,
  seed: z.number().int().nonnegative(),
  prompt: text,
});

export const complianceItem = z.object({
  check: text,
  passed: z.boolean(),
  reason: text,
});

export const complianceReport = z.object({
  items: z.array(complianceItem).min(1),
});

/** Fixed backend dimension keys, in rubric order. */
export const scoreDimensionKeys = [
  "brief_alignment",
  "audience_fit",
  "copy_quality",
  "visual_quality",
  "compliance_risk",
] as const;

export const scoreDimension = z.object({
  score: z.number().min(0).max(10),
  justification: z
    .string()
    .min(5)
    .max(200)
    .regex(/^[^\r\n]*$/, "must be a single line"),
});

export const creativeScore = z.object({
  brief_alignment: scoreDimension,
  audience_fit: scoreDimension,
  copy_quality: scoreDimension,
  visual_quality: scoreDimension,
  compliance_risk: scoreDimension,
  total: z.number().min(0).max(100),
});

export const campaignPackage = z.object({
  brief: campaignBrief,
  research: audienceResearch,
  copy: z.array(copyVariant).min(1),
  direction: creativeDirection,
  assets: z.array(asset).min(1),
  compliance: complianceReport,
  score: creativeScore,
});

export type CampaignBrief = z.infer<typeof campaignBrief>;
export type ResearchSource = z.infer<typeof researchSource>;
export type AudienceResearch = z.infer<typeof audienceResearch>;
export type CopyVariant = z.infer<typeof copyVariant>;
export type CreativeDirection = z.infer<typeof creativeDirection>;
export type Asset = z.infer<typeof asset>;
export type ComplianceReport = z.infer<typeof complianceReport>;
export type CreativeScore = z.infer<typeof creativeScore>;
export type CampaignPackage = z.infer<typeof campaignPackage>;
