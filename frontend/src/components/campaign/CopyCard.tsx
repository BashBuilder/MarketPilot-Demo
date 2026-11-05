import { EmptyState } from "@/components/states/empty-state";
import type { CopyVariant } from "@/lib/schemas";
import { cn } from "@/lib/utils";

interface CopyCardProps {
  copy?: CopyVariant[] | null;
  className?: string;
}

/** Group variants by channel while preserving the backend's order. */
function groupByChannel(
  variants: CopyVariant[],
): Array<[string, CopyVariant[]]> {
  const groups = new Map<string, CopyVariant[]>();

  for (const variant of variants) {
    const existing = groups.get(variant.channel);
    if (existing) {
      existing.push(variant);
    } else {
      groups.set(variant.channel, [variant]);
    }
  }

  return [...groups.entries()];
}

export function CopyCard({ copy, className }: CopyCardProps) {
  if (!copy || copy.length === 0) {
    return (
      <EmptyState
        className={className}
        title="No copy yet"
        description="The Copywriter agent has not produced copy for this version."
      />
    );
  }

  const groups = groupByChannel(copy);
  const variantLabel = copy.length === 1 ? "variant" : "variants";
  const channelLabel = groups.length === 1 ? "channel" : "channels";

  return (
    <section
      aria-label="Advertising copy"
      className={cn(
        "flex flex-col gap-lg rounded-xl border border-border bg-card p-lg",
        className,
      )}
    >
      <header className="flex flex-col gap-2xs">
        <p className="text-2xs font-medium tracking-wider text-muted-foreground uppercase">
          Copy
        </p>
        <h2 className="text-xl font-semibold tracking-tight">Copy variants</h2>
        <p className="text-sm text-muted-foreground">
          {copy.length} {variantLabel} across {groups.length} {channelLabel}
        </p>
      </header>

      <div className="flex flex-col gap-lg">
        {groups.map(([channel, variants]) => (
          <section
            key={channel}
            aria-label={`${channel} copy`}
            className="flex flex-col gap-sm"
          >
            <h3 className="text-sm font-medium text-foreground">{channel}</h3>
            <ol className="flex flex-col gap-sm">
              {variants.map((variant, index) => (
                <li
                  key={`${variant.headline}-${index}`}
                  className="flex flex-col gap-2xs rounded-lg border border-border/70 bg-background/60 p-md"
                >
                  <p className="text-base font-medium text-foreground">
                    {variant.headline}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {variant.description}
                  </p>
                  <p className="text-2xs font-medium tracking-wider text-brand uppercase">
                    CTA: {variant.cta}
                  </p>
                </li>
              ))}
            </ol>
          </section>
        ))}
      </div>
    </section>
  );
}
