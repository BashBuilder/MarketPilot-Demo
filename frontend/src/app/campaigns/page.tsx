import type { ReactNode } from "react";
import Link from "next/link";
import { Inbox } from "lucide-react";
import { CampaignCard } from "@/components/campaign/CampaignCard";
import { EmptyState } from "@/components/states/empty-state";
import { RetryErrorState } from "@/components/states/retry-error-state";
import { buttonVariants } from "@/components/ui/button";
import { ApiError, listCampaigns } from "@/lib/api";
import type { CampaignSummary } from "@/lib/schemas";

export const instant = false;

function newestFirst(campaigns: readonly CampaignSummary[]): CampaignSummary[] {
  return [...campaigns].sort((a, b) => {
    const byCreated = Date.parse(b.created_at) - Date.parse(a.created_at);
    if (byCreated !== 0) return byCreated;
    return Date.parse(b.updated_at) - Date.parse(a.updated_at);
  });
}

function CampaignListEmpty() {
  return (
    <EmptyState
      title="No campaigns yet"
      description="Describe a product and audience, and the agents will build the first campaign package."
      icon={<Inbox />}
      action={
        <Link href="/campaigns/new" className={buttonVariants({ size: "lg" })}>
          New campaign
        </Link>
      }
    />
  );
}

type LoadResult =
  | { ok: true; campaigns: CampaignSummary[] }
  | { ok: false; error: unknown };

async function loadCampaigns(): Promise<LoadResult> {
  try {
    return { ok: true, campaigns: await listCampaigns() };
  } catch (error) {
    return { ok: false, error };
  }
}

export default async function CampaignsPage() {
  const result = await loadCampaigns();

  let content: ReactNode;
  if (!result.ok) {
    content = (
      <RetryErrorState
        title="Could not load campaigns"
        description={
          result.error instanceof ApiError
            ? result.error.message
            : "An unexpected error occurred while loading campaigns."
        }
      />
    );
  } else if (result.campaigns.length === 0) {
    content = <CampaignListEmpty />;
  } else {
    content = (
      <ul aria-label="Campaigns" className="grid gap-sm sm:grid-cols-2">
        {newestFirst(result.campaigns).map((campaign) => (
          <CampaignCard key={campaign.id} campaign={campaign} />
        ))}
      </ul>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-[64rem] flex-col gap-lg">
      <header className="flex flex-col gap-2xs">
        <p className="text-2xs font-medium tracking-wider text-muted-foreground uppercase">
          Workspace
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">Campaigns</h1>
        <p className="max-w-prose text-sm text-muted-foreground">
          Review the campaigns the agents have built, newest first.
        </p>
      </header>

      {content}
    </div>
  );
}
