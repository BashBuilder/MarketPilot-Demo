import type { AgentName } from "@/lib/schemas";
import type { AgentRunState } from "@/lib/sse/run-state";
import { AGENT_ORDER } from "@/lib/sse/run-state";
import { FailureNotice } from "./FailureNotice";

interface RunFailureListProps {
  agents: Record<AgentName, AgentRunState>;
}

export function RunFailureList({ agents }: RunFailureListProps) {
  const failures = AGENT_ORDER.flatMap((agent) => {
    const agentState = agents[agent];
    const validationFailures = agentState.validationFailures.map(
      (reason, index) => (
        <FailureNotice
          key={`${agent}-validation-${index}`}
          kind="validation_failed"
          agent={agent}
          reason={reason}
        />
      ),
    );

    if (agentState.status !== "retrying") {
      return validationFailures;
    }

    return [
      ...validationFailures,
      <FailureNotice
        key={`${agent}-retrying`}
        kind="retrying"
        agent={agent}
        attempt={agentState.attempt}
        maxAttempts={agentState.maxAttempts}
      />,
    ];
  });

  if (failures.length === 0) {
    return null;
  }

  return (
    <section aria-label="Run failures" className="flex flex-col gap-xs">
      <h2 className="text-sm font-medium">Failures and retries</h2>
      {failures}
    </section>
  );
}
