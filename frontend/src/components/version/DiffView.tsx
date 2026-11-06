import type { VersionDiff } from "@/lib/schemas";

type DiffChange = VersionDiff["changes"][number];

const SECTION_ORDER = [
  "brief",
  "research",
  "copy",
  "direction",
  "assets",
  "compliance",
  "score",
] as const;

const SECTION_LABELS: Record<string, string> = {
  brief: "Brief",
  research: "Research",
  copy: "Copy",
  direction: "Creative direction",
  assets: "Assets",
  compliance: "Compliance",
  score: "Score",
};

function sectionKey(field: string): string {
  const match = /^[A-Za-z_]+/.exec(field);
  return match?.[0] ?? "other";
}

function sectionRank(key: string): number {
  const index = SECTION_ORDER.indexOf(key as (typeof SECTION_ORDER)[number]);
  return index === -1 ? SECTION_ORDER.length : index;
}

function groupChanges(changes: readonly DiffChange[]) {
  const groups = new Map<string, DiffChange[]>();
  for (const change of changes) {
    const key = sectionKey(change.path);
    const group = groups.get(key);
    if (group) {
      group.push(change);
    } else {
      groups.set(key, [change]);
    }
  }

  return [...groups.entries()].sort(
    ([a], [b]) => sectionRank(a) - sectionRank(b) || a.localeCompare(b),
  );
}

/** Formats any contract value as text; objects are pretty-printed JSON. */
function formatValue(value: unknown): string {
  if (value === undefined) return "—";
  if (value === null) return "null";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  try {
    return JSON.stringify(value, null, 2) ?? String(value);
  } catch {
    return String(value);
  }
}

function labelFor(key: string): string {
  return SECTION_LABELS[key] ?? key.charAt(0).toUpperCase() + key.slice(1);
}

interface DiffViewProps {
  diff: VersionDiff;
}

export function DiffView({ diff }: DiffViewProps) {
  if (diff.changes.length === 0) {
    return (
      <p className="rounded-xl border border-dashed border-border bg-card/50 p-lg text-sm text-muted-foreground">
        No changes between these versions.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-lg">
      {groupChanges(diff.changes).map(([key, changes]) => (
        <section key={key} aria-label={`Changes in ${labelFor(key)}`}>
          <h3 className="text-lg font-semibold tracking-tight">
            {labelFor(key)}
          </h3>
          <ol className="mt-sm flex flex-col gap-sm">
            {changes.map((change) => (
              <li
                key={change.path}
                data-changed="true"
                className="rounded-lg border border-border border-l-2 border-l-brand bg-card p-md"
              >
                <div className="flex flex-wrap items-center justify-between gap-2xs">
                  <code className="text-xs break-all text-muted-foreground">
                    {change.path}
                  </code>
                  <span className="rounded-full border border-brand/40 bg-brand/10 px-2 py-0.5 text-2xs font-medium text-brand">
                    Changed
                  </span>
                </div>

                <div className="mt-sm grid gap-sm sm:grid-cols-2">
                  <div className="min-w-0">
                    <h4 className="text-2xs font-medium tracking-wider text-muted-foreground uppercase">
                      Before
                    </h4>
                    <pre className="mt-2xs font-sans text-sm break-words whitespace-pre-wrap text-foreground">
                      {formatValue(change.before)}
                    </pre>
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-2xs font-medium tracking-wider text-muted-foreground uppercase">
                      After
                    </h4>
                    <pre className="mt-2xs font-sans text-sm break-words whitespace-pre-wrap text-foreground">
                      {formatValue(change.after)}
                    </pre>
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </section>
      ))}
    </div>
  );
}
