import { describe, expect, it } from "vitest";
import {
  campaignDetail,
  campaignList,
  campaignSummary,
  campaignVersion,
  versionDiff,
  versionList,
  versionSummary,
} from "@/lib/schemas";
import {
  campaignDetail as campaignDetailFixture,
  campaignSummary as campaignSummaryFixture,
  revisionDiff,
  versionOne,
  versionSummaryOne,
} from "@/mocks/fixtures";

describe("campaign schemas", () => {
  it("parses a campaign summary and list", () => {
    expect(campaignSummary.safeParse(campaignSummaryFixture).success).toBe(true);
    expect(campaignList.safeParse([campaignSummaryFixture]).success).toBe(true);
  });

  it("parses a campaign detail with its latest package", () => {
    expect(campaignDetail.safeParse(campaignDetailFixture).success).toBe(true);
  });

  it("parses version summaries and a full version", () => {
    expect(versionSummary.safeParse(versionSummaryOne).success).toBe(true);
    expect(versionList.safeParse([versionSummaryOne]).success).toBe(true);
    expect(campaignVersion.safeParse(versionOne).success).toBe(true);
  });

  it("rejects a version without run identity or with an unknown run status", () => {
    expect(
      campaignVersion.safeParse({ ...versionOne, run_id: undefined }).success,
    ).toBe(false);
    expect(
      campaignVersion.safeParse({ ...versionOne, run_status: "paused" }).success,
    ).toBe(false);
    expect(
      versionSummary.safeParse({ ...versionSummaryOne, run_status: undefined })
        .success,
    ).toBe(false);
  });

  it("parses a version diff", () => {
    expect(versionDiff.safeParse(revisionDiff).success).toBe(true);
  });

  it("accepts every backend workflow status", () => {
    for (const status of [
      "pending",
      "running",
      "awaiting_approval",
      "approved",
      "revising",
      "completed",
      "failed",
    ]) {
      expect(
        campaignSummary.safeParse({ ...campaignSummaryFixture, status }).success,
      ).toBe(true);
    }
  });

  it("rejects an unknown campaign status", () => {
    expect(
      campaignSummary.safeParse({ ...campaignSummaryFixture, status: "paused" })
        .success,
    ).toBe(false);
    expect(
      campaignSummary.safeParse({ ...campaignSummaryFixture, status: "draft" })
        .success,
    ).toBe(false);
  });

  it("rejects a non-positive version number", () => {
    expect(
      campaignVersion.safeParse({ ...versionOne, version: 0 }).success,
    ).toBe(false);
  });

  it("rejects a diff change without a field", () => {
    expect(
      versionDiff.safeParse({
        ...revisionDiff,
        changes: [{ before: 1, after: 2 }],
      }).success,
    ).toBe(false);
  });

  it("rejects a detail whose package is malformed", () => {
    expect(
      campaignDetail.safeParse({
        ...campaignDetailFixture,
        latest_package: { brief: {} },
      }).success,
    ).toBe(false);
  });
});
