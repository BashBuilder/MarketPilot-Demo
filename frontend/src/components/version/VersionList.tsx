import Link from "next/link";
import { ChevronRight } from "lucide-react";
import type { VersionSummary } from "@/lib/schemas";

export interface VersionListProps {
  campaignId: string;
  versions: readonly VersionSummary[];
}

export function VersionList({ campaignId, versions }: VersionListProps) {
  const ordered = [...versions].sort((a, b) => b.version - a.version);

  return (
    <ol
      aria-label="Version history"
      className="divide-y divide-border overflow-hidden rounded-xl border border-border bg-card"
    >
      {ordered.map((version) => (
        <li key={version.version}>
          <Link
            href={`/campaigns/${campaignId}/versions/${version.version}`}
            className="group flex items-center justify-between gap-md px-md py-sm transition-colors hover:bg-muted/50 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
          >
            <div className="min-w-0">
              <p className="text-sm font-medium text-foreground">
                Version {version.version}
              </p>
              <p className="mt-3xs text-xs text-muted-foreground">
                <time dateTime={version.created_at}>
                  {version.created_at.slice(0, 10)}
                </time>
                {version.parent_version_id ? " · Revision" : null}
              </p>
            </div>

            <div className="flex shrink-0 items-center gap-sm">
              <div className="flex flex-col items-end gap-1">
                <p className="text-xs text-muted-foreground">
                  {version.score === null
                    ? "No score"
                    : `${version.score} / 100`}
                </p>
              </div>
              <ChevronRight
                aria-hidden="true"
                className="size-4 text-muted-foreground transition-transform motion-safe:group-hover:translate-x-0.5"
              />
            </div>
          </Link>
        </li>
      ))}
    </ol>
  );
}
