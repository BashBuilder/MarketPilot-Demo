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
  name: z.string().min(2),
  description: z.string().min(5),
});

export const researchSource = z.object({
  title: z.string().min(1).max(300),
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
  channel: z.string().min(2),
  headline: z.string().min(5),
  description: z.string().min(10),
  cta: z.string().min(2),
});

/** The backend groups copy in an `AdCopySet` object, not a bare array. */
export const adCopySet = z.object({
  variants: z.array(copyVariant).min(1),
});

export const creativeDirection = z.object({
  style_guide: z.string().min(5),
  composition: z.string().min(5),
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
  model: z.string().min(2),
  // Backend seeds are 64-bit integers and can exceed Number.MAX_SAFE_INTEGER.
  // `z.number().int()` rejects them, so keep the integer check without the
  // safe-range cap. JavaScript has already rounded the value by JSON.parse.
  seed: z.number().nonnegative().refine(Number.isInteger, "must be an integer"),
  prompt: z.string().min(5),
});

/** The backend groups generated files in an `AssetSet` object. */
export const assetSet = z.object({
  assets: z.array(asset).min(1),
});

export const complianceItem = z.object({
  check: z.string().min(3),
  passed: z.boolean(),
  reason: z.string().min(5),
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

/**
 * A version may be snapshotted at the human gate before every agent finishes.
 * The backend serializes those versions with `response_model_exclude_none`, so
 * an unproduced section arrives either as `null` or omitted entirely.
 */
export const campaignPackage = z.object({
  brief: campaignBrief.nullish(),
  research: audienceResearch.nullish(),
  copy: adCopySet.nullish(),
  direction: creativeDirection.nullish(),
  assets: assetSet.nullish(),
  compliance: complianceReport.nullish(),
  score: creativeScore.nullish(),
});

export type CampaignBrief = z.infer<typeof campaignBrief>;
export type ResearchSource = z.infer<typeof researchSource>;
export type AudienceResearch = z.infer<typeof audienceResearch>;
export type CopyVariant = z.infer<typeof copyVariant>;
export type AdCopySet = z.infer<typeof adCopySet>;
export type CreativeDirection = z.infer<typeof creativeDirection>;
export type Asset = z.infer<typeof asset>;
export type AssetSet = z.infer<typeof assetSet>;
export type ComplianceReport = z.infer<typeof complianceReport>;
export type CreativeScore = z.infer<typeof creativeScore>;
export type CampaignPackage = z.infer<typeof campaignPackage>;
