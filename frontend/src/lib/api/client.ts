import { z } from "zod";
import { apiErrorBody } from "@/lib/schemas";

const DEFAULT_BASE_URL = "http://localhost:8000/api/v1";

export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_BASE_URL
).replace(/\/+$/, "");

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function toApiError(status: number, payload: unknown): ApiError {
  const parsed = apiErrorBody.safeParse(payload);
  if (parsed.success) {
    return new ApiError(
      status,
      parsed.data.error.code,
      parsed.data.error.message,
      parsed.data.error.details,
    );
  }
  return new ApiError(status, "http_error", `Request failed with status ${status}`, payload);
}

export interface ApiRequestOptions {
  method?: "GET" | "POST";
  body?: unknown;
  headers?: HeadersInit;
  signal?: AbortSignal;
}

/**
 * The single network boundary for JSON endpoints. Every successful payload is
 * validated so a contract drift becomes a visible error state, never bad UI.
 */
export async function apiRequest<T>(
  path: string,
  schema: z.ZodType<T>,
  options: ApiRequestOptions = {},
): Promise<T> {
  const url = `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(url, {
      method: options.method ?? "GET",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
      cache: "no-store",
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Network request failed";
    throw new ApiError(0, "network_error", message);
  }

  const raw = await response.text();
  let payload: unknown;
  if (raw.length > 0) {
    try {
      payload = JSON.parse(raw);
    } catch {
      throw new ApiError(
        response.status,
        "invalid_response",
        "API response was not valid JSON",
        raw,
      );
    }
  }

  if (!response.ok) {
    throw toApiError(response.status, payload);
  }

  const parsed = schema.safeParse(payload);
  if (!parsed.success) {
    throw new ApiError(
      response.status,
      "invalid_response",
      "API response did not match the expected schema",
      parsed.error.issues,
    );
  }
  return parsed.data;
}
