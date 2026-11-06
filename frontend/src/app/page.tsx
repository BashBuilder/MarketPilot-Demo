import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { LandingClosing } from "@/components/landing/landing-closing";
import { LandingHighlights } from "@/components/landing/landing-highlights";
import { PipelinePreview } from "@/components/landing/pipeline-preview";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Autonomous advertising campaigns",
  description:
    "Describe a product and an audience. MarketPilot's agents research, write, design and check the campaign, then you approve it.",
};

export default function LandingPage() {
  return (
    <div className="relative isolate flex flex-col gap-section">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 -top-xl -z-10 h-[28rem] overflow-hidden"
      >
        <div className="absolute top-0 left-1/2 size-[36rem] -translate-x-1/2 rounded-full bg-accent/50 blur-3xl" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,var(--color-border)_1px,transparent_1px)] [background-size:24px_24px] opacity-40 [mask-image:linear-gradient(to_bottom,black,transparent)]" />
      </div>

      <section
        aria-labelledby="landing-heading"
        className="grid items-center gap-xl lg:grid-cols-[minmax(0,1fr)_24rem] lg:gap-2xl"
      >
        <div className="flex max-w-[42rem] flex-col items-start gap-md">
          <p className="inline-flex items-center gap-xs rounded-full border border-border bg-background/80 px-sm py-1 text-2xs font-medium tracking-wider text-muted-foreground uppercase backdrop-blur-sm">
            <span
              aria-hidden="true"
              className="size-1.5 rounded-full bg-brand"
            />
            Autonomous creative pipeline
          </p>

          <h1
            id="landing-heading"
            className="text-display font-semibold text-balance tracking-tight"
          >
            Campaigns, composed by a{" "}
            <span className="text-brand">team of agents.</span>
          </h1>

          <p className="max-w-[36rem] text-lg text-pretty text-muted-foreground">
            Describe a product and an audience. MarketPilot researches the
            market, writes channel-ready copy, designs the visuals and checks
            every claim — then hands the package to you.
          </p>

          <div className="mt-xs flex flex-col gap-sm sm:flex-row sm:items-center">
            <Link
              href="/campaigns"
              className={cn(
                buttonVariants({ size: "lg" }),
                "h-11 px-lg text-base",
              )}
            >
              Open campaigns
              <ArrowRight aria-hidden="true" />
            </Link>
            <Link
              href="/campaigns/new"
              className={cn(
                buttonVariants({ variant: "outline", size: "lg" }),
                "h-11 border-input px-lg text-base",
              )}
            >
              Start a campaign
            </Link>
          </div>

          <p className="text-xs text-muted-foreground">
            No setup. Reviewers stay in control of every launch.
          </p>
        </div>

        <PipelinePreview />
      </section>

      <LandingHighlights />

      <LandingClosing />
    </div>
  );
}
