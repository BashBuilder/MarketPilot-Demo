import { ArrowRight } from "lucide-react";
import type { HandoffRecord } from "@/lib/sse/run-state";
import { cn } from "@/lib/utils";
import { agentLabel } from "./agent-meta";
import { formatTimestamp } from "./agent-format";

interface HandoffNoteProps {
  handoff: HandoffRecord;
  className?: string;
}

export function HandoffNote({ handoff, className }: HandoffNoteProps) {
  return (
    <div
      data-agent-from={handoff.from}
      data-agent-to={handoff.to}
      className={cn(
        "flex flex-wrap items-center gap-x-2xs gap-y-1 rounded-lg border border-border bg-card px-sm py-xs text-xs motion-safe:animate-in motion-safe:fade-in-0 motion-safe:duration-200",
        className,
      )}
    >
      <span className="font-medium text-foreground">
        {agentLabel(handoff.from)}
      </span>{" "}
      <span className="sr-only">handed off to</span>{" "}
      <ArrowRight
        aria-hidden="true"
        className="size-3 shrink-0 text-muted-foreground"
      />
      <span className="font-medium text-foreground">
        {agentLabel(handoff.to)}
      </span>
      <time
        dateTime={handoff.timestamp}
        className="ml-auto text-2xs tabular-nums text-muted-foreground"
      >
        {formatTimestamp(handoff.timestamp)}
      </time>
    </div>
  );
}
