import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { EmptyState } from "@/components/states/empty-state";
import { buttonVariants } from "@/components/ui/button";
import { StatusPill } from "@/components/version/StatusPill";
import type { CampaignSummary, VersionSummary } from "@/lib/schemas";

interface CampaignOverviewProps {
  campaign: CampaignSummary;
  version: VersionSummary | null;
}

interface ActiveRunNoticeProps {
  campaignId: string;
  runId: string;
}

function ActiveRunNotice({ campaignId, runId }: ActiveRunNoticeProps) {
  return (
    <section
      aria-labelledby="active-run-heading"
      className="flex flex-wrap items-center justify-between gap-sm rounded-xl border border-brand/30 bg-brand/5 p-md"
    >
      <div className="flex flex-col gap-2xs">
        <h2
          id="active-run-heading"
          className="text-sm font-semibold tracking-tight"
        >
          Run in progress
        </h2>
        <p className="text-sm text-muted-foreground">
          The agents are still working on a new version.
        </p>
      </div>
      <Link
        href={`/campaigns/${campaignId}/run/${runId}`}
        className={buttonVariants({ variant: "outline", size: "lg" })}
      >
        Open live run
        <ArrowRight aria-hidden="true" />
      </Link>
    </section>
  );
}

interface LatestVersionProps {
  campaignId: string;
  campaignStatus: CampaignSummary["status"];
  version: VersionSummary;
}

function LatestVersion({
  campaignId,
  campaignStatus,
  version,
}: LatestVersionProps) {
  return (
    <section
      aria-labelledby="latest-version-heading"
      className="rounded-xl border border-border bg-card p-lg"
    >
      <div className="flex flex-wrap items-start justify-between gap-md">
        <div className="flex flex-col gap-2xs">
          <p className="text-2xs font-medium tracking-wider text-muted-foreground uppercase">
            Latest version
          </p>
          <h2
            id="latest-version-heading"
            className="text-xl font-semibold tracking-tight"
          >
            Version {version.version}
          </h2>
          <p className="text-sm text-muted-foreground">
            Created{" "}
            <time dateTime={version.created_at}>
              {version.created_at.slice(0, 10)}
            </time>
            {version.parent_version_id ? " · Revision" : null}
          </p>
        </div>

        <div className="flex flex-col items-end gap-xs">
          <StatusPill status={campaignStatus} />
          <p className="text-2xl font-semibold tracking-tight">
            {version.score === null ? "No score" : `${version.score} / 100`}
          </p>
        </div>
      </div>

      <div className="mt-md flex flex-wrap gap-sm">
        <Link
          href={`/campaigns/${campaignId}/versions/${version.version}`}
          className={buttonVariants({ size: "lg" })}
        >
          Review latest version
        </Link>
        <Link
          href={`/campaigns/${campaignId}/versions`}
          className={buttonVariants({ variant: "outline", size: "lg" })}
        >
          Version history
        </Link>
      </div>
    </section>
  );
}

export function CampaignOverview({
  campaign,
  version,
}: CampaignOverviewProps) {
  const activeRun =
    campaign.active_run_id !== null &&
    campaign.status !== "awaiting_approval" &&
    campaign.status !== "completed" &&
    campaign.status !== "failed"
      ? campaign.active_run_id
      : null;

  return (
    <div className="mx-auto flex w-full max-w-[64rem] flex-col gap-lg">
      <header className="flex flex-col gap-2xs">
        <p className="text-2xs font-medium tracking-wider text-muted-foreground uppercase">
          Campaign overview
        </p>
        <h1 className="max-w-[48rem] text-balance text-3xl font-semibold tracking-tight">
          {campaign.idea}
        </h1>
        <p className="text-sm text-muted-foreground">
          Created{" "}
          <time dateTime={campaign.created_at}>
            {campaign.created_at.slice(0, 10)}
          </time>
        </p>
      </header>

      {activeRun ? (
        <ActiveRunNotice campaignId={campaign.id} runId={activeRun} />
      ) : null}

      {version ? (
        <LatestVersion
          campaignId={campaign.id}
          campaignStatus={campaign.status}
          version={version}
        />
      ) : (
        <EmptyState
          title="No version yet"
          description="A package appears here once the agents finish the first run."
          action={
            <Link
              href={`/campaigns/${campaign.id}/versions`}
              className={buttonVariants({ variant: "outline", size: "lg" })}
            >
              Version history
            </Link>
          }
        />
      )}
    </div>
  );
}
