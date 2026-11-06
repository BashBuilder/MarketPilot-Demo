import Link from "next/link";
import { ChevronRight } from "lucide-react";
import type { CampaignStatus, CampaignSummary } from "@/lib/schemas";
import { cn } from "@/lib/utils";

const STATUS_META: Record<
  CampaignStatus,
  { label: string; className: string }
> = {
  draft: {
    label: "Draft",
    className: "border-border bg-muted text-muted-foreground",
  },
  running: {
    label: "Running",
    className: "border-brand/40 bg-brand/10 text-brand",
  },
  awaiting_approval: {
    label: "Awaiting approval",
    className: "border-brand/40 bg-brand/10 text-brand",
  },
  completed: {
    label: "Completed",
    className: "border-border bg-muted text-foreground",
  },
  failed: {
    label: "Failed",
    className: "border-destructive/30 bg-destructive/5 text-destructive",
  },
};

interface StatusPillProps {
  status: CampaignStatus;
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

export interface CampaignCardProps {
  campaign: CampaignSummary;
}

export function CampaignCard({ campaign }: CampaignCardProps) {
  return (
    <li>
      <Link
        href={`/campaigns/${campaign.id}`}
        className="group flex h-full items-start justify-between gap-md rounded-xl border border-border bg-card p-md transition-colors hover:bg-muted/50 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
      >
        <div className="flex min-w-0 flex-1 flex-col gap-xs">
          <p className="line-clamp-2 text-sm font-medium text-foreground">
            {campaign.idea}
          </p>
          <p className="text-xs text-muted-foreground">
            Updated{" "}
            <time dateTime={campaign.updated_at}>
              {campaign.updated_at.slice(0, 10)}
            </time>
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-sm">
          <div className="flex flex-col items-end gap-1">
            <StatusPill status={campaign.status} />
            <div className="text-right">
              <p className="text-2xs tracking-wider text-muted-foreground uppercase">
                Latest score
              </p>
              <p className="text-sm font-medium text-foreground">
                {campaign.latest_score === null
                  ? "No score yet"
                  : `${campaign.latest_score} / 100`}
              </p>
            </div>
          </div>
          <ChevronRight
            aria-hidden="true"
            className="size-4 text-muted-foreground transition-transform motion-safe:group-hover:translate-x-0.5"
          />
        </div>
      </Link>
    </li>
  );
}
