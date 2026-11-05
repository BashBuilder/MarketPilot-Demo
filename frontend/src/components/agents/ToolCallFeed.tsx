import { ChevronDown } from "lucide-react";
import type { ToolCallRecord } from "@/lib/sse/run-state";
import { cn } from "@/lib/utils";
import { agentLabel } from "./agent-meta";
import { formatDuration, formatTimestamp } from "./agent-format";

interface ToolCallFeedProps {
  calls: readonly ToolCallRecord[];
  className?: string;
}

function ToolStatus({ status }: { status: ToolCallRecord["status"] }) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1 text-2xs font-medium",
        status === "success" ? "text-brand" : "text-destructive",
      )}
    >
      <span aria-hidden="true" className="size-1.5 rounded-full bg-current" />
      {status === "success" ? "Success" : "Error"}
    </span>
  );
}

export function ToolCallFeed({ calls, className }: ToolCallFeedProps) {
  return (
    <section
      aria-label="Tool calls"
      aria-live="polite"
      className={cn(
        "overflow-hidden rounded-xl border border-border bg-card",
        className,
      )}
    >
      {calls.length === 0 ? (
        <p className="px-md py-sm text-sm text-muted-foreground">
          No tool calls yet.
        </p>
      ) : (
        <ol className="divide-y divide-border">
          {calls.map((call) => (
            <li key={call.id} data-status={call.status}>
              <details className="group">
                <summary className="flex cursor-pointer list-none items-center gap-sm px-md py-xs transition-colors hover:bg-muted/50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset focus-visible:outline-none [&::-webkit-details-marker]:hidden">
                  <code className="min-w-0 flex-1 truncate font-mono text-xs text-foreground">
                    {call.tool}
                  </code>
                  <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
                    {formatDuration(call.durationMs)}
                  </span>
                  <ToolStatus status={call.status} />
                  <ChevronDown
                    aria-hidden="true"
                    className="size-3.5 shrink-0 text-muted-foreground motion-safe:transition-transform group-open:rotate-180"
                  />
                </summary>

                <dl className="grid gap-x-md gap-y-2xs border-t border-border bg-muted/30 px-md py-sm text-xs sm:grid-cols-2">
                  <div>
                    <dt className="text-muted-foreground">Agent</dt>
                    <dd className="font-medium">{agentLabel(call.agent)}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Duration</dt>
                    <dd className="tabular-nums">{call.durationMs} ms</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Status</dt>
                    <dd>{call.status === "success" ? "Success" : "Error"}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Recorded</dt>
                    <dd>
                      <time dateTime={call.timestamp}>
                        {formatTimestamp(call.timestamp)}
                      </time>
                    </dd>
                  </div>
                </dl>
              </details>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
