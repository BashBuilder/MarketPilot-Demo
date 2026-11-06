"use client";

import { AGENT_META } from "@/components/agents/agent-meta";
import { FieldError } from "@/components/ui/field";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { AgentName } from "@/lib/schemas";
import { AGENT_ORDER } from "@/lib/sse/run-state";

export const COMMENT_MAX_LENGTH = 2000;

interface ApprovalFieldsProps {
  isRevise: boolean;
  comment: string;
  targetNode: AgentName | "";
  commentError: string | null;
  disabled: boolean;
  onCommentChange: (comment: string) => void;
  onTargetChange: (targetNode: AgentName | "") => void;
}

export function ApprovalFields({
  isRevise,
  comment,
  targetNode,
  commentError,
  disabled,
  onCommentChange,
  onTargetChange,
}: ApprovalFieldsProps) {
  return (
    <>
      <div className="flex flex-col gap-2">
        <Label htmlFor="approval-comment">
          {isRevise ? "What should change?" : "Comment (optional)"}
        </Label>
        <Textarea
          id="approval-comment"
          value={comment}
          maxLength={COMMENT_MAX_LENGTH}
          required={isRevise}
          disabled={disabled}
          aria-invalid={commentError ? true : undefined}
          aria-describedby={commentError ? "approval-comment-error" : undefined}
          placeholder={
            isRevise
              ? "e.g. The headline makes a claim we cannot support."
              : "Optional note about this package."
          }
          onChange={(event) => onCommentChange(event.target.value)}
        />
        {commentError ? (
          <FieldError id="approval-comment-error">{commentError}</FieldError>
        ) : null}
      </div>

      {isRevise ? (
        <div className="mt-4 flex flex-col gap-2">
          <Label htmlFor="approval-target">Target agent (optional)</Label>
          <select
            id="approval-target"
            value={targetNode}
            disabled={disabled}
            className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-base outline-none transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm dark:bg-input/30"
            onChange={(event) => {
              const next = AGENT_ORDER.find(
                (agent) => agent === event.target.value,
              );
              onTargetChange(next ?? "");
            }}
          >
            <option value="">No specific agent</option>
            {AGENT_ORDER.map((agent) => (
              <option key={agent} value={agent}>
                {AGENT_META[agent].name}
              </option>
            ))}
          </select>
        </div>
      ) : null}
    </>
  );
}
