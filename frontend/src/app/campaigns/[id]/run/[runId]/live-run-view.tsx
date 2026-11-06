"use client";

import { Loader2 } from "lucide-react";
import { AgentTimeline } from "@/components/agents/AgentTimeline";
import { HandoffNote } from "@/components/agents/HandoffNote";
import { RunApprovalPrompt } from "@/components/agents/RunApprovalPrompt";
import { RunFailureList } from "@/components/agents/RunFailureList";
import { ToolCallFeed } from "@/components/agents/ToolCallFeed";
import { agentLabel } from "@/components/agents/agent-meta";
import { EmptyState } from "@/components/states/empty-state";
import { ErrorState } from "@/components/states/error-state";
import { Button } from "@/components/ui/button";
import type { RunStatus } from "@/lib/sse/run-state";
import { useRunStream } from "@/lib/sse/useRunStream";

interface LiveRunViewProps {
  campaignId: string;
  runId: string;
  /** Optional override for tests; production uses the stream default. */
  stallAfterMs?: number;
}

const HEADLINES: Record<RunStatus, string> = {
  idle: "Waiting for the run to start",
  running: "Agents are working",
  awaiting_approval: "Ready for your review",
  completed: "Run complete",
  failed: "Run ended with an error",
};

export function LiveRunView({
  campaignId,
  runId,
  stallAfterMs,
}: LiveRunViewProps) {
  const { state, status, stalled } = useRunStream(runId, { stallAfterMs });
  const connecting = status === "connecting" || status === "reconnecting";
  const fatalErrors = state.errors.filter((error) => !error.recoverable);

  return (
    <section className="mx-auto flex w-full max-w-[56rem] flex-col gap-lg">
      <header className="flex flex-col gap-2xs">
        <p className="text-2xs font-medium tracking-wider text-muted-foreground uppercase">
          Live run
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">
          {HEADLINES[state.status]}
        </h1>
        <p className="text-sm text-muted-foreground">
          Campaign{" "}
          <span className="font-mono text-xs break-all text-foreground">
            {campaignId}
          </span>{" "}
          · Run{" "}
          <span className="font-mono text-xs break-all text-foreground">
            {runId}
          </span>
        </p>
      </header>

      {connecting ? (
        <p
          role="status"
          className="flex items-center gap-xs rounded-lg border border-border bg-muted/50 px-sm py-xs text-xs text-muted-foreground"
        >
          <Loader2
            aria-hidden="true"
            className="size-3.5 shrink-0 motion-safe:animate-spin"
          />
          {status === "reconnecting"
            ? "Reconnecting to the live stream…"
            : "Connecting to the live stream…"}
        </p>
      ) : null}

      {stalled ? (
        <div role="status">
          <EmptyState
            title="No progress yet"
            description="The run is connected but has not sent an update for a while. Long model calls can stay quiet, so this is not treated as a failure. Reload to check the latest state."
            action={
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => window.location.reload()}
              >
                Reload run
              </Button>
            }
          />
        </div>
      ) : null}

      {fatalErrors.length > 0 || state.status === "failed" ? (
        <ErrorState
          title="The run stopped"
          description={
            fatalErrors.length > 0
              ? fatalErrors
                  .map((error) => `${agentLabel(error.agent)}: ${error.message}`)
                  .join(" ")
              : "The stream ended with an unrecoverable error. Reload the run to try again."
          }
          retryLabel="Reload run"
          onRetry={() => window.location.reload()}
        />
      ) : null}

      {state.malformedEvents.length > 0 ? (
        <ErrorState
          title="Some stream data could not be read"
          description={`${state.malformedEvents.length} event${
            state.malformedEvents.length === 1 ? "" : "s"
          } were skipped, so this view may be incomplete.`}
        />
      ) : null}

      {state.status === "awaiting_approval" && state.version !== null ? (
        <RunApprovalPrompt campaignId={campaignId} version={state.version} />
      ) : null}

      <section aria-label="Agent progress" className="flex flex-col gap-xs">
        <h2 className="text-sm font-medium">Agents</h2>
        <AgentTimeline agents={state.agents} />
      </section>

      <RunFailureList agents={state.agents} />

      {state.handoffs.length > 0 ? (
        <section aria-label="Handoffs" className="flex flex-col gap-xs">
          <h2 className="text-sm font-medium">Handoffs</h2>
          <ol className="flex flex-col gap-2xs">
            {state.handoffs.map((handoff) => (
              <li key={handoff.id}>
                <HandoffNote handoff={handoff} />
              </li>
            ))}
          </ol>
        </section>
      ) : null}

      <ToolCallFeed calls={state.toolCalls} />
    </section>
  );
}
