import { z } from "zod";
import { eventActor, isoDateTime, text, uuid } from "./common";

const eventBase = z.object({
  run_id: uuid,
  timestamp: isoDateTime,
  agent: eventActor,
});

export const agentStartedEvent = z.object({
  id: text,
  event: z.literal("agent_started"),
  data: eventBase,
});

export const agentHandoffEvent = z.object({
  id: text,
  event: z.literal("agent_handoff"),
  data: eventBase.extend({
    from: eventActor,
    to: eventActor,
  }),
});

export const toolCalledEvent = z.object({
  id: text,
  event: z.literal("tool_called"),
  data: eventBase.extend({
    tool: text,
    duration_ms: z.number().int().nonnegative(),
    status: z.enum(["success", "error", "denied"]),
  }),
});

export const validationFailedEvent = z.object({
  id: text,
  event: z.literal("validation_failed"),
  data: eventBase.extend({
    reason: text,
  }),
});

export const retryingEvent = z.object({
  id: text,
  event: z.literal("retrying"),
  data: eventBase.extend({
    attempt: z.number().int().positive(),
    max_attempts: z.number().int().positive(),
  }),
});

export const awaitingApprovalEvent = z.object({
  id: text,
  event: z.literal("awaiting_approval"),
  data: eventBase.extend({
    version: z.number().int().positive(),
  }),
});

export const completedEvent = z.object({
  id: text,
  event: z.literal("completed"),
  data: eventBase.extend({
    version: z.number().int().positive(),
    score: z.number().min(0).max(100).nullable(),
  }),
});

export const errorEvent = z.object({
  id: text,
  event: z.literal("error"),
  data: eventBase.extend({
    message: text,
    recoverable: z.boolean(),
  }),
});

export const sseEvent = z.discriminatedUnion("event", [
  agentStartedEvent,
  agentHandoffEvent,
  toolCalledEvent,
  validationFailedEvent,
  retryingEvent,
  awaitingApprovalEvent,
  completedEvent,
  errorEvent,
]);

export type SseEvent = z.infer<typeof sseEvent>;
export type SseEventType = SseEvent["event"];
export type AgentStartedEvent = z.infer<typeof agentStartedEvent>;
export type AgentHandoffEvent = z.infer<typeof agentHandoffEvent>;
export type ToolCalledEvent = z.infer<typeof toolCalledEvent>;
export type ValidationFailedEvent = z.infer<typeof validationFailedEvent>;
export type RetryingEvent = z.infer<typeof retryingEvent>;
export type AwaitingApprovalEvent = z.infer<typeof awaitingApprovalEvent>;
export type CompletedEvent = z.infer<typeof completedEvent>;
export type ErrorEvent = z.infer<typeof errorEvent>;
