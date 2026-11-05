"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { IdeaForm } from "@/components/campaign/IdeaForm";
import { ErrorState } from "@/components/states/error-state";
import { ApiError, createCampaign } from "@/lib/api";

export default function NewCampaignPage() {
  const router = useRouter();
  const [error, setError] = useState<ApiError | null>(null);

  async function handleSubmit(idea: string) {
    setError(null);
    try {
      const { campaign_id, run_id } = await createCampaign({ idea });
      router.push(`/campaigns/${campaign_id}/run/${run_id}`);
    } catch (cause) {
      if (cause instanceof ApiError) {
        setError(cause);
        return;
      }
      // Let IdeaForm surface unexpected client errors next to the input.
      throw cause;
    }
  }

  return (
    <section className="mx-auto flex w-full max-w-3xl flex-col gap-6">
      <header className="flex flex-col gap-2">
        <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
          New campaign
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">
          What should the agents create?
        </h1>
        <p className="max-w-prose text-muted-foreground">
          Describe the product, audience and goal. MarketPilot researches,
          writes and designs a complete campaign package for your review.
        </p>
      </header>

      {error ? (
        <ErrorState
          title="Could not start the campaign"
          description={error.message}
        />
      ) : null}

      <IdeaForm onSubmit={handleSubmit} />
    </section>
  );
}
