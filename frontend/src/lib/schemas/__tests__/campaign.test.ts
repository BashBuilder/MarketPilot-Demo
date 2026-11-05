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

  it("parses a version diff", () => {
    expect(versionDiff.safeParse(revisionDiff).success).toBe(true);
  });

  it("rejects an unknown campaign status", () => {
    expect(
      campaignSummary.safeParse({ ...campaignSummaryFixture, status: "paused" })
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
