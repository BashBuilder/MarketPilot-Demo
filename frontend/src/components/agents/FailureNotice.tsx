import { AlertTriangle, RotateCw } from "lucide-react";
import type { AgentName } from "@/lib/schemas";
import { cn } from "@/lib/utils";
import { agentLabel } from "./agent-meta";
import { formatTimestamp } from "./agent-format";

interface FailureNoticeBase {
  agent: AgentName;
  timestamp?: string;
  className?: string;
}

type FailureNoticeProps =
  | (FailureNoticeBase & {
      kind: "validation_failed";
      reason: string;
      attempt?: number;
      maxAttempts?: number;
    })
  | (FailureNoticeBase & {
      kind: "retrying";
      attempt: number;
      maxAttempts: number;
      reason?: string;
    });

export function FailureNotice(props: FailureNoticeProps) {
  const { agent, timestamp, className } = props;
  const retrying = props.kind === "retrying";
  const Icon = retrying ? RotateCw : AlertTriangle;
  const title = retrying
    ? `Retrying ${agentLabel(agent)}`
    : `Validation failed · ${agentLabel(agent)}`;
  const attemptLabel =
    props.attempt !== undefined && props.maxAttempts !== undefined
      ? `Attempt ${props.attempt} of ${props.maxAttempts}`
      : null;

  return (
    <section
      role="status"
      aria-label={attemptLabel ? `${title}, ${attemptLabel}` : title}
      data-kind={props.kind}
      className={cn(
        "rounded-lg border p-sm motion-safe:animate-in motion-safe:fade-in-0 motion-safe:duration-200",
        retrying
          ? "border-brand/30 bg-brand/5"
          : "border-destructive/30 bg-destructive/5",
        className,
      )}
    >
      <div className="flex items-start gap-xs">
        <Icon
          aria-hidden="true"
          className={cn(
            "mt-0.5 size-3.5 shrink-0",
            retrying ? "text-brand" : "text-destructive",
          )}
        />

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-xs gap-y-1">
            <p
              className={cn(
                "text-xs font-medium",
                retrying ? "text-brand" : "text-destructive",
              )}
            >
              {title}
            </p>

            {attemptLabel ? (
              <span className="rounded-full border border-border bg-background px-1.5 py-0.5 text-2xs font-medium tabular-nums text-muted-foreground">
                {attemptLabel}
              </span>
            ) : null}

            {timestamp ? (
              <time
                dateTime={timestamp}
                className="ml-auto text-2xs tabular-nums text-muted-foreground"
              >
                {formatTimestamp(timestamp)}
              </time>
            ) : null}
          </div>

          {props.reason ? (
            <p className="mt-2xs text-xs text-muted-foreground">
              {props.reason}
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}
