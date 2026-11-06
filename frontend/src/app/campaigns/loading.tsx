import { SkeletonBlock } from "@/components/states/skeleton-block";

export default function LoadingCampaignsPage() {
  return (
    <div
      role="status"
      aria-label="Loading campaigns"
      className="mx-auto flex w-full max-w-[64rem] flex-col gap-lg"
    >
      <div className="flex flex-col gap-2xs">
        <SkeletonBlock className="h-3 w-20" />
        <SkeletonBlock className="h-8 w-48" />
        <SkeletonBlock className="h-4 w-80 max-w-full" />
      </div>

      <div className="grid gap-sm sm:grid-cols-2">
        {[0, 1, 2, 3].map((card) => (
          <div
            key={card}
            className="flex items-start justify-between gap-md rounded-xl border border-border bg-card p-md"
          >
            <div className="flex flex-1 flex-col gap-xs">
              <SkeletonBlock className="h-4 w-full max-w-[22rem]" />
              <SkeletonBlock className="h-3 w-40" />
            </div>
            <div className="flex flex-col items-end gap-xs">
              <SkeletonBlock className="h-5 w-24 rounded-full" />
              <SkeletonBlock className="h-4 w-16" />
            </div>
          </div>
        ))}
      </div>

      <span className="sr-only">Loading campaigns…</span>
    </div>
  );
}
