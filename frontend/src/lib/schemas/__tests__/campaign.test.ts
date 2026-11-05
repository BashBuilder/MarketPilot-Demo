import { describe, expect, it } from "vitest";
import {
  campaignList,
  campaignSummary,
  versionDiff,
  versionList,
  versionSummary,
} from "@/lib/schemas";
import {
  campaignSummary as campaignSummaryFixture,
  revisionDiff,
  versionSummaryOne,
} from "@/mocks/fixtures";

describe("campaign schemas", () => {
  it("parses a campaign summary and list", () => {
    expect(campaignSummary.safeParse(campaignSummaryFixture).success).toBe(true);
    expect(campaignList.safeParse([campaignSummaryFixture]).success).toBe(true);
  });

  it("requires the active run id named in the contract", () => {
    const withoutRun: Record<string, unknown> = { ...campaignSummaryFixture };
    delete withoutRun.active_run_id;
    expect(campaignSummary.safeParse(withoutRun).success).toBe(false);
  });

  it("parses version summaries and the version list", () => {
    expect(versionSummary.safeParse(versionSummaryOne).success).toBe(true);
    expect(versionList.safeParse([versionSummaryOne]).success).toBe(true);
  });

  it("requires score and parent identity on a version summary", () => {
    const withoutScore: Record<string, unknown> = { ...versionSummaryOne };
    delete withoutScore.score;
    expect(versionSummary.safeParse(withoutScore).success).toBe(false);

    const withoutParent: Record<string, unknown> = { ...versionSummaryOne };
    delete withoutParent.parent_version_id;
    expect(versionSummary.safeParse(withoutParent).success).toBe(false);
  });

  it("parses a version diff", () => {
    expect(versionDiff.safeParse(revisionDiff).success).toBe(true);
  });

  it("accepts every backend campaign status", () => {
    for (const status of [
      "draft",
      "running",
      "awaiting_approval",
      "completed",
      "failed",
    ]) {
      expect(
        campaignSummary.safeParse({ ...campaignSummaryFixture, status }).success,
      ).toBe(true);
    }
  });

  it("rejects statuses the backend no longer emits", () => {
    for (const status of ["pending", "approved", "revising", "paused"]) {
      expect(
        campaignSummary.safeParse({ ...campaignSummaryFixture, status }).success,
      ).toBe(false);
    }
  });

  it("rejects a non-positive version number", () => {
    expect(
      versionSummary.safeParse({ ...versionSummaryOne, version: 0 }).success,
    ).toBe(false);
  });

  it("rejects a diff change without a path", () => {
    expect(
      versionDiff.safeParse({
        ...revisionDiff,
        changes: [{ before: 1, after: 2 }],
      }).success,
    ).toBe(false);
  });
});
