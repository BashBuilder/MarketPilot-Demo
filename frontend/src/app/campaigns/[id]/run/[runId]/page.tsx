import { LiveRunView } from "./live-run-view";

export const instant = false;

export default async function RunPage({
  params,
}: PageProps<"/campaigns/[id]/run/[runId]">) {
  const { id, runId } = await params;

  return <LiveRunView campaignId={id} runId={runId} />;
}
