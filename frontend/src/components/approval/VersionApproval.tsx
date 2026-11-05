"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApprovalPanel } from "@/components/approval/ApprovalPanel";
import { ApiError, approveRun, reviseRun } from "@/lib/api";
import type { AgentName, WorkflowRunStatus } from "@/lib/schemas";

interface VersionApprovalProps {
  campaignId: string;
  version: number;
  runId: string;
  runStatus: WorkflowRunStatus;
}

function errorMessage(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : "An unexpected error occurred while submitting your review.";
}

export function VersionApproval({
  campaignId,
  version,
  runId,
  runStatus,
}: VersionApprovalProps) {
  const router = useRouter();
  const [approved, setApproved] = useState(runStatus === "approved");
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleApprove(comment?: string) {
    setIsPending(true);
    setError(null);
    try {
      await approveRun(runId, { comment });
      setApproved(true);
      router.refresh();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setIsPending(false);
    }
  }

  async function handleRevise(comment: string, targetNode?: AgentName) {
    setIsPending(true);
    setError(null);
    try {
      const result = await reviseRun(runId, {
        comment,
        target_node: targetNode,
      });
      // Stay pending while the new run page loads, so the action cannot repeat.
      router.push(`/campaigns/${campaignId}/run/${result.new_run_id}`);
    } catch (caught) {
      setError(errorMessage(caught));
      setIsPending(false);
    }
  }

  if (approved) {
    return (
      <section
        role="status"
        aria-live="polite"
        className="rounded-xl border border-brand/40 bg-brand/5 p-lg"
      >
        <p className="text-2xs font-medium tracking-wider text-brand uppercase">
          Approved
        </p>
        <h2 className="mt-2xs text-xl font-semibold tracking-tight">
          Version {version} approved
        </h2>
        <p className="mt-xs text-sm text-muted-foreground">
          This package is final. The campaign and version records are being
          refreshed.
        </p>
      </section>
    );
  }

  if (runStatus !== "awaiting_approval") {
    return null;
  }

  return (
    <ApprovalPanel
      version={version}
      onApprove={handleApprove}
      onRevise={handleRevise}
      isPending={isPending}
      error={error}
    />
  );
}
