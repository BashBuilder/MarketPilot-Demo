import type { Metadata } from "next";
import "./globals.css";
import { Geist } from "next/font/google";
import { PageContainer } from "@/components/layout/page-container";
import { SiteHeader } from "@/components/layout/site-header";
import { SkipLink } from "@/components/layout/skip-link";
import { ThemeScript } from "@/components/theme/theme-script";
import { cn } from "@/lib/utils";
import { MockProvider } from "@/mocks/provider";

const geist = Geist({ subsets: ["latin"], variable: "--font-geist-sans" });

const mockingEnabled = process.env.NEXT_PUBLIC_API_MOCKING === "enabled";

export const metadata: Metadata = {
  title: {
    default: "MarketPilot",
    template: "%s · MarketPilot",
  },
  description: "Autonomous advertising creative pipeline",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={cn("font-sans", geist.variable)}
    >
      <head>
        <ThemeScript />
      </head>
      <body>
        <div className="flex min-h-dvh flex-col">
          <SkipLink />
          <SiteHeader />
          <main
            id="main-content"
            tabIndex={-1}
            className="flex-1 scroll-mt-20 outline-none"
          >
            <PageContainer className="py-lg sm:py-xl">
              {mockingEnabled ? (
                <MockProvider>{children}</MockProvider>
              ) : (
                children
              )}
            </PageContainer>
          </main>
        </div>
      </body>
    </html>
  );
}
