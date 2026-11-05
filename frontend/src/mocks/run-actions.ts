import { revisionDiff, revisedPackage } from "./fixtures";
import type { MockApiStore } from "./store";

function diffKey(campaign: string, from: number, to: number): string {
  return `${campaign}:${from}:${to}`;
}

export function approveMockRun(store: MockApiStore, id: string) {
  const run = store.runs.get(id);
  if (!run) return undefined;
  const campaign = store.campaigns.get(run.campaign_id);
  if (!campaign) return undefined;

  run.status = "approved";
  campaign.status = "approved";
  campaign.updated_at = new Date().toISOString();

  return {
    run_id: run.id,
    status: "approved" as const,
    version: campaign.latest_version ?? 1,
  };
}

export function reviseMockRun(store: MockApiStore, id: string) {
  const run = store.runs.get(id);
  if (!run) return undefined;
  const campaign = store.campaigns.get(run.campaign_id);
  const versions = store.versions.get(run.campaign_id);
  if (!campaign || !versions) return undefined;

  const previous = versions.at(-1);
  if (!previous) return undefined;
  const nextVersion = previous.version + 1;
  const now = new Date().toISOString();

  versions.push({
    ...previous,
    version: nextVersion,
    parent_version: previous.version,
    created_at: now,
    package: revisedPackage,
  });
  store.diffs.set(diffKey(campaign.id, previous.version, nextVersion), {
    ...revisionDiff,
    from_version: previous.version,
    to_version: nextVersion,
  });
  campaign.latest_version = nextVersion;
  campaign.latest_score = revisedPackage.score.total;
  campaign.status = "awaiting_approval";
  campaign.updated_at = now;
  run.status = "revision_requested";

  return {
    run_id: run.id,
    status: "revision_requested" as const,
    version: nextVersion,
  };
}
