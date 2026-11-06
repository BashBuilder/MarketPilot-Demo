import Link from "next/link";
import { CampaignOverview } from "@/components/campaign/CampaignOverview";
import { EmptyState } from "@/components/states/empty-state";
import { RetryErrorState } from "@/components/states/retry-error-state";
import { ApiError, getCampaign, listVersions } from "@/lib/api";
import type { CampaignSummary, VersionSummary } from "@/lib/schemas";

export const instant = false;

interface CampaignPageProps {
  params: Promise<{ id: string }>;
}

type LoadResult =
  | { ok: true; campaign: CampaignSummary; version: VersionSummary | null }
  | { ok: false; error: unknown };

async function loadCampaign(id: string): Promise<LoadResult> {
  try {
    const [campaign, versions] = await Promise.all([
      getCampaign(id),
      listVersions(id),
    ]);
    if (campaign.latest_version === null) {
      return { ok: true, campaign, version: null };
    }

    const version =
      versions.find((item) => item.version === campaign.latest_version) ?? null;
    return { ok: true, campaign, version };
  } catch (error) {
    return { ok: false, error };
  }
}

function CampaignNotFound() {
  return (
    <div className="mx-auto w-full max-w-[48rem]">
      <EmptyState
        title="Campaign not found"
        description="This campaign does not exist or is no longer available."
        action={
          <Link
            href="/campaigns"
            className="text-sm font-medium text-brand underline-offset-4 hover:underline"
          >
            Back to campaigns
          </Link>
        }
      />
    </div>
  );
}

export default async function CampaignPage({ params }: CampaignPageProps) {
  const { id } = await params;
  const result = await loadCampaign(id);

  if (!result.ok) {
    if (result.error instanceof ApiError && result.error.status === 404) {
      return <CampaignNotFound />;
    }

    return (
      <div className="mx-auto w-full max-w-[64rem]">
        <RetryErrorState
          title="Could not load this campaign"
          description={
            result.error instanceof ApiError
              ? result.error.message
              : "An unexpected error occurred while loading the campaign."
          }
        />
      </div>
    );
  }

  return (
    <CampaignOverview campaign={result.campaign} version={result.version} />
  );
}
