import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface RunApprovalPromptProps {
  campaignId: string;
  version: number;
}

export function RunApprovalPrompt({
  campaignId,
  version,
}: RunApprovalPromptProps) {
  return (
    <section
      aria-labelledby="approval-heading"
      className="rounded-xl border border-brand/40 bg-brand/5 p-lg motion-safe:animate-in motion-safe:fade-in-0"
    >
      <p className="text-2xs font-medium tracking-wider text-brand uppercase">
        Ready for review
      </p>
      <h2
        id="approval-heading"
        className="mt-2xs text-xl font-semibold tracking-tight"
      >
        Version {version} is waiting for approval
      </h2>
      <p className="mt-xs max-w-prose text-sm text-muted-foreground">
        Review the copy, assets, compliance report and score before approving or
        requesting a revision.
      </p>
      <Link
        href={`/campaigns/${campaignId}/versions/${version}`}
        className={cn(buttonVariants({ size: "lg" }), "mt-md")}
      >
        Review version {version}
      </Link>
    </section>
  );
}
