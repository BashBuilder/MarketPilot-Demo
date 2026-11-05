export const instant = false;

export default async function RunPage({
  params,
}: PageProps<"/campaigns/[id]/run/[runId]">) {
  const { id, runId } = await params;

  return (
    <section className="mx-auto flex w-full max-w-3xl flex-col gap-3">
      <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
        Live run
      </p>
      <h1 className="text-3xl font-semibold tracking-tight">
        Agents are starting
      </h1>
      <p className="text-muted-foreground">
        Campaign <span className="font-mono text-sm text-foreground">{id}</span>
      </p>
      <p className="text-muted-foreground">
        Run <span className="font-mono text-sm text-foreground">{runId}</span>
      </p>
      <p className="max-w-prose text-sm text-muted-foreground">
        The live agent timeline arrives in the next step. This page confirms
        the run route and its identifiers.
      </p>
    </section>
  );
}
