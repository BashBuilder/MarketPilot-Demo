import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

export function SkeletonBlock({
  className,
  ...props
}: ComponentProps<"div">) {
  return (
    <div
      {...props}
      data-slot="skeleton"
      aria-hidden="true"
      className={cn(
        "motion-safe:animate-pulse rounded-md bg-muted",
        className,
      )}
    />
  );
}
