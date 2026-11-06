import { EmptyState } from "@/components/states/empty-state";
import { ErrorState } from "@/components/states/error-state";
import { VersionCompare } from "@/components/version/VersionCompare";
import { VersionList } from "@/components/version/VersionList";
import { ApiError, listVersions } from "@/lib/api";
import type { VersionSummary } from "@/lib/schemas";

export const instant = false;

interface VersionsPageProps {
  params: Promise<{ id: string }>;
}

export default async function VersionsPage({ params }: VersionsPageProps) {
  const { id } = await params;

  let versions: VersionSummary[];
  try {
    versions = await listVersions(id);
  } catch (error) {
    return (
      <div className="mx-auto w-full max-w-[64rem]">
        <ErrorState
          title="Could not load version history"
          description={
            error instanceof ApiError
              ? error.message
              : "An unexpected error occurred while loading the versions."
          }
        />
      </div>
    );
  }

  if (versions.length === 0) {
    return (
      <div className="mx-auto w-full max-w-[64rem]">
        <EmptyState
          title="No versions yet"
          description="This campaign has not produced a package yet. A version appears here after the agents finish a run."
        />
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-[64rem] flex-col gap-lg">
      <header className="flex flex-col gap-2xs">
        <p className="text-2xs font-medium tracking-wider text-muted-foreground uppercase">
          Campaign
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">Version history</h1>
        <p className="max-w-prose text-sm text-muted-foreground">
          Every revision is saved as a new version. Select one to review its
          package.
        </p>
      </header>

      <VersionList campaignId={id} versions={versions} />

      <section
        aria-labelledby="compare-versions-heading"
        className="flex flex-col gap-sm"
      >
        <h2
          id="compare-versions-heading"
          className="text-xl font-semibold tracking-tight"
        >
          Compare versions
        </h2>
        <p className="max-w-prose text-sm text-muted-foreground">
          Pick two versions to see what changed between them.
        </p>
        <VersionCompare campaignId={id} versions={versions} />
      </section>
    </div>
  );
}
