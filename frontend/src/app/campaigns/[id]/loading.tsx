import { SkeletonBlock } from "@/components/states/skeleton-block";

export default function LoadingCampaignPage() {
  return (
    <div
      role="status"
      aria-label="Loading campaign"
      className="mx-auto flex w-full max-w-[64rem] flex-col gap-lg"
    >
      <div className="flex flex-col gap-sm">
        <SkeletonBlock className="h-3 w-28" />
        <SkeletonBlock className="h-9 w-full max-w-[40rem]" />
        <SkeletonBlock className="h-3 w-36" />
      </div>

      <div className="rounded-xl border border-border bg-card p-lg">
        <div className="flex flex-wrap items-start justify-between gap-md">
          <div className="flex flex-col gap-xs">
            <SkeletonBlock className="h-3 w-24" />
            <SkeletonBlock className="h-6 w-32" />
            <SkeletonBlock className="h-4 w-44" />
          </div>
          <div className="flex flex-col items-end gap-xs">
            <SkeletonBlock className="h-5 w-24 rounded-full" />
            <SkeletonBlock className="h-8 w-20" />
          </div>
        </div>
        <div className="mt-md flex flex-wrap gap-sm">
          <SkeletonBlock className="h-9 w-40" />
          <SkeletonBlock className="h-9 w-36" />
        </div>
      </div>

      <span className="sr-only">Loading campaign…</span>
    </div>
  );
}
