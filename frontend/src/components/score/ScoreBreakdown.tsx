"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";
import { EmptyState } from "@/components/states/empty-state";
import {
  scoreDimensionKeys,
  type CreativeScore,
} from "@/lib/schemas";
import { cn } from "@/lib/utils";

type DimensionKey = (typeof scoreDimensionKeys)[number];

const DIMENSION_LABELS: Record<DimensionKey, string> = {
  brief_alignment: "Brief alignment",
  audience_fit: "Audience fit",
  copy_quality: "Copy quality",
  visual_quality: "Visual quality",
  compliance_risk: "Compliance risk",
};

interface ScoreBreakdownProps {
  score?: CreativeScore | null;
  className?: string;
}

export function ScoreBreakdown({ score, className }: ScoreBreakdownProps) {
  if (!score) {
    return (
      <EmptyState
        className={className}
        title="No score yet"
        description="The Reviewer agent has not scored this version yet."
      />
    );
  }

  const dimensions = scoreDimensionKeys.map((key) => ({
    key,
    label: DIMENSION_LABELS[key],
    score: score[key].score,
    justification: score[key].justification,
  }));

  const chartLabel = `Score breakdown: ${dimensions
    .map((dimension) => `${dimension.label} ${dimension.score} out of 10`)
    .join(", ")}. Weighted total ${score.total} out of 100.`;

  return (
    <section
      aria-label="Creative score"
      className={cn(
        "flex flex-col gap-lg rounded-xl border border-border bg-card p-lg",
        className,
      )}
    >
      <header className="flex flex-col gap-2xs">
        <p className="text-2xs font-medium tracking-wider text-muted-foreground uppercase">
          Score
        </p>
        <h2 className="text-xl font-semibold tracking-tight">Creative score</h2>
      </header>

      <div className="flex items-end justify-between gap-md rounded-lg border border-border bg-muted/30 px-md py-sm">
        <div className="flex flex-col gap-2xs">
          <p className="text-2xs font-medium tracking-wider text-muted-foreground uppercase">
            Weighted total
          </p>
          <p className="text-sm text-muted-foreground">
            Across five rubric dimensions
          </p>
        </div>
        <p className="shrink-0 text-3xl font-semibold tabular-nums text-foreground">
          {score.total}
          <span className="text-sm font-normal text-muted-foreground">
            {" "}
            / 100
          </span>
        </p>
      </div>

      <div role="img" aria-label={chartLabel} className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={dimensions}
            layout="vertical"
            accessibilityLayer={false}
            margin={{ top: 0, right: 12, bottom: 0, left: 0 }}
          >
            <CartesianGrid horizontal={false} stroke="var(--border)" />
            <XAxis
              type="number"
              domain={[0, 10]}
              ticks={[0, 5, 10]}
              tickLine={false}
              axisLine={false}
              tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
            />
            <YAxis
              type="category"
              dataKey="label"
              width={112}
              tickLine={false}
              axisLine={false}
              tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
            />
            <Bar
              dataKey="score"
              fill="var(--chart-1)"
              radius={[0, 4, 4, 0]}
              isAnimationActive={false}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <ol className="flex flex-col gap-sm">
        {dimensions.map((dimension) => (
          <li
            key={dimension.key}
            data-dimension={dimension.key}
            className="flex flex-col gap-2xs border-t border-border pt-sm"
          >
            <div className="flex items-baseline justify-between gap-sm">
              <h3 className="text-sm font-medium text-foreground">
                {dimension.label}
              </h3>
              <p className="shrink-0 text-sm tabular-nums text-muted-foreground">
                <span className="font-medium text-foreground">
                  {dimension.score}
                </span>{" "}
                / 10
              </p>
            </div>
            <p className="text-sm text-muted-foreground">
              {dimension.justification}
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}
