import { cn } from "@/lib/utils";
import type { AgentStatus } from "@/lib/sse/run-state";

interface StatusBadgeProps {
  status: AgentStatus;
  attempt?: number;
  maxAttempts?: number;
  className?: string;
}

const statusLabels: Record<AgentStatus, string> = {
  waiting: "Waiting",
  running: "Running",
  retrying: "Retrying",
  failed: "Failed",
  done: "Done",
};

const statusStyles: Record<AgentStatus, string> = {
  waiting: "border-border bg-muted text-muted-foreground",
  running: "border-brand/30 bg-brand/10 text-brand",
  retrying: "border-accent-foreground/20 bg-accent text-accent-foreground",
  failed: "border-destructive/30 bg-destructive/10 text-destructive",
  done: "border-border bg-card text-foreground",
};

function badgeLabel(
  status: AgentStatus,
  attempt: number | undefined,
  maxAttempts: number | undefined,
): string {
  if (status !== "retrying" || !attempt || attempt < 1) {
    return statusLabels[status];
  }

  return maxAttempts
    ? `Retrying · attempt ${attempt} of ${maxAttempts}`
    : `Retrying · attempt ${attempt}`;
}

export function StatusBadge({
  status,
  attempt,
  maxAttempts,
  className,
}: StatusBadgeProps) {
  const pulsing = status === "running" || status === "retrying";

  return (
    <span
      data-status={status}
      className={cn(
        "inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2 py-0.5 text-2xs font-medium tracking-wide whitespace-nowrap motion-safe:animate-in motion-safe:fade-in-0 motion-safe:duration-200 motion-safe:ease-out",
        statusStyles[status],
        className,
      )}
    >
      <span
        aria-hidden="true"
        className={cn(
          "size-1.5 rounded-full bg-current",
          pulsing && "motion-safe:animate-pulse",
        )}
      />
      {badgeLabel(status, attempt, maxAttempts)}
    </span>
  );
}
