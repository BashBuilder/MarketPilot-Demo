import type { CreateCampaignResult } from "@/lib/schemas";

const MIRROR_ENDPOINT = "/api/mock/campaigns";

/**
 * The mock API runs in both the browser (MSW worker) and the server (MSW
 * instrumentation). A campaign created in the browser must also exist on the
 * server so Server Components can render its review page.
 */
export async function mirrorCreatedCampaign(
  idea: string,
  created: CreateCampaignResult,
): Promise<void> {
  if (typeof window === "undefined" || !("serviceWorker" in navigator)) {
    return;
  }

  const response = await fetch(MIRROR_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ idea, ...created }),
  });

  if (!response.ok) {
    throw new Error("Could not mirror the mock campaign to the server");
  }
}
