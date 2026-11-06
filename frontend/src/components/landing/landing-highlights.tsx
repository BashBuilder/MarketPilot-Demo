import { History, ShieldCheck, Sparkles } from "lucide-react";

const highlights = [
  {
    icon: Sparkles,
    title: "A full creative team",
    description:
      "Research, copy, art direction, visuals and review arrive as one coherent campaign package.",
  },
  {
    icon: ShieldCheck,
    title: "Checked before you see it",
    description:
      "Every claim is scored against compliance rules, and nothing ships without your approval.",
  },
  {
    icon: History,
    title: "Every revision preserved",
    description:
      "Each round becomes a new version, so you can compare what changed and why.",
  },
] as const;

export function LandingHighlights() {
  return (
    <section
      aria-labelledby="highlights-heading"
      className="flex flex-col gap-lg"
    >
      <div className="flex flex-col gap-2xs">
        <h2
          id="highlights-heading"
          className="text-2xs font-medium tracking-wider text-muted-foreground uppercase"
        >
          Why MarketPilot
        </h2>
        <p className="max-w-prose text-2xl font-medium tracking-tight text-balance">
          One brief in. A campaign you can defend out.
        </p>
      </div>

      <ul className="grid gap-sm md:grid-cols-3">
        {highlights.map((highlight) => {
          const Icon = highlight.icon;
          return (
            <li
              key={highlight.title}
              className="flex flex-col gap-xs rounded-xl border border-border bg-card p-md"
            >
              <span className="grid size-9 place-items-center rounded-lg bg-accent text-accent-foreground">
                <Icon aria-hidden="true" className="size-4" />
              </span>
              <h3 className="text-sm font-medium text-foreground">
                {highlight.title}
              </h3>
              <p className="text-sm text-muted-foreground">
                {highlight.description}
              </p>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
