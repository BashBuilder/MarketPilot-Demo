import Link from "next/link";
import { ChevronRight } from "lucide-react";
import type { VersionSummary, WorkflowRunStatus } from "@/lib/schemas";
import { cn } from "@/lib/utils";

const STATUS_META: Record<
  WorkflowRunStatus,
  { label: string; className: string }
> = {
  running: {
    label: "Running",
    className: "border-border bg-muted text-muted-foreground",
  },
  awaiting_approval: {
    label: "Awaiting approval",
    className: "border-brand/40 bg-brand/10 text-brand",
  },
  approved: {
    label: "Approved",
    className: "border-border bg-muted text-foreground",
  },
  revision_requested: {
    label: "Revision requested",
    className: "border-border bg-muted text-muted-foreground",
  },
  failed: {
    label: "Failed",
    className: "border-destructive/30 bg-destructive/5 text-destructive",
  },
};

interface StatusPillProps {
  status: WorkflowRunStatus;
}

function StatusPill({ status }: StatusPillProps) {
  const meta = STATUS_META[status];

  return (
    <span
      data-status={status}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-2xs font-medium",
        meta.className,
      )}
    >
      <span aria-hidden="true" className="size-1.5 rounded-full bg-current" />
      {meta.label}
    </span>
  );
}

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
                {version.parent_version
                  ? ` · Revised from version ${version.parent_version}`
                  : null}
              </p>
            </div>

            <div className="flex shrink-0 items-center gap-sm">
              <div className="flex flex-col items-end gap-1">
                <StatusPill status={version.run_status} />
                <p className="text-xs text-muted-foreground">
                  {version.total_score === null
                    ? "No score"
                    : `${version.total_score} / 100`}
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
