import { SkeletonBlock } from "@/components/states/skeleton-block";

export default function LoadingVersionPage() {
  return (
    <div
      role="status"
      aria-label="Loading version"
      className="mx-auto flex w-full max-w-[64rem] flex-col gap-lg"
    >
      <div className="flex flex-col gap-2xs">
        <SkeletonBlock className="h-3 w-24" />
        <SkeletonBlock className="h-8 w-48" />
        <SkeletonBlock className="h-4 w-64" />
      </div>

      <div className="grid gap-lg lg:grid-cols-2">
        <SkeletonBlock className="h-64 rounded-xl" />
        <SkeletonBlock className="h-64 rounded-xl" />
        <SkeletonBlock className="h-80 rounded-xl lg:col-span-2" />
        <SkeletonBlock className="h-72 rounded-xl" />
        <SkeletonBlock className="h-72 rounded-xl" />
      </div>

      <span className="sr-only">Loading version…</span>
    </div>
  );
}
