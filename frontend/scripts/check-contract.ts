/**
 * Validates live GET responses against the frontend's Zod contract.
 * Usage: pnpm check:contract (optionally CHECK_API_URL=...).
 */
import { z } from "zod";
import {
  campaignDetail,
  campaignList,
  campaignPackage,
  sseEvent,
  versionDiff,
  versionList,
} from "../src/lib/schemas/index";

const BASE = (
  process.env.CHECK_API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000/api/v1"
).replace(/\/+$/, "");
const ORIGIN = new URL(BASE).origin;

interface Failure {
  endpoint: string;
  issues: string[];
}

const failures: Failure[] = [];
const skips: string[] = [];
let checked = 0;

function fail(endpoint: string, issues: string[]): void {
  failures.push({ endpoint, issues });
  console.log(`FAIL ${endpoint}`);
  for (const issue of issues) console.log(`     ${issue}`);
}

async function fetchJson(path: string): Promise<unknown> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { Accept: "application/json" },
  });
  const text = await response.text();
  if (!response.ok) {
    throw new Error(`${path} -> HTTP ${response.status}: ${text.slice(0, 200)}`);
  }
  return text.length === 0 ? null : JSON.parse(text);
}

function check<T>(endpoint: string, schema: z.ZodType<T>, body: unknown): T | null {
  checked += 1;
  const parsed = schema.safeParse(body);
  if (parsed.success) {
    console.log(`ok   ${endpoint}`);
    return parsed.data;
  }
  const issues = parsed.error.issues.map(
    (issue) =>
      `${issue.path.length > 0 ? issue.path.join(".") : "(root)"}: ${issue.message}`,
  );
  fail(endpoint, issues);
  return null;
}

async function checkHealth(): Promise<void> {
  checked += 1;
  const response = await fetch(`${ORIGIN}/health`);
  if (response.ok) console.log("ok   GET /health");
  else fail("GET /health", [`HTTP ${response.status}`]);
}

interface SseFrame {
  id: string;
  event: string;
  data: unknown;
}

function parseFrames(text: string): SseFrame[] {
  return text.split(/\r?\n\r?\n/).flatMap((block) => {
    const lines = block.split(/\r?\n/);
    const id = lines.find((line) => line.startsWith("id: "))?.slice(4);
    const event = lines.find((line) => line.startsWith("event: "))?.slice(7);
    const data = lines.find((line) => line.startsWith("data: "))?.slice(6);
    if (id === undefined || event === undefined || data === undefined) return [];
    try {
      return [{ id, event, data: JSON.parse(data) }];
    } catch {
      return [{ id, event, data }];
    }
  });
}

async function checkStream(runId: string): Promise<void> {
  const endpoint = "GET /runs/{run_id}/stream";
  checked += 1;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 1500);
  let buffer = "";
  try {
    const response = await fetch(`${BASE}/runs/${runId}/stream`, {
      headers: { Accept: "text/event-stream" },
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    while (reader) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
    }
  } catch (error) {
    if (!controller.signal.aborted) {
      fail(endpoint, [error instanceof Error ? error.message : String(error)]);
      return;
    }
  } finally {
    clearTimeout(timer);
  }

  const frames = parseFrames(buffer);
  if (frames.length === 0) {
    console.log(`ok   ${endpoint} (open, no events before timeout)`);
    return;
  }
  for (const frame of frames) {
    check(`${endpoint} ${frame.event}`, sseEvent, frame);
  }
}

async function main(): Promise<void> {
  await checkHealth();

  const rawList = await fetchJson("/campaigns");
  check("GET /campaigns", campaignList, rawList);
  const campaigns = Array.isArray(rawList)
    ? (rawList as Array<Record<string, unknown>>)
    : [];
  if (campaigns.length === 0) skips.push("campaign-scoped endpoints (no campaigns)");

  const streamed = new Set<string>();
  for (const campaign of campaigns) {
    const id = typeof campaign.id === "string" ? campaign.id : null;
    if (id === null) continue;

    check("GET /campaigns/{id}", campaignDetail, await fetchJson(`/campaigns/${id}`));

    const rawVersions = await fetchJson(`/campaigns/${id}/versions`);
    check("GET /campaigns/{id}/versions", versionList, rawVersions);
    const numbers = Array.isArray(rawVersions)
      ? (rawVersions as Array<Record<string, unknown>>)
          .map((item) => item.version)
          .filter((version): version is number => typeof version === "number")
      : [];

    if (numbers.length === 0) {
      skips.push("GET /campaigns/{id}/versions/{n} (no versions)");
      skips.push("GET /campaigns/{id}/versions/{a}/diff/{b} (no versions)");
    }
    for (const version of numbers) {
      check(
        "GET /campaigns/{id}/versions/{n}",
        campaignPackage,
        await fetchJson(`/campaigns/${id}/versions/${version}`),
      );
    }
    if (numbers.length >= 2) {
      check(
        "GET /campaigns/{id}/versions/{a}/diff/{b}",
        versionDiff,
        await fetchJson(
          `/campaigns/${id}/versions/${numbers[0]}/diff/${numbers[1]}`,
        ),
      );
    }

    const runId = campaign.active_run_id;
    if (typeof runId === "string" && !streamed.has(runId)) {
      streamed.add(runId);
      await checkStream(runId);
    }
  }
  if (streamed.size === 0) skips.push("GET /runs/{run_id}/stream (no active run)");

  console.log(`\nChecked ${checked} endpoint response(s).`);
  for (const skip of new Set(skips)) console.log(`skip ${skip}`);
  if (failures.length > 0) {
    console.log(`\n${failures.length} endpoint(s) failed the contract:`);
    for (const failure of failures) console.log(`- ${failure.endpoint}`);
    process.exitCode = 1;
  } else {
    console.log("\nAll checked endpoints match the Zod contract.");
  }
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
