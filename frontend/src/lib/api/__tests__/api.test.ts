import { HttpResponse, http } from "msw";
import { setupServer } from "msw/node";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";
import {
  ApiError,
  API_BASE_URL,
  approveRun,
  checkHealth,
  createCampaign,
  getCampaign,
  getVersion,
  getVersionDiff,
  listCampaigns,
  listVersions,
  reviseRun,
} from "@/lib/api";
import { handlers } from "@/mocks/handlers";
import { campaignId, runId } from "@/mocks/fixtures";
import { resetMockStore } from "@/mocks/store";

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterAll(() => server.close());
beforeEach(() => resetMockStore());

describe("API client against the mock API", () => {
  it("lists the seeded campaign and reads its summary", async () => {
    const campaigns = await listCampaigns();
    expect(campaigns).toHaveLength(1);
    expect(campaigns[0].id).toBe(campaignId);

    const detail = await getCampaign(campaignId);
    expect(detail.latest_version).toBe(1);
    expect(detail.active_run_id).toBe(runId);
  });

  it("creates a campaign, then exposes it with version 1", async () => {
    const created = await createCampaign({ idea: "Launch a travel mug" });
    expect(created.campaign_id).not.toBe(campaignId);

    const detail = await getCampaign(created.campaign_id);
    expect(detail.idea).toBe("Launch a travel mug");
    expect(detail.latest_version).toBe(1);
    expect(await listVersions(created.campaign_id)).toHaveLength(1);
  });

  it("reads a full version package", async () => {
    const version = await getVersion(campaignId, 1);
    expect(version.score?.total).toBe(86);
    expect(version.copy?.variants[0].channel).toBe("instagram");
  });

  it("approves a run", async () => {
    const result = await approveRun(runId, { comment: "Ship it" });
    expect(result.status).toBe("completed");
    expect(result.version).toBe(1);
    expect((await getCampaign(campaignId)).status).toBe("completed");
  });

  it("revises a run into version 2 and exposes the new run", async () => {
    const result = await reviseRun(runId, {
      comment: "Sharper hook",
      target_node: "copywriter",
    });
    expect(result.version).toBe(2);
    const versions = await listVersions(campaignId);
    expect(versions).toHaveLength(2);
    expect(versions[1].parent_version_id).not.toBeNull();

    const version = await getVersion(campaignId, 2);
    expect(version.copy?.variants[0].headline).toContain("commute");

    const diff = await getVersionDiff(campaignId, 1, 2);
    expect(diff.changes.length).toBeGreaterThan(0);
    expect(diff.changes[0].path).toContain("copy");
  });

  it("validates the revision comment before sending", async () => {
    await expect(reviseRun(runId, { comment: "  " })).rejects.toThrow();
  });

  it("surfaces a payload that does not match the contract", async () => {
    server.use(
      http.get("*/api/v1/campaigns", () =>
        HttpResponse.json({ campaigns: [] }),
      ),
    );

    const error = await listCampaigns().catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe("invalid_response");
  });

  it("surfaces contract error responses", async () => {
    server.use(
      http.get("*/api/v1/campaigns/:id", () =>
        HttpResponse.json(
          { error: { code: "internal_error", message: "Database unavailable" } },
          { status: 500 },
        ),
      ),
    );

    const error = await getCampaign(campaignId).catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(500);
    expect((error as ApiError).code).toBe("internal_error");
  });

  it("serves the scripted SSE stream", async () => {
    const response = await fetch(`${API_BASE_URL}/runs/${runId}/stream`);
    expect(response.headers.get("content-type")).toContain("text/event-stream");
    const body = await response.text();
    expect(body).toContain("event: validation_failed");
    expect(body).toContain("event: awaiting_approval");
  });

  it("checks health", async () => {
    await expect(checkHealth()).resolves.toBeUndefined();
  });
});
