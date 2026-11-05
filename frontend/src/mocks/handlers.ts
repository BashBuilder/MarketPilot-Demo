import { http, HttpResponse } from "msw";
import {
  approveRunRequest,
  createCampaignRequest,
  reviseRunRequest,
} from "@/lib/schemas";
import { serializeSse } from "./fixtures";
import { approveMockRun, reviseMockRun } from "./run-actions";
import { mockStore } from "./store";

function fail(status: number, code: string, message: string, details?: unknown) {
  return HttpResponse.json({ error: { code, message, details } }, { status });
}

async function readBody(request: Request): Promise<unknown> {
  try {
    return await request.json();
  } catch {
    return undefined;
  }
}

function numericParam(value: string | readonly string[] | undefined): number {
  const parsed = Number(Array.isArray(value) ? value[0] : value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : Number.NaN;
}

export const handlers = [
  http.get("*/health", () => HttpResponse.json({ status: "ok" })),

  http.get("*/api/v1/campaigns", () =>
    HttpResponse.json(mockStore.listCampaigns()),
  ),

  http.post("*/api/v1/campaigns", async ({ request }) => {
    const parsed = createCampaignRequest.safeParse(await readBody(request));
    if (!parsed.success) {
      return fail(422, "validation_error", "Invalid campaign idea", parsed.error.issues);
    }
    return HttpResponse.json(mockStore.createCampaign(parsed.data.idea), {
      status: 201,
    });
  }),

  http.get("*/api/v1/campaigns/:id", ({ params }) => {
    const campaign = mockStore.getCampaign(String(params.id));
    if (!campaign) return fail(404, "campaign_not_found", "Campaign not found");
    return HttpResponse.json(campaign);
  }),

  http.get("*/api/v1/campaigns/:id/versions", ({ params }) => {
    const id = String(params.id);
    if (!mockStore.campaigns.has(id)) {
      return fail(404, "campaign_not_found", "Campaign not found");
    }
    return HttpResponse.json(mockStore.listVersions(id));
  }),

  http.get("*/api/v1/campaigns/:id/versions/:version", ({ params }) => {
    const version = mockStore.getVersion(String(params.id), numericParam(params.version));
    if (!version) return fail(404, "version_not_found", "Version not found");
    return HttpResponse.json(version);
  }),

  http.get(
    "*/api/v1/campaigns/:id/versions/:from/diff/:to",
    ({ params }) => {
      const diff = mockStore.getDiff(
        String(params.id),
        numericParam(params.from),
        numericParam(params.to),
      );
      if (!diff) return fail(404, "diff_not_found", "No diff for these versions");
      return HttpResponse.json(diff);
    },
  ),

  http.post("*/api/v1/runs/:runId/approve", async ({ params, request }) => {
    const parsed = approveRunRequest.safeParse(await readBody(request));
    if (!parsed.success) {
      return fail(422, "validation_error", "Invalid approval", parsed.error.issues);
    }
    const result = approveMockRun(mockStore, String(params.runId));
    if (!result) return fail(404, "run_not_found", "Run not found");
    return HttpResponse.json(result);
  }),

  http.post("*/api/v1/runs/:runId/revise", async ({ params, request }) => {
    const parsed = reviseRunRequest.safeParse(await readBody(request));
    if (!parsed.success) {
      return fail(422, "validation_error", "A revision comment is required", parsed.error.issues);
    }
    const result = reviseMockRun(mockStore, String(params.runId));
    if (!result) return fail(404, "run_not_found", "Run not found");
    return HttpResponse.json(result);
  }),

  http.get("*/api/v1/runs/:runId/stream", ({ params }) => {
    const run = mockStore.runs.get(String(params.runId));
    if (!run) return fail(404, "run_not_found", "Run not found");
    return new HttpResponse(serializeSse(run.events), {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  }),

  http.all("*/api/v1/*", () =>
    fail(404, "not_found", "Mock endpoint not found"),
  ),
];
