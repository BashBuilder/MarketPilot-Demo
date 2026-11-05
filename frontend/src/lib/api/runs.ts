import {
  approveRunRequest,
  reviseRunRequest,
  runActionResponse,
  type ApproveRunInput,
  type ReviseRunInput,
} from "@/lib/schemas";
import { apiRequest } from "./client";

export async function approveRun(
  runId: string,
  input: ApproveRunInput = {},
  signal?: AbortSignal,
) {
  return apiRequest(
    `/runs/${encodeURIComponent(runId)}/approve`,
    runActionResponse,
    {
      method: "POST",
      body: approveRunRequest.parse(input),
      signal,
    },
  );
}

export async function reviseRun(
  runId: string,
  input: ReviseRunInput,
  signal?: AbortSignal,
) {
  return apiRequest(
    `/runs/${encodeURIComponent(runId)}/revise`,
    runActionResponse,
    {
      method: "POST",
      body: reviseRunRequest.parse(input),
      signal,
    },
  );
}
