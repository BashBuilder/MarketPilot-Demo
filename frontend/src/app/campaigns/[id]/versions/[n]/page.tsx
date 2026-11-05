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
import { ApiError, getVersion } from "@/lib/api";
import type { CampaignVersion } from "@/lib/schemas";

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

export default async function VersionPage({ params }: VersionPageProps) {
  const { id, n } = await params;
  const versionNumber = parseVersionParam(n);

  if (versionNumber === null) {
    return <VersionUnavailable />;
  }

  let version: CampaignVersion;
  try {
    version = await getVersion(id, versionNumber);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return <VersionUnavailable />;
    }

    return (
      <div className="mx-auto w-full max-w-[48rem]">
        <ErrorState
          title="Could not load this version"
          description={
            error instanceof ApiError
              ? error.message
              : "An unexpected error occurred while loading the version."
          }
        />
      </div>
    );
  }

  const campaignPackage = version.package;
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
          {version.parent_version
            ? ` · Revised from version ${version.parent_version}`
            : null}
        </p>
      </header>

      <div className="grid gap-lg lg:grid-cols-2">
        <BriefCard brief={campaignPackage.brief} />
        <ResearchCard research={campaignPackage.research} />
        <CopyCard copy={campaignPackage.copy} className="lg:col-span-2" />
        <AssetGrid
          assets={campaignPackage.assets}
          direction={campaignPackage.direction}
          className="lg:col-span-2"
        />
        <ComplianceReport compliance={campaignPackage.compliance} />
        <ScoreBreakdown score={campaignPackage.score} />
      </div>

      <VersionApproval
        campaignId={id}
        version={version.version}
        runId={version.run_id}
        runStatus={version.run_status}
      />
    </div>
  );
}
