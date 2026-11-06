import { buildScriptedRun, revisionDiff, revisedPackage } from "./fixtures";
import type { MockApiStore } from "./store";

function diffKey(campaign: string, from: number, to: number): string {
  return `${campaign}:${from}:${to}`;
}

export function approveMockRun(store: MockApiStore, id: string) {
  const run = store.runs.get(id);
  if (!run) return undefined;
  const campaign = store.campaigns.get(run.campaign_id);
  if (!campaign) return undefined;

  run.status = "completed";
  campaign.status = "completed";
  campaign.active_run_id = null;
  campaign.updated_at = new Date().toISOString();

  const versions = store.versions.get(run.campaign_id) ?? [];
  const current =
    versions.find((version) => version.run_id === run.id) ?? versions.at(-1);

  return {
    status: "completed" as const,
    version: current?.summary.version ?? campaign.latest_version ?? 1,
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
  const nextVersion = previous.summary.version + 1;
  const newRunId = crypto.randomUUID();
  const now = new Date().toISOString();

  versions.push({
    id: crypto.randomUUID(),
    summary: {
      version: nextVersion,
      parent_version_id: previous.id,
      created_at: now,
      score: revisedPackage.score.total,
    },
    package: revisedPackage,
    run_id: newRunId,
  });
  store.diffs.set(diffKey(campaign.id, previous.summary.version, nextVersion), {
    ...revisionDiff,
    from: previous.summary.version,
    to: nextVersion,
  });
  store.runs.set(newRunId, {
    id: newRunId,
    campaign_id: campaign.id,
    status: "awaiting_approval",
    events: buildScriptedRun(newRunId, nextVersion),
  });

  campaign.latest_version = nextVersion;
  campaign.latest_score = revisedPackage.score.total;
  campaign.status = "awaiting_approval";
  campaign.active_run_id = newRunId;
  campaign.updated_at = now;
  run.status = "completed";

  return {
    run_id: newRunId,
    version: nextVersion,
  };
}
