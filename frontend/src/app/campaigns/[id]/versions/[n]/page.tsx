import Link from "next/link";
import { AssetGrid } from "@/components/campaign/AssetGrid";
import { BriefCard } from "@/components/campaign/BriefCard";
import { ComplianceReport } from "@/components/campaign/ComplianceReport";
import { CopyCard } from "@/components/campaign/CopyCard";
import { ResearchCard } from "@/components/campaign/ResearchCard";
import { ScoreBreakdown } from "@/components/score/ScoreBreakdown";
import { EmptyState } from "@/components/states/empty-state";
import { ErrorState } from "@/components/states/error-state";
import { VersionApproval } from "@/components/approval/VersionApproval";
import { ApiError, getCampaign, getVersion, listVersions } from "@/lib/api";
import type {
  CampaignPackage,
  CampaignSummary,
  VersionSummary,
} from "@/lib/schemas";

export const instant = false;

interface VersionPageProps {
  params: Promise<{ id: string; n: string }>;
}

function parseVersionParam(value: string): number | null {
  const version = Number(value);
  return Number.isInteger(version) && version > 0 ? version : null;
}

function VersionUnavailable() {
  return (
    <div className="mx-auto w-full max-w-[48rem]">
      <EmptyState
        title="Version not found"
        description="This version does not exist or is no longer available."
        action={
          <Link
            href="/"
            className="text-sm font-medium text-brand underline-offset-4 hover:underline"
          >
            Back to campaigns
          </Link>
        }
      />
    </div>
  );
}

type VersionLoadResult =
  | {
      ok: true;
      campaign: CampaignSummary;
      version: VersionSummary;
      campaignPackage: CampaignPackage;
    }
  | { ok: false; missing: true }
  | { ok: false; error: unknown };

async function loadVersion(
  campaignId: string,
  versionNumber: number,
): Promise<VersionLoadResult> {
  try {
    const [campaign, versions] = await Promise.all([
      getCampaign(campaignId),
      listVersions(campaignId),
    ]);
    const version = versions.find((item) => item.version === versionNumber);
    if (!version) {
      return { ok: false, missing: true };
    }
    const campaignPackage = await getVersion(campaignId, versionNumber);
    return { ok: true, campaign, version, campaignPackage };
  } catch (error) {
    return { ok: false, error };
  }
}

export default async function VersionPage({ params }: VersionPageProps) {
  const { id, n } = await params;
  const versionNumber = parseVersionParam(n);

  if (versionNumber === null) {
    return <VersionUnavailable />;
  }

  const result = await loadVersion(id, versionNumber);
  if (!result.ok) {
    if ("missing" in result) {
      return <VersionUnavailable />;
    }
    if (result.error instanceof ApiError && result.error.status === 404) {
      return <VersionUnavailable />;
    }

    return (
      <div className="mx-auto w-full max-w-[48rem]">
        <ErrorState
          title="Could not load this version"
          description={
            result.error instanceof ApiError
              ? result.error.message
              : "An unexpected error occurred while loading the version."
          }
        />
      </div>
    );
  }

  const { campaign, version, campaignPackage } = result;
  const createdOn = version.created_at.slice(0, 10);

  return (
    <div className="mx-auto flex w-full max-w-[64rem] flex-col gap-lg">
      <header className="flex flex-col gap-2xs">
        <p className="text-2xs font-medium tracking-wider text-muted-foreground uppercase">
          Version review
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">
          Version {version.version}
        </h1>
        <p className="text-sm text-muted-foreground">
          Created {createdOn}
          {version.parent_version_id ? " · Revision" : null}
        </p>
      </header>

      <div className="grid gap-lg lg:grid-cols-2">
        <BriefCard brief={campaignPackage.brief} />
        <ResearchCard research={campaignPackage.research} />
        <CopyCard
          copy={campaignPackage.copy?.variants ?? null}
          className="lg:col-span-2"
        />
        {campaignPackage.direction ? null : (
          <EmptyState
            className="lg:col-span-2"
            title="No creative direction yet"
            description="The Creative Director agent has not produced direction for this version."
          />
        )}
        <AssetGrid
          assets={campaignPackage.assets?.assets ?? null}
          direction={campaignPackage.direction}
          className="lg:col-span-2"
        />
        <ComplianceReport compliance={campaignPackage.compliance} />
        <ScoreBreakdown score={campaignPackage.score} />
      </div>

      <VersionApproval
        campaignId={id}
        version={version.version}
        runId={campaign.active_run_id}
        campaignStatus={campaign.status}
        isLatest={campaign.latest_version === version.version}
      />
    </div>
  );
}
