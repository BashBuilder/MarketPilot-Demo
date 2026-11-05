import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import type { StateHeadingLevel } from "./heading-level";

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
  headingLevel?: StateHeadingLevel;
  className?: string;
}

export function EmptyState({
  title,
  description,
  icon,
  action,
  headingLevel = "h2",
  className,
}: EmptyStateProps) {
  const Heading = headingLevel;

  return (
    <section
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/50 px-lg py-2xl text-center",
        className,
      )}
    >
      {icon ? (
        <div
          aria-hidden="true"
          className="mb-sm grid size-11 place-items-center rounded-full bg-muted text-muted-foreground [&_svg]:size-5"
        >
          {icon}
        </div>
      ) : null}

      <Heading className="text-lg font-semibold tracking-tight">{title}</Heading>

      {description ? (
        <p className="mt-2xs max-w-prose text-sm text-muted-foreground">
          {description}
        </p>
      ) : null}

      {action ? <div className="mt-md">{action}</div> : null}
    </section>
  );
}
