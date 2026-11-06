import { EmptyState } from "@/components/states/empty-state";
import type { CampaignBrief } from "@/lib/schemas";
import { cn } from "@/lib/utils";

interface BriefCardProps {
  brief?: CampaignBrief | null;
  className?: string;
}

export function BriefCard({ brief, className }: BriefCardProps) {
  if (!brief) {
    return (
      <EmptyState
        className={className}
        title="No brief yet"
        description="The Brief agent has not produced a brief for this version."
      />
    );
  }

  return (
    <section
      aria-label="Campaign brief"
      className={cn(
        "flex flex-col gap-lg rounded-xl border border-border bg-card p-lg",
        className,
      )}
    >
      <header className="flex flex-col gap-2xs">
        <p className="text-2xs font-medium tracking-wider text-muted-foreground uppercase">
          Brief
        </p>
        <h2 className="text-xl font-semibold tracking-tight">Campaign brief</h2>
      </header>

      <p className="text-lg font-medium tracking-tight text-foreground">
        {brief.product}
      </p>

      <dl className="grid gap-md sm:grid-cols-2">
        <div className="flex flex-col gap-2xs">
          <dt className="text-2xs font-medium tracking-wider text-muted-foreground uppercase">
            Goal
          </dt>
          <dd className="text-sm text-foreground">{brief.goal}</dd>
        </div>
        <div className="flex flex-col gap-2xs">
          <dt className="text-2xs font-medium tracking-wider text-muted-foreground uppercase">
            Audience
          </dt>
          <dd className="text-sm text-foreground">{brief.audience}</dd>
        </div>
        <div className="flex flex-col gap-2xs">
          <dt className="text-2xs font-medium tracking-wider text-muted-foreground uppercase">
            Tone
          </dt>
          <dd className="text-sm text-foreground">{brief.tone}</dd>
        </div>
      </dl>

      <div className="grid gap-lg sm:grid-cols-2">
        <section aria-label="Channels" className="flex flex-col gap-xs">
          <h3 className="text-sm font-medium">Channels</h3>
          <ul className="list-disc pl-md text-sm text-muted-foreground marker:text-border">
            {brief.channels.map((channel, index) => (
              <li key={`${channel}-${index}`}>{channel}</li>
            ))}
          </ul>
        </section>

        <section aria-label="Constraints" className="flex flex-col gap-xs">
          <h3 className="text-sm font-medium">Constraints</h3>
          <ul className="list-disc pl-md text-sm text-muted-foreground marker:text-border">
            {brief.constraints.map((constraint, index) => (
              <li key={`${constraint}-${index}`}>{constraint}</li>
            ))}
          </ul>
        </section>
      </div>
    </section>
  );
}
