import { createCampaignRequest, uuid } from "@/lib/schemas";
import { mockStore } from "@/mocks/store";

const mirrorRequest = createCampaignRequest.extend({
  campaign_id: uuid,
  run_id: uuid,
});

/**
 * Mock-only bridge: the browser MSW worker creates campaigns client-side, but
 * Server Components read from the server mock store. This copies the new
 * campaign across so the review page can render it.
 */
export async function POST(request: Request): Promise<Response> {
  if (process.env.NEXT_PUBLIC_API_MOCKING !== "enabled") {
    return Response.json(
      { error: { code: "not_found", message: "Not found" } },
      { status: 404 },
    );
  }

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    payload = undefined;
  }

  const parsed = mirrorRequest.safeParse(payload);
  if (!parsed.success) {
    return Response.json(
      {
        error: {
          code: "validation_error",
          message: "Invalid mock campaign payload",
        },
      },
      { status: 422 },
    );
  }

  mockStore.importCampaign(parsed.data);
  return new Response(null, { status: 204 });
}
