import type {
  Asset,
  ComplianceReport,
  CreativeDirection,
  CreativeScore,
} from "@/lib/schemas";

export const haircareDirection: CreativeDirection = {
  style_guide:
    "Editorial product photography, warm neutral palette, soft window light, no visible logos beyond the fictional brand.",
  composition:
    "Product low and left with generous negative space top right for the headline. Shallow depth of field.",
  image_prompts: [
    "Editorial still life of an amber shampoo and conditioner set on a pale stone shelf, soft morning window light, shallow depth of field, warm neutral palette",
  ],
  negative_prompts: [
    "medical imagery",
    "split ends close-up",
    "celebrity likeness",
    "watermarks",
  ],
  video_prompts: [
    "Slow push in on the bottled set as a hand lifts a strand of glossy hair in the background",
  ],
};

export const haircareAssets: Asset[] = [
  {
    uri: "/mock-assets/aurelia-set.webp",
    checksum: "6b0e1d0c9f63f0f1d2c1a7a4e2f9b8d7c6a5e4f3d2c1b0a9e8f7d6c5b4a3f2e1",
    model: "flux.1-schnell",
    seed: 48291,
    prompt: "Editorial still life of an amber shampoo and conditioner set, soft morning light",
  },
];

export const haircareCompliance: ComplianceReport = {
  items: [
    {
      check: "Colour-kind cleansing",
      passed: true,
      reason: "Qualified as a cosmetic benefit without a repair or treatment promise.",
    },
    {
      check: "First orders include a sample sachet",
      passed: true,
      reason: "Offer is clearly described and does not imply a guaranteed result.",
    },
    {
      check: "No medical or guaranteed repair claims",
      passed: true,
      reason: "Copy avoids treatment, cure and guaranteed repair language.",
    },
  ],
};

export const haircareScore: CreativeScore = {
  brief_alignment: {
    score: 9,
    justification: "Covers the product, audience and launch goal without adding scope.",
  },
  audience_fit: {
    score: 8.5,
    justification: "Speaks to time-poor, colour-maintaining adults with specific outcomes.",
  },
  copy_quality: {
    score: 8,
    justification: "Clear channel-native copy; the display variant could be more distinctive.",
  },
  visual_quality: {
    score: 9,
    justification: "Prompt matches the editorial direction and leaves room for the headline.",
  },
  compliance_risk: {
    score: 8.5,
    justification: "One wording choice was tightened to avoid implying repair.",
  },
  total: 86,
};
