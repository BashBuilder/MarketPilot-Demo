import { Check, X } from "lucide-react";
import { EmptyState } from "@/components/states/empty-state";
import type { ComplianceReport as ComplianceReportData } from "@/lib/schemas";
import { cn } from "@/lib/utils";

interface ComplianceReportProps {
  compliance?: ComplianceReportData | null;
  className?: string;
}

export function ComplianceReport({
  compliance,
  className,
}: ComplianceReportProps) {
  if (!compliance || compliance.items.length === 0) {
    return (
      <EmptyState
        className={className}
        title="No compliance report yet"
        description="The Compliance agent has not checked this version yet."
      />
    );
  }

  const failedCount = compliance.items.filter((item) => !item.passed).length;
  const passedCount = compliance.items.length - failedCount;

  return (
    <section
      aria-label="Compliance report"
      className={cn(
        "flex flex-col gap-lg rounded-xl border border-border bg-card p-lg",
        className,
      )}
    >
      <header className="flex flex-col gap-2xs">
        <p className="text-2xs font-medium tracking-wider text-muted-foreground uppercase">
          Compliance
        </p>
        <h2 className="text-xl font-semibold tracking-tight">
          Compliance report
        </h2>
        <p className="text-sm text-muted-foreground">
          {passedCount} of {compliance.items.length} checks passed
          {failedCount > 0 ? ` · ${failedCount} need attention` : ""}
        </p>
      </header>

      <ul className="flex flex-col gap-sm">
        {compliance.items.map((item, index) => (
          <li
            key={`${item.check}-${index}`}
            data-status={item.passed ? "passed" : "failed"}
            className={cn(
              "flex gap-sm rounded-lg border border-l-4 p-md",
              item.passed
                ? "border-border border-l-brand/60"
                : "border-destructive/30 border-l-destructive bg-destructive/5",
            )}
          >
            <span
              aria-hidden="true"
              className={cn(
                "mt-2xs grid size-5 shrink-0 place-items-center rounded-full",
                item.passed
                  ? "bg-brand/10 text-brand"
                  : "bg-destructive/10 text-destructive",
              )}
            >
              {item.passed ? (
                <Check className="size-3" />
              ) : (
                <X className="size-3" />
              )}
            </span>

            <div className="flex min-w-0 flex-col gap-2xs">
              <div className="flex flex-wrap items-center gap-x-sm gap-y-1">
                <h3 className="text-sm font-medium text-foreground">
                  {item.check}
                </h3>
                <span
                  className={cn(
                    "inline-flex shrink-0 items-center rounded-full border px-2 py-0.5 text-2xs font-medium tracking-wide uppercase",
                    item.passed
                      ? "border-brand/40 text-brand"
                      : "border-destructive/40 text-destructive",
                  )}
                >
                  {item.passed ? "Passed" : "Failed"}
                </span>
              </div>
              <p className="text-sm text-muted-foreground">{item.reason}</p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
