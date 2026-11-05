"use client";

import { useState } from "react";
import { ErrorState } from "@/components/states/error-state";
import { Button } from "@/components/ui/button";
import type { AgentName } from "@/lib/schemas";
import { ApprovalDialog, type ApprovalMode } from "./ApprovalDialog";

export interface ApprovalPanelProps {
  version: number;
  onApprove: (comment?: string) => void;
  onRevise: (comment: string, targetNode?: AgentName) => void;
  isPending: boolean;
  error?: string | null;
}

export function ApprovalPanel({
  version,
  onApprove,
  onRevise,
  isPending,
  error,
}: ApprovalPanelProps) {
  const [mode, setMode] = useState<ApprovalMode | null>(null);

  function open(next: ApprovalMode) {
    if (isPending) return;
    setMode(next);
  }

  return (
    <section
      aria-labelledby="approval-panel-heading"
      aria-busy={isPending}
      className="rounded-xl border border-brand/40 bg-brand/5 p-lg motion-safe:animate-in motion-safe:fade-in-0"
    >
      <p className="text-2xs font-medium tracking-wider text-brand uppercase">
        Approval
      </p>
      <h2
        id="approval-panel-heading"
        className="mt-2xs text-xl font-semibold tracking-tight"
      >
        Version {version} is ready for review
      </h2>
      <p className="mt-xs max-w-prose text-sm text-muted-foreground">
        Approve the package to finish the run, or request a revision to send it
        back to the agents as a new version.
      </p>

      <div
        role="group"
        aria-label="Review actions"
        className="mt-md flex flex-wrap gap-sm"
      >
        <Button
          type="button"
          disabled={isPending}
          onClick={() => open("approve")}
        >
          {isPending ? "Submitting…" : "Approve"}
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={isPending}
          onClick={() => open("revise")}
        >
          Request revision
        </Button>
      </div>

      {error ? (
        <ErrorState
          title="Could not submit your review"
          description={error}
          headingLevel="h3"
          className="mt-md"
        />
      ) : null}

      {mode ? (
        <ApprovalDialog
          key={mode}
          mode={mode}
          version={version}
          isPending={isPending}
          onOpenChange={(next) => {
            if (!next) setMode(null);
          }}
          onApprove={onApprove}
          onRevise={onRevise}
        />
      ) : null}
    </section>
  );
}
