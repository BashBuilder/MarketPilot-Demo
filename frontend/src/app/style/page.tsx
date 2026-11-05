import type { Metadata } from "next";
import { StyleGuide } from "./style-guide";

export const metadata: Metadata = {
  title: "Style guide",
  description:
    "Design tokens and shared empty, loading, and error states in both themes.",
};

export default function StylePage() {
  return (
    <div className="space-y-lg">
      <header className="max-w-prose space-y-xs">
        <p className="text-xs font-medium tracking-wider text-muted-foreground uppercase">
          Design system
        </p>
        <h1 className="text-4xl font-semibold tracking-tight">Style guide</h1>
        <p className="text-base text-muted-foreground">
          Every design token and shared state, shown in fixed light and dark
          previews. The header toggle changes the surrounding app theme; these
          panels stay fixed for comparison.
        </p>
      </header>

      <StyleGuide />
    </div>
  );
}
