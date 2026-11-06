import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function LandingClosing() {
  return (
    <section
      aria-labelledby="closing-heading"
      className="flex flex-col items-start justify-between gap-md rounded-2xl border border-border bg-card p-lg sm:flex-row sm:items-center"
    >
      <div className="flex flex-col gap-2xs">
        <h2 id="closing-heading" className="text-xl font-semibold tracking-tight">
          The next campaign is one idea away.
        </h2>
        <p className="text-sm text-muted-foreground">
          Browse what the agents have built, or start with a blank brief.
        </p>
      </div>
      <div className="flex w-full flex-col gap-sm sm:w-auto sm:flex-row sm:items-center">
        <Link
          href="/campaigns"
          className={cn(
            buttonVariants({ variant: "outline", size: "lg" }),
            "h-10 px-md",
          )}
        >
          Browse campaigns
        </Link>
        <Link
          href="/campaigns/new"
          className={cn(buttonVariants({ size: "lg" }), "h-10 px-md")}
        >
          Start a campaign
          <ArrowRight aria-hidden="true" />
        </Link>
      </div>
    </section>
  );
}
