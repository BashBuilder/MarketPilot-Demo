import { API_BASE_URL, ApiError } from "./client";

/** `GET /health` is served from the API origin, not the versioned base path. */
export async function checkHealth(signal?: AbortSignal): Promise<void> {
  const url = new URL("/health", API_BASE_URL).toString();

  let response: Response;
  try {
    response = await fetch(url, { signal, cache: "no-store" });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Network request failed";
    throw new ApiError(0, "network_error", message);
  }

  if (!response.ok) {
    throw new ApiError(
      response.status,
      "health_check_failed",
      `Health check failed with status ${response.status}`,
    );
  }
}
