import type {
  AudienceResearch,
  CampaignBrief,
  CopyVariant,
} from "@/lib/schemas";

export const haircareBrief: CampaignBrief = {
  product: "Aurelia Repair & Shine shampoo and conditioner set",
  goal: "Launch a fictional hair-care line and drive first purchases",
  audience: "Adults aged 25 to 40 who colour or heat-style their hair",
  tone: "Warm, confident, lightly playful",
  channels: ["instagram", "email", "display"],
  constraints: [
    "No medical or guaranteed repair claims",
    "Include a first-order offer disclaimer where a price appears",
  ],
};

export const haircareResearch: AudienceResearch = {
  summary:
    "The audience wants visible shine without a long routine. They distrust miracle claims and respond to specific, achievable outcomes.",
  segments: [
    {
      name: "Busy professionals",
      description: "Time-poor commuters who style their hair most weekdays.",
      pain_points: [
        "Frizz returns by mid-afternoon",
        "Styling takes longer than they want",
      ],
      messaging_angles: [
        "Three-minute routine",
        "Shine that survives the commute",
      ],
    },
    {
      name: "Colour maintainers",
      description: "Adults refreshing colour every six to eight weeks.",
      pain_points: [
        "Colour fades faster than expected",
        "Hair feels dry after cleansing",
      ],
      messaging_angles: [
        "Colour-kind cleansing",
        "Softness after the first wash",
      ],
    },
  ],
};

export const haircareCopy: CopyVariant[] = [
  {
    channel: "instagram",
    headline: "Shine that keeps up with your day",
    description:
      "A colour-kind cleanse and a lightweight conditioner for hair that looks polished from morning to evening.",
    cta: "Meet Aurelia",
  },
  {
    channel: "email",
    headline: "Your three-minute shine routine",
    description:
      "Repair & Shine pairs a gentle cleanse with a conditioner that smooths without weighing hair down.",
    cta: "Shop the set",
  },
  {
    channel: "display",
    headline: "Polished hair, without the extra steps",
    description:
      "A simple two-step routine for shine and softness. First orders include a sample sachet.",
    cta: "Try Aurelia",
  },
];
