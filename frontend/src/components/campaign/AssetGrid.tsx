"use client";

import { useState } from "react";
import { ChevronDown, ImageOff } from "lucide-react";
import { EmptyState } from "@/components/states/empty-state";
import type { Asset, CreativeDirection } from "@/lib/schemas";
import { cn } from "@/lib/utils";

interface AssetGridProps {
  assets?: Asset[] | null;
  direction?: CreativeDirection | null;
  className?: string;
}

/**
 * Prefer the art direction for alt text. The asset prompt is a generation
 * prompt, so it only serves as a last-resort description.
 */
function assetAlt(
  asset: Asset,
  direction: CreativeDirection | null | undefined,
  index: number,
): string {
  const directedPrompt = direction?.image_prompts[index];
  if (directedPrompt) return directedPrompt;
  if (direction?.style_guide) return direction.style_guide;
  return asset.prompt || "Generated campaign asset";
}

export function AssetGrid({ assets, direction, className }: AssetGridProps) {
  const [failedAssets, setFailedAssets] = useState<ReadonlySet<string>>(
    () => new Set(),
  );

  if (!assets || assets.length === 0) {
    return (
      <EmptyState
        className={className}
        title="No assets yet"
        description="The Designer agent has not produced any images for this version."
      />
    );
  }

  function markFailed(key: string) {
    setFailedAssets((previous) => {
      if (previous.has(key)) return previous;
      const next = new Set(previous);
      next.add(key);
      return next;
    });
  }

  return (
    <section
      aria-label="Campaign assets"
      className={cn(
        "flex flex-col gap-lg rounded-xl border border-border bg-card p-lg",
        className,
      )}
    >
      <header className="flex flex-col gap-2xs">
        <p className="text-2xs font-medium tracking-wider text-muted-foreground uppercase">
          Assets
        </p>
        <h2 className="text-xl font-semibold tracking-tight">Campaign assets</h2>
        <p className="text-sm text-muted-foreground">
          {assets.length} generated {assets.length === 1 ? "image" : "images"}
        </p>
      </header>

      <ul className="grid gap-md sm:grid-cols-2">
        {assets.map((asset, index) => {
          const key = `${asset.uri}-${index}`;
          const alt = assetAlt(asset, direction, index);
          const failed = failedAssets.has(key);

          return (
            <li key={key} className="min-w-0">
              <figure className="flex h-full flex-col overflow-hidden rounded-lg border border-border/70 bg-background/60">
                <div className="relative aspect-[4/3] bg-muted">
                  {failed ? (
                    <div
                      role="img"
                      aria-label={alt}
                      className="flex h-full flex-col items-center justify-center gap-xs p-md text-center"
                    >
                      <ImageOff
                        aria-hidden="true"
                        className="size-6 text-muted-foreground"
                      />
                      <p className="text-sm font-medium text-foreground">
                        Preview unavailable
                      </p>
                      <p className="text-xs break-words text-muted-foreground">
                        {alt}
                      </p>
                    </div>
                  ) : (
                    /* eslint-disable-next-line @next/next/no-img-element -- asset hosts are backend-provided at runtime */
                    <img
                      src={asset.uri}
                      alt={alt}
                      loading="lazy"
                      decoding="async"
                      onError={() => markFailed(key)}
                      className="h-full w-full object-cover"
                    />
                  )}
                </div>

                <figcaption className="flex flex-col p-md">
                  <details className="group">
                    <summary className="flex cursor-pointer list-none items-center justify-between gap-sm text-xs font-medium text-foreground transition-colors hover:text-brand focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background focus-visible:outline-none [&::-webkit-details-marker]:hidden">
                      Asset details
                      <ChevronDown
                        aria-hidden="true"
                        className="size-3.5 shrink-0 text-muted-foreground motion-safe:transition-transform group-open:rotate-180"
                      />
                    </summary>

                    <dl className="mt-sm grid gap-x-md gap-y-2xs text-xs">
                      <dt className="text-muted-foreground">Prompt</dt>
                      <dd className="break-words text-foreground">
                        {asset.prompt}
                      </dd>
                      <dt className="text-muted-foreground">Model</dt>
                      <dd className="break-words text-foreground">
                        {asset.model}
                      </dd>
                      <dt className="text-muted-foreground">Seed</dt>
                      <dd className="text-foreground tabular-nums">
                        {asset.seed}
                      </dd>
                    </dl>
                  </details>
                </figcaption>
              </figure>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
