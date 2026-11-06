import {
  FileText,
  Image as ImageIcon,
  PenLine,
  Search,
  ShieldCheck,
  Sparkles,
  Star,
  UserCheck,
} from "lucide-react";

interface PipelineStep {
  name: string;
  role: string;
  icon: typeof FileText;
}

const steps: readonly PipelineStep[] = [
  { name: "Brief", role: "Frame the idea", icon: FileText },
  { name: "Research", role: "Map the audience", icon: Search },
  { name: "Copywriter", role: "Write every channel", icon: PenLine },
  { name: "Creative Director", role: "Set the direction", icon: Sparkles },
  { name: "Designer", role: "Produce the visuals", icon: ImageIcon },
  { name: "Compliance", role: "Check each claim", icon: ShieldCheck },
  { name: "Reviewer", role: "Score the package", icon: Star },
];

export function PipelinePreview() {
  return (
    <article
      aria-label="Agent pipeline preview"
      className="rounded-2xl border border-border bg-card/80 p-sm shadow-sm backdrop-blur-sm sm:p-md"
    >
      <header className="flex items-center justify-between gap-sm px-xs pb-sm">
        <div className="flex flex-col">
          <p className="text-2xs font-medium tracking-wider text-muted-foreground uppercase">
            The pipeline
          </p>
          <p className="text-sm font-medium text-foreground">Eight agents, one brief</p>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-brand/30 bg-brand/10 px-2 py-0.5 text-2xs font-medium text-brand">
          <span aria-hidden="true" className="size-1.5 rounded-full bg-current" />
          Human in the loop
        </span>
      </header>

      <ol className="flex flex-col" aria-label="Pipeline steps">
        {steps.map((step, index) => {
          const Icon = step.icon;
          return (
            <li
              key={step.name}
              className="relative flex items-center gap-sm py-1.5 pl-xs"
            >
              {index < steps.length - 1 ? (
                <span
                  aria-hidden="true"
                  className="absolute top-1/2 left-5 h-full w-px bg-border"
                />
              ) : null}
              <span
                aria-hidden="true"
                className="relative z-10 grid size-6 shrink-0 place-items-center rounded-full border border-border bg-background text-muted-foreground"
              >
                <Icon className="size-3" />
              </span>
              <div className="flex min-w-0 flex-1 items-baseline justify-between gap-xs">
                <p className="truncate text-xs font-medium text-foreground">
                  {step.name}
                </p>
                <p className="truncate text-2xs text-muted-foreground">
                  {step.role}
                </p>
              </div>
            </li>
          );
        })}

        <li className="mt-1 flex items-center gap-sm rounded-lg border border-brand/25 bg-brand/5 p-xs">
          <span
            aria-hidden="true"
            className="grid size-6 shrink-0 place-items-center rounded-full bg-brand text-brand-foreground"
          >
            <UserCheck className="size-3" />
          </span>
          <div className="flex min-w-0 flex-1 items-baseline justify-between gap-xs">
            <p className="truncate text-xs font-medium text-foreground">You</p>
            <p className="truncate text-2xs text-muted-foreground">
              Approve or revise
            </p>
          </div>
        </li>
      </ol>
    </article>
  );
}
