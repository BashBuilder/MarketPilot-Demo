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

export interface ImportCampaignInput {
  campaign_id: string;
  run_id: string;
  idea: string;
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
    const campaign_id = crypto.randomUUID();
    const run_id = crypto.randomUUID();

    this.addCampaign({ campaign_id, run_id, idea });

    return { campaign_id, run_id };
  }

  /**
   * Adds a campaign created in the browser mock to the server mock. The review
   * page is rendered on the server, so it can only see campaigns mirrored here.
   */
  importCampaign(input: ImportCampaignInput): void {
    if (this.campaigns.has(input.campaign_id)) return;
    this.addCampaign(input);
  }

  private addCampaign({
    campaign_id,
    run_id,
    idea,
  }: ImportCampaignInput): void {
    const now = new Date().toISOString();
    const summary: CampaignSummary = {
      id: campaign_id,
      idea,
      status: "awaiting_approval",
      latest_version: 1,
      latest_score: versionOne.package.score.total,
      created_at: now,
      updated_at: now,
    };

    this.campaigns.set(campaign_id, summary);
    this.versions.set(campaign_id, [
      {
        ...versionOne,
        campaign_id,
        created_at: now,
        run_id,
        run_status: "awaiting_approval",
      },
    ]);
    this.runs.set(run_id, {
      id: run_id,
      campaign_id,
      status: "awaiting_approval",
      events: buildScriptedRun(run_id, 1),
    });
  }
}

// Next bundles instrumentation and route handlers separately; a process-wide
// singleton keeps the server mock store shared between them.
const globalForMock = globalThis as typeof globalThis & {
  __marketpilotMockStore?: MockApiStore;
};

export const mockStore =
  globalForMock.__marketpilotMockStore ?? new MockApiStore();
globalForMock.__marketpilotMockStore = mockStore;

export function resetMockStore(): void {
  mockStore.reset();
}
