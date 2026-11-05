import Link from "next/link";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { PageContainer } from "./page-container";
import { SiteNav } from "./site-nav";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-border/70 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <PageContainer className="flex h-16 items-center justify-between gap-sm">
        <Link
          href="/"
          aria-label="MarketPilot home"
          className="inline-flex min-h-10 items-center gap-2xs rounded-md px-2xs text-foreground transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          <span
            aria-hidden="true"
            className="grid size-7 place-items-center rounded-md bg-primary text-xs font-semibold text-primary-foreground"
          >
            M
          </span>
          <span className="hidden text-sm font-semibold tracking-tight sm:inline">
            MarketPilot
          </span>
        </Link>

        <div className="flex items-center gap-2xs">
          <SiteNav />
          <ThemeToggle />
        </div>
      </PageContainer>
    </header>
  );
}
