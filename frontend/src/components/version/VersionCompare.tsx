"use client";

import { useState, type FormEvent } from "react";
import { ErrorState } from "@/components/states/error-state";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { ApiError, getVersionDiff } from "@/lib/api";
import type { VersionDiff, VersionSummary } from "@/lib/schemas";
import { DiffView } from "./DiffView";

const selectClassName =
  "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-base outline-none transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm dark:bg-input/30";

interface VersionCompareProps {
  campaignId: string;
  versions: readonly VersionSummary[];
}

function errorMessage(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : "An unexpected error occurred while comparing versions.";
}

export function VersionCompare({
  campaignId,
  versions,
}: VersionCompareProps) {
  const ordered = [...versions].sort((a, b) => b.version - a.version);
  const [fromVersion, setFromVersion] = useState(
    ordered[1] ? String(ordered[1].version) : "",
  );
  const [toVersion, setToVersion] = useState(
    ordered[0] ? String(ordered[0].version) : "",
  );
  const [diff, setDiff] = useState<VersionDiff | null>(null);
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (ordered.length < 2) {
    return (
      <p className="rounded-xl border border-dashed border-border bg-card/50 p-lg text-sm text-muted-foreground">
        Add another version to compare changes.
      </p>
    );
  }

  const canCompare =
    fromVersion !== "" && toVersion !== "" && fromVersion !== toVersion;

  function resetResult() {
    setDiff(null);
    setError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canCompare || isPending) return;

    setIsPending(true);
    resetResult();
    try {
      const result = await getVersionDiff(
        campaignId,
        Number(fromVersion),
        Number(toVersion),
      );
      setDiff(result);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setIsPending(false);
    }
  }

  return (
    <div className="flex flex-col gap-md">
      <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-sm">
        <div className="flex min-w-40 flex-col gap-2">
          <Label htmlFor="compare-from">From version</Label>
          <select
            id="compare-from"
            value={fromVersion}
            disabled={isPending}
            className={selectClassName}
            onChange={(event) => {
              setFromVersion(event.target.value);
              resetResult();
            }}
          >
            {ordered.map((version) => (
              <option key={version.version} value={version.version}>
                Version {version.version}
              </option>
            ))}
          </select>
        </div>

        <div className="flex min-w-40 flex-col gap-2">
          <Label htmlFor="compare-to">To version</Label>
          <select
            id="compare-to"
            value={toVersion}
            disabled={isPending}
            className={selectClassName}
            onChange={(event) => {
              setToVersion(event.target.value);
              resetResult();
            }}
          >
            {ordered.map((version) => (
              <option key={version.version} value={version.version}>
                Version {version.version}
              </option>
            ))}
          </select>
        </div>

        <Button type="submit" disabled={!canCompare || isPending}>
          {isPending ? "Comparing…" : "Compare versions"}
        </Button>
      </form>

      {isPending ? (
        <p role="status" className="text-sm text-muted-foreground">
          Comparing versions…
        </p>
      ) : null}

      {error ? (
        <ErrorState
          title="Could not compare versions"
          description={error}
          headingLevel="h3"
        />
      ) : null}

      {diff ? <DiffView diff={diff} /> : null}
    </div>
  );
}
