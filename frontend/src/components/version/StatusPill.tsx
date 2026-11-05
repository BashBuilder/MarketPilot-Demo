import type { WorkflowRunStatus } from "@/lib/schemas";
import { cn } from "@/lib/utils";

const STATUS_META: Record<
  WorkflowRunStatus,
  { label: string; className: string }
> = {
  running: {
    label: "Running",
    className: "border-brand/40 bg-brand/10 text-brand",
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

export function StatusPill({ status }: StatusPillProps) {
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
