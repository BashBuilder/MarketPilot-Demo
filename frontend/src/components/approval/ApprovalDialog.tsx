"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { AgentName } from "@/lib/schemas";
import { ApprovalFields } from "./ApprovalFields";

export type ApprovalMode = "approve" | "revise";

export interface ApprovalDialogProps {
  mode: ApprovalMode;
  version: number;
  isPending: boolean;
  onOpenChange: (open: boolean) => void;
  onApprove: (comment?: string) => void;
  onRevise: (comment: string, targetNode?: AgentName) => void;
}

export function ApprovalDialog({
  mode,
  version,
  isPending,
  onOpenChange,
  onApprove,
  onRevise,
}: ApprovalDialogProps) {
  const [comment, setComment] = useState("");
  const [targetNode, setTargetNode] = useState<AgentName | "">("");
  const [commentError, setCommentError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  function handleOpenChange(next: boolean) {
    if (!next && isPending) return;
    onOpenChange(next);
  }

  function handleConfirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitted || isPending) return;

    const trimmed = comment.trim();

    if (mode === "revise" && !trimmed) {
      setCommentError("Describe what should change before requesting a revision.");
      return;
    }

    setCommentError(null);
    setSubmitted(true);

    if (mode === "revise") {
      onRevise(trimmed, targetNode || undefined);
    } else {
      onApprove(trimmed || undefined);
    }

    onOpenChange(false);
  }

  const isRevise = mode === "revise";
  const controlsDisabled = isPending || submitted;

  return (
    <Dialog open onOpenChange={handleOpenChange}>
      <DialogContent showCloseButton={!controlsDisabled}>
        <DialogHeader>
          <DialogTitle>
            {isRevise
              ? `Request a revision for version ${version}`
              : `Approve version ${version}?`}
          </DialogTitle>
          <DialogDescription>
            {isRevise
              ? "Tell the agents what to change. A new version will be created and the current one stays intact."
              : "This records your approval and finishes the run. You can leave an optional note for the team."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleConfirm} noValidate>
          <ApprovalFields
            isRevise={isRevise}
            comment={comment}
            targetNode={targetNode}
            commentError={commentError}
            disabled={controlsDisabled}
            onCommentChange={(next) => {
              setComment(next);
              if (commentError) setCommentError(null);
            }}
            onTargetChange={setTargetNode}
          />

          <DialogFooter className="mt-4">
            <Button
              type="button"
              variant="outline"
              disabled={controlsDisabled}
              onClick={() => handleOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={controlsDisabled}>
              {isRevise ? "Request revision" : `Approve version ${version}`}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
