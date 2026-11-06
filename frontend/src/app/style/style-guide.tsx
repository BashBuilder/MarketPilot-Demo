"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { Inbox } from "lucide-react";
import { EmptyState } from "@/components/states/empty-state";
import { ErrorState } from "@/components/states/error-state";
import { SkeletonBlock } from "@/components/states/skeleton-block";
import { buttonVariants } from "@/components/ui/button";
import {
  colorTokenGroups,
  fontTokens,
  radiusScale,
  spacingScale,
  trackingScale,
  typeScale,
} from "@/lib/design/token-manifest";
import { cn } from "@/lib/utils";

interface ThemePanelProps {
  theme: "light" | "dark";
  children: ReactNode;
}

function ThemePanel({ theme, children }: ThemePanelProps) {
  const headingId = `${theme}-preview-heading`;

  return (
    <section
      data-testid="theme-preview"
      data-theme-preview={theme}
      aria-labelledby={headingId}
      className={cn(
        theme === "dark" ? "dark" : "light",
        "min-w-0 rounded-2xl border border-border bg-background p-lg text-foreground shadow-sm sm:p-xl",
      )}
    >
      <header className="flex flex-wrap items-center justify-between gap-sm border-b border-border pb-md">
        <div>
          <h2 id={headingId} className="text-xl font-semibold tracking-tight">
            {theme === "dark" ? "Dark theme" : "Light theme"}
          </h2>
          <p className="mt-2xs text-sm text-muted-foreground">
            Fixed preview. The header toggle does not change this panel.
          </p>
        </div>
        <span className="rounded-full border border-border bg-muted px-sm py-2xs text-2xs font-medium tracking-wide text-muted-foreground uppercase">
          {theme}
        </span>
      </header>

      <div className="mt-lg space-y-2xl">{children}</div>
    </section>
  );
}

interface TokenSectionProps {
  title: string;
  description: string;
  children: ReactNode;
}

function TokenSection({ title, description, children }: TokenSectionProps) {
  return (
    <section className="min-w-0">
      <div className="mb-sm">
        <h3 className="text-lg font-semibold tracking-tight">{title}</h3>
        <p className="mt-2xs text-sm text-muted-foreground">{description}</p>
      </div>
      {children}
    </section>
  );
}

function ColourTokens() {
  return (
    <TokenSection
      title="Colour tokens"
      description="Every semantic colour, resolved inside this preview."
    >
      <div className="space-y-lg">
        {colorTokenGroups.map((group) => (
          <div key={group.label}>
            <div className="mb-xs">
              <h4 className="text-sm font-medium">{group.label}</h4>
              <p className="text-2xs text-muted-foreground">
                {group.description}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-sm sm:grid-cols-3">
              {group.tokens.map((token) => (
                <div key={token} className="min-w-0">
                  <div
                    data-color-token={token}
                    className="h-12 rounded-md border border-foreground/15"
                    style={{ backgroundColor: `var(${token})` }}
                  />
                  <code className="mt-2xs block truncate font-mono text-2xs text-muted-foreground">
                    {token}
                  </code>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </TokenSection>
  );
}

function TypeScale() {
  return (
    <TokenSection
      title="Type scale"
      description="Editorial sizes with their paired line-height tokens."
    >
      <div className="space-y-md">
        {typeScale.map((step) => {
          const derived = [
            `${step.token}--line-height`,
            ...(step.token === "--text-display"
              ? ["--text-display--letter-spacing"]
              : []),
          ].join(" · ");

          return (
            <div
              key={step.token}
              data-type-token={step.token}
              className="border-b border-border pb-sm last:border-b-0 last:pb-0"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2xs">
                <code className="font-mono text-2xs text-muted-foreground">
                  {step.token}
                </code>
                <code className="font-mono text-2xs text-muted-foreground">
                  {derived}
                </code>
              </div>
              <p className={cn(step.className, "mt-2xs break-words")}>
                {step.sample}
              </p>
            </div>
          );
        })}
      </div>
    </TokenSection>
  );
}

function SpacingScale() {
  return (
    <TokenSection
      title="Spacing scale"
      description="A 4px base grid with named steps for editorial rhythm."
    >
      <div className="space-y-xs">
        {spacingScale.map((step) => (
          <div
            key={step.token}
            data-spacing-token={step.token}
            className="flex items-center gap-sm"
          >
            <code className="w-36 shrink-0 truncate font-mono text-2xs text-muted-foreground">
              {step.token}
            </code>
            <div className="flex min-w-0 flex-1 items-center gap-sm">
              <div
                className="h-2 shrink-0 rounded-full bg-brand"
                style={{ width: `var(${step.token})` }}
              />
              <span className="text-2xs text-muted-foreground">
                {step.label}
              </span>
            </div>
          </div>
        ))}
      </div>
    </TokenSection>
  );
}

function RadiusScale() {
  return (
    <TokenSection
      title="Radius scale"
      description="One base radius with derived steps."
    >
      <div className="flex flex-wrap gap-md">
        {radiusScale.map((step) => (
          <div
            key={step.token}
            data-radius-token={step.token}
            className="text-center"
          >
            <div
              className="size-16 border border-border bg-accent"
              style={{ borderRadius: `var(${step.token})` }}
            />
            <code className="mt-2xs block font-mono text-2xs text-muted-foreground">
              {step.token}
            </code>
          </div>
        ))}
      </div>
    </TokenSection>
  );
}

function TrackingScale() {
  return (
    <TokenSection
      title="Tracking"
      description="Letter-spacing tokens for labels and display type."
    >
      <div className="space-y-xs">
        {trackingScale.map((step) => (
          <div
            key={step.token}
            data-tracking-token={step.token}
            className="flex flex-wrap items-baseline justify-between gap-2xs"
          >
            <code className="font-mono text-2xs text-muted-foreground">
              {step.token}
            </code>
            <span
              className="text-sm"
              style={{ letterSpacing: `var(${step.token})` }}
            >
              Editorial rhythm
            </span>
          </div>
        ))}
      </div>
    </TokenSection>
  );
}

function FontFamilies() {
  return (
    <TokenSection
      title="Font families"
      description="Body and heading families share the Geist variable."
    >
      <div className="space-y-sm">
        {fontTokens.map((font) => (
          <div key={font.token} data-font-token={font.token}>
            <div className="flex items-baseline justify-between gap-sm">
              <code className="font-mono text-2xs text-muted-foreground">
                {font.token}
              </code>
              <span className="text-2xs text-muted-foreground">
                {font.label}
              </span>
            </div>
            <p
              className="mt-2xs text-2xl tracking-tight"
              style={{ fontFamily: `var(${font.token})` }}
            >
              {font.sample}
            </p>
          </div>
        ))}
      </div>
    </TokenSection>
  );
}

function StateExamples() {
  const [message, setMessage] = useState<string | null>(null);

  return (
    <TokenSection
      title="State examples"
      description="Empty, loading, and error states built from shared components."
    >
      <div className="space-y-md">
        <EmptyState
          headingLevel="h4"
          icon={<Inbox />}
          title="No campaigns yet"
          description="Start with a brief; the agents will return a full package for review."
          action={
            <Link
              href="/campaigns/new"
              className={buttonVariants({ variant: "outline", size: "sm" })}
            >
              Create a campaign
            </Link>
          }
        />

        <div
          role="status"
          aria-busy="true"
          className="rounded-xl border border-border bg-card p-lg"
        >
          <span className="sr-only">Loading campaign preview</span>
          <SkeletonBlock className="h-5 w-2/5" />
          <SkeletonBlock className="mt-sm h-3 w-full" />
          <SkeletonBlock className="mt-xs h-3 w-4/5" />
          <div className="mt-md flex items-center gap-sm">
            <SkeletonBlock className="size-12 rounded-full" />
            <div className="min-w-0 flex-1 space-y-xs">
              <SkeletonBlock className="h-3 w-1/2" />
              <SkeletonBlock className="h-3 w-1/3" />
            </div>
          </div>
        </div>

        <ErrorState
          headingLevel="h4"
          title="We couldn't load this campaign"
          description="The package may still be generating. Retry in a moment."
          onRetry={() =>
            setMessage("Retry requested. This preview does not call the API.")
          }
        />

        {message ? (
          <p role="status" className="text-sm text-muted-foreground">
            {message}
          </p>
        ) : null}
      </div>
    </TokenSection>
  );
}

export function StyleGuide() {
  return (
    <div className="grid gap-lg xl:grid-cols-2">
      <ThemePanel theme="light">
        <ColourTokens />
        <TypeScale />
        <SpacingScale />
        <RadiusScale />
        <TrackingScale />
        <FontFamilies />
        <StateExamples />
      </ThemePanel>

      <ThemePanel theme="dark">
        <ColourTokens />
        <TypeScale />
        <SpacingScale />
        <RadiusScale />
        <TrackingScale />
        <FontFamilies />
        <StateExamples />
      </ThemePanel>
    </div>
  );
}
