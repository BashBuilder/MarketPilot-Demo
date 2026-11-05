import { describe, expect, it } from "vitest";
import {
  approveRunRequest,
  approveRunResponse,
  createCampaignRequest,
  createCampaignResponse,
  reviseRunRequest,
  reviseRunResponse,
} from "@/lib/schemas";

describe("run schemas", () => {
  it("accepts a campaign idea and response", () => {
    expect(
      createCampaignRequest.safeParse({ idea: "Launch a hair-care campaign" })
        .success,
    ).toBe(true);
    expect(
      createCampaignResponse.safeParse({
        campaign_id: "7c9e6679-7425-40de-944b-e07fc1f90ae7",
        run_id: "0f8fad5b-d9cb-469f-a165-70867728950e",
      }).success,
    ).toBe(true);
  });

  it("rejects a blank or oversized idea", () => {
    expect(createCampaignRequest.safeParse({ idea: "   " }).success).toBe(false);
    expect(
      createCampaignRequest.safeParse({ idea: "x".repeat(2001) }).success,
    ).toBe(false);
  });

  it("accepts an optional approval comment", () => {
    expect(approveRunRequest.safeParse({}).success).toBe(true);
    expect(approveRunRequest.safeParse({ comment: "Looks good" }).success).toBe(
      true,
    );
  });

  it("requires a non-empty revision comment", () => {
    expect(reviseRunRequest.safeParse({}).success).toBe(false);
    expect(reviseRunRequest.safeParse({ comment: "  " }).success).toBe(false);
  });

  it("limits the revision target to known agents", () => {
    expect(
      reviseRunRequest.safeParse({ comment: "Sharper hook", target_node: "copywriter" })
        .success,
    ).toBe(true);
    expect(
      reviseRunRequest.safeParse({ comment: "Sharper hook", target_node: "intern" })
        .success,
    ).toBe(false);
  });

  it("accepts the approve response shape", () => {
    const response = {
      run_id: "0f8fad5b-d9cb-469f-a165-70867728950e",
      status: "approved",
      version: 1,
    };
    expect(approveRunResponse.safeParse(response).success).toBe(true);
    expect(
      approveRunResponse.safeParse({
        ...response,
        status: "revision_requested",
      }).success,
    ).toBe(false);
  });

  it("requires a new run id on a revision response", () => {
    const response = {
      run_id: "0f8fad5b-d9cb-469f-a165-70867728950e",
      status: "revision_requested",
      version: 2,
      new_run_id: "5f2c1d3a-8b6e-4f0a-9c7d-2e1b3a4c5d6e",
    };
    expect(reviseRunResponse.safeParse(response).success).toBe(true);
    expect(
      reviseRunResponse.safeParse({ ...response, new_run_id: undefined })
        .success,
    ).toBe(false);
    expect(
      reviseRunResponse.safeParse({ ...response, status: "approved" }).success,
    ).toBe(false);
  });
});
