import type {
  CampaignDetail,
  CampaignSummary,
  CampaignVersion,
  SseEvent,
  VersionDiff,
  VersionSummary,
} from "@/lib/schemas";
import {
  buildScriptedRun,
  campaignId,
  campaignSummary,
  runId,
  versionOne,
} from "./fixtures";

export type MockRunStatus =
  | "running"
  | "awaiting_approval"
  | "approved"
  | "revision_requested";

export interface MockRun {
  id: string;
  campaign_id: string;
  status: MockRunStatus;
  events: SseEvent[];
}

function diffKey(campaign: string, from: number, to: number): string {
  return `${campaign}:${from}:${to}`;
}

export class MockApiStore {
  campaigns = new Map<string, CampaignSummary>();
  versions = new Map<string, CampaignVersion[]>();
  diffs = new Map<string, VersionDiff>();
  runs = new Map<string, MockRun>();

  constructor() {
    this.reset();
  }

  reset(): void {
    this.campaigns = new Map([[campaignId, { ...campaignSummary }]]);
    this.versions = new Map([[campaignId, [versionOne]]]);
    this.diffs = new Map();
    this.runs = new Map([
      [
        runId,
        {
          id: runId,
          campaign_id: campaignId,
          status: "awaiting_approval",
          events: buildScriptedRun(runId, 1),
        },
      ],
    ]);
  }

  listCampaigns(): CampaignSummary[] {
    return Array.from(this.campaigns.values());
  }

  getCampaign(id: string): CampaignDetail | undefined {
    const summary = this.campaigns.get(id);
    if (!summary) return undefined;
    const versions = this.versions.get(id) ?? [];
    return {
      ...summary,
      latest_package: versions.at(-1)?.package ?? null,
    };
  }

  listVersions(id: string): VersionSummary[] {
    return (this.versions.get(id) ?? []).map((version) => ({
      version: version.version,
      parent_version: version.parent_version,
      created_at: version.created_at,
      total_score: version.package.score.total,
      run_status: version.run_status,
    }));
  }

  getVersion(id: string, version: number): CampaignVersion | undefined {
    return this.versions.get(id)?.find((item) => item.version === version);
  }

  getDiff(id: string, from: number, to: number): VersionDiff | undefined {
    return this.diffs.get(diffKey(id, from, to));
  }

  createCampaign(idea: string): { campaign_id: string; run_id: string } {
    const newCampaignId = crypto.randomUUID();
    const newRunId = crypto.randomUUID();
    const now = new Date().toISOString();
    const summary: CampaignSummary = {
      id: newCampaignId,
      idea,
      status: "awaiting_approval",
      latest_version: 1,
      latest_score: versionOne.package.score.total,
      created_at: now,
      updated_at: now,
    };

    this.campaigns.set(newCampaignId, summary);
    this.versions.set(newCampaignId, [
      {
        ...versionOne,
        campaign_id: newCampaignId,
        created_at: now,
        run_id: newRunId,
        run_status: "awaiting_approval",
      },
    ]);
    this.runs.set(newRunId, {
      id: newRunId,
      campaign_id: newCampaignId,
      status: "awaiting_approval",
      events: buildScriptedRun(newRunId, 1),
    });

    return { campaign_id: newCampaignId, run_id: newRunId };
  }
}

export const mockStore = new MockApiStore();

export function resetMockStore(): void {
  mockStore.reset();
}
