import { EmptyState } from "@/components/states/empty-state";
import type { AudienceResearch } from "@/lib/schemas";
import { cn } from "@/lib/utils";

interface ResearchCardProps {
  research?: AudienceResearch | null;
  className?: string;
}

export function ResearchCard({ research, className }: ResearchCardProps) {
  if (!research) {
    return (
      <EmptyState
        className={className}
        title="No research yet"
        description="The Research agent has not produced audience research for this version."
      />
    );
  }

  return (
    <section
      aria-label="Audience research"
      className={cn(
        "flex flex-col gap-lg rounded-xl border border-border bg-card p-lg",
        className,
      )}
    >
      <header className="flex flex-col gap-2xs">
        <p className="text-2xs font-medium tracking-wider text-muted-foreground uppercase">
          Research
        </p>
        <h2 className="text-xl font-semibold tracking-tight">
          Audience research
        </h2>
      </header>

      <section aria-label="Audience segments" className="flex flex-col gap-xs">
        <h3 className="text-sm font-medium">Segments</h3>
        <ul className="grid gap-sm sm:grid-cols-2">
          {research.segments.map((segment, index) => (
            <li
              key={`${segment.name}-${index}`}
              className="rounded-lg border border-border/70 bg-background/60 p-md"
            >
              <p className="text-sm font-medium text-foreground">
                {segment.name}
              </p>
              <p className="mt-2xs text-sm text-muted-foreground">
                {segment.description}
              </p>
            </li>
          ))}
        </ul>
      </section>

      <div className="grid gap-lg sm:grid-cols-2">
        <section aria-label="Pain points" className="flex flex-col gap-xs">
          <h3 className="text-sm font-medium">Pain points</h3>
          <ul className="list-disc pl-md text-sm text-muted-foreground marker:text-border">
            {research.pain_points.map((painPoint, index) => (
              <li key={`${painPoint}-${index}`}>{painPoint}</li>
            ))}
          </ul>
        </section>

        <section aria-label="Messaging angles" className="flex flex-col gap-xs">
          <h3 className="text-sm font-medium">Messaging angles</h3>
          <ul className="list-disc pl-md text-sm text-muted-foreground marker:text-border">
            {research.messaging_angles.map((angle, index) => (
              <li key={`${angle}-${index}`}>{angle}</li>
            ))}
          </ul>
        </section>
      </div>
    </section>
  );
}
