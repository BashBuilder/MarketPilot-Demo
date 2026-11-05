import type { AgentName } from "@/lib/schemas";
import type { AgentRunState } from "@/lib/sse/run-state";
import { AGENT_ORDER } from "@/lib/sse/run-state";
import { cn } from "@/lib/utils";
import { AGENT_META } from "./agent-meta";
import { StatusBadge } from "./StatusBadge";

interface AgentTimelineProps {
  agents: Record<AgentName, AgentRunState>;
  className?: string;
}

export function AgentTimeline({ agents, className }: AgentTimelineProps) {
  return (
    <ol
      aria-label="Agent pipeline"
      aria-live="polite"
      className={cn(
        "divide-y divide-border overflow-hidden rounded-xl border border-border bg-card",
        className,
      )}
    >
      {AGENT_ORDER.map((agent) => {
        const copy = AGENT_META[agent];
        const state = agents[agent];

        return (
          <li
            key={agent}
            data-agent={agent}
            data-status={state.status}
            className="flex items-center justify-between gap-sm px-md py-sm motion-safe:transition-colors"
          >
            <div className="min-w-0">
              <p className="text-sm font-medium text-foreground">{copy.name}</p>
              <p className="text-xs text-muted-foreground">
                {copy.description}
              </p>
            </div>

            <StatusBadge
              // Remount on status change so the fade-in runs again.
              key={state.status}
              status={state.status}
              attempt={state.attempt}
              maxAttempts={state.maxAttempts}
            />
          </li>
        );
      })}
    </ol>
  );
}
