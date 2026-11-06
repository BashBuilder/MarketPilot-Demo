import {
  approveRunRequest,
  approveRunResponse,
  reviseRunRequest,
  reviseRunResponse,
  type ApproveRunInput,
  type ApproveRunResult,
  type ReviseRunInput,
  type ReviseRunResult,
} from "@/lib/schemas";
import { apiRequest } from "./client";

export async function approveRun(
  runId: string,
  input: ApproveRunInput = {},
  signal?: AbortSignal,
): Promise<ApproveRunResult> {
  return apiRequest(
    `/runs/${encodeURIComponent(runId)}/approve`,
    approveRunResponse,
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
): Promise<ReviseRunResult> {
  return apiRequest(
    `/runs/${encodeURIComponent(runId)}/revise`,
    reviseRunResponse,
    {
      method: "POST",
      body: reviseRunRequest.parse(input),
      signal,
    },
  );
}
