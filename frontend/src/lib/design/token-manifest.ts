export interface ColorTokenGroup {
  label: string;
  description: string;
  tokens: readonly string[];
}

/**
 * Every semantic colour token in globals.css, grouped by the job it does.
 * The style guide and its coverage test both read from this list.
 */
export const colorTokenGroups: readonly ColorTokenGroup[] = [
  {
    label: "Surfaces",
    description: "Page, card, popover, and subtle tinted surfaces.",
    tokens: [
      "--background",
      "--card",
      "--popover",
      "--muted",
      "--secondary",
      "--accent",
    ],
  },
  {
    label: "Text",
    description: "Foreground values paired with each surface.",
    tokens: [
      "--foreground",
      "--card-foreground",
      "--popover-foreground",
      "--muted-foreground",
      "--secondary-foreground",
      "--accent-foreground",
      "--primary-foreground",
      "--brand-foreground",
    ],
  },
  {
    label: "Brand and focus",
    description: "The single accent, its primary alias, and the focus ring.",
    tokens: ["--brand", "--primary", "--ring"],
  },
  {
    label: "Borders",
    description: "Decorative dividers and control boundaries.",
    tokens: ["--border", "--input"],
  },
  {
    label: "Status",
    description: "Functional error colour; not a second brand accent.",
    tokens: ["--destructive"],
  },
  {
    label: "Charts",
    description: "Accent-led chart ramps for score visualisations.",
    tokens: [
      "--chart-1",
      "--chart-2",
      "--chart-3",
      "--chart-4",
      "--chart-5",
    ],
  },
  {
    label: "Sidebar",
    description: "Navigation surface and its matching foreground pairs.",
    tokens: [
      "--sidebar",
      "--sidebar-foreground",
      "--sidebar-primary",
      "--sidebar-primary-foreground",
      "--sidebar-accent",
      "--sidebar-accent-foreground",
      "--sidebar-border",
      "--sidebar-ring",
    ],
  },
];

export interface TypeStep {
  token: string;
  className: string;
  label: string;
  sample: string;
}

export const typeScale: readonly TypeStep[] = [
  { token: "--text-2xs", className: "text-2xs", label: "2xs", sample: "Campaign package · v3" },
  { token: "--text-xs", className: "text-xs", label: "xs", sample: "Audience research" },
  { token: "--text-sm", className: "text-sm", label: "sm", sample: "Primary audience: adults 25–40" },
  { token: "--text-base", className: "text-base", label: "base", sample: "A calm, confident campaign for everyday hair care." },
  { token: "--text-lg", className: "text-lg", label: "lg", sample: "Editorial headlines with room to breathe." },
  { token: "--text-xl", className: "text-xl", label: "xl", sample: "Research-informed messaging." },
  { token: "--text-2xl", className: "text-2xl", label: "2xl", sample: "From idea to approved campaign." },
  { token: "--text-3xl", className: "text-3xl", label: "3xl", sample: "Creative that earns attention." },
  { token: "--text-4xl", className: "text-4xl", label: "4xl", sample: "Campaigns, composed." },
  { token: "--text-5xl", className: "text-5xl", label: "5xl", sample: "Ideas into campaigns" },
  { token: "--text-6xl", className: "text-6xl", label: "6xl", sample: "Editorial rhythm" },
  { token: "--text-7xl", className: "text-7xl", label: "7xl", sample: "Campaigns" },
  { token: "--text-display", className: "text-display", label: "display", sample: "Ideas" },
];

export const spacingScale = [
  { token: "--spacing", label: "base" },
  { token: "--spacing-3xs", label: "3xs" },
  { token: "--spacing-2xs", label: "2xs" },
  { token: "--spacing-xs", label: "xs" },
  { token: "--spacing-sm", label: "sm" },
  { token: "--spacing-md", label: "md" },
  { token: "--spacing-lg", label: "lg" },
  { token: "--spacing-xl", label: "xl" },
  { token: "--spacing-2xl", label: "2xl" },
  { token: "--spacing-3xl", label: "3xl" },
  { token: "--spacing-4xl", label: "4xl" },
  { token: "--spacing-section", label: "section" },
] as const;

export const radiusScale = [
  { token: "--radius", label: "base" },
  { token: "--radius-sm", label: "sm" },
  { token: "--radius-md", label: "md" },
  { token: "--radius-lg", label: "lg" },
  { token: "--radius-xl", label: "xl" },
  { token: "--radius-2xl", label: "2xl" },
  { token: "--radius-3xl", label: "3xl" },
  { token: "--radius-4xl", label: "4xl" },
] as const;

export const trackingScale = [
  { token: "--tracking-tight", label: "tight" },
  { token: "--tracking-normal", label: "normal" },
  { token: "--tracking-wide", label: "wide" },
  { token: "--tracking-wider", label: "wider" },
] as const;

export const fontTokens = [
  { token: "--font-sans", label: "sans", sample: "MarketPilot campaigns" },
  { token: "--font-heading", label: "heading", sample: "Ideas into campaigns" },
] as const;
