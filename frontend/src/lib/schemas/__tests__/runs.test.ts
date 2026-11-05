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

  it("accepts the backend approval response", () => {
    expect(
      approveRunResponse.safeParse({ status: "completed", version: 1 }).success,
    ).toBe(true);
    expect(
      approveRunResponse.safeParse({ status: "approved", version: 1 }).success,
    ).toBe(false);
    expect(approveRunResponse.safeParse({ status: "completed" }).success).toBe(
      false,
    );
  });

  it("accepts the backend revision response", () => {
    const response = {
      run_id: "0f8fad5b-d9cb-469f-a165-70867728950e",
      version: 2,
    };
    expect(reviseRunResponse.safeParse(response).success).toBe(true);
    expect(
      reviseRunResponse.safeParse({ ...response, run_id: undefined }).success,
    ).toBe(false);
    expect(
      reviseRunResponse.safeParse({ ...response, version: 0 }).success,
    ).toBe(false);
  });
});
