import { SkeletonBlock } from "@/components/states/skeleton-block";

export default function LoadingVersionsPage() {
  return (
    <div
      role="status"
      aria-label="Loading version history"
      className="mx-auto flex w-full max-w-[64rem] flex-col gap-lg"
    >
      <div className="flex flex-col gap-2xs">
        <SkeletonBlock className="h-3 w-24" />
        <SkeletonBlock className="h-8 w-56" />
        <SkeletonBlock className="h-4 w-80" />
      </div>

      <div className="divide-y divide-border overflow-hidden rounded-xl border border-border">
        {[0, 1, 2].map((row) => (
          <div key={row} className="flex items-center justify-between gap-md p-md">
            <div className="flex flex-col gap-2">
              <SkeletonBlock className="h-4 w-24" />
              <SkeletonBlock className="h-3 w-40" />
            </div>
            <SkeletonBlock className="h-6 w-28 rounded-full" />
          </div>
        ))}
      </div>

      <span className="sr-only">Loading version history…</span>
    </div>
  );
}
