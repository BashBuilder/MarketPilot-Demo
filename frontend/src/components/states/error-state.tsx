"use client";

import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { StateHeadingLevel } from "./heading-level";

interface ErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
  retryLabel?: string;
  headingLevel?: StateHeadingLevel;
  className?: string;
}

export function ErrorState({
  title = "Something went wrong",
  description,
  onRetry,
  retryLabel = "Try again",
  headingLevel = "h2",
  className,
}: ErrorStateProps) {
  const Heading = headingLevel;

  return (
    <section
      role="alert"
      className={cn(
        "rounded-xl border border-destructive/30 bg-destructive/5 p-lg",
        className,
      )}
    >
      <div className="flex items-start gap-sm">
        <div
          aria-hidden="true"
          className="grid size-9 shrink-0 place-items-center rounded-full bg-destructive/10 text-destructive [&_svg]:size-4"
        >
          <AlertTriangle />
        </div>

        <div className="min-w-0">
          <Heading className="text-base font-semibold tracking-tight">
            {title}
          </Heading>

          {description ? (
            <p className="mt-2xs text-sm text-muted-foreground">
              {description}
            </p>
          ) : null}

          {onRetry ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="mt-sm"
              onClick={onRetry}
            >
              {retryLabel}
            </Button>
          ) : null}
        </div>
      </div>
    </section>
  );
}
