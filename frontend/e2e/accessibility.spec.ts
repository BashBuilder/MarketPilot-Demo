import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

// These IDs match src/mocks/fixtures/campaign.ts. The mock API seeds one
// campaign and one run so each page can be reached without setup.
const campaignId = "7c9e6679-7425-40de-944b-e07fc1f90ae7";
const runId = "0f8fad5b-d9cb-469f-a165-70867728950e";

const pages = [
  {
    name: "campaign list",
    path: "/",
    heading: "Campaigns",
  },
  {
    name: "new campaign",
    path: "/campaigns/new",
    heading: "What should the agents create?",
  },
  {
    name: "live run",
    path: `/campaigns/${campaignId}/run/${runId}`,
    heading: "Ready for your review",
  },
  {
    name: "version review",
    path: `/campaigns/${campaignId}/versions/1`,
    heading: "Version 1",
  },
  {
    name: "version history",
    path: `/campaigns/${campaignId}/versions`,
    heading: "Version history",
  },
  {
    name: "campaign overview",
    path: `/campaigns/${campaignId}`,
    heading:
      "Create an advertising campaign for a fictional hair-care product targeting adults aged 25 to 40",
  },
] as const;

async function expectNoSeriousViolations(page: Page): Promise<void> {
  const results = await new AxeBuilder({ page }).analyze();
  const violations = results.violations.filter(
    (violation) =>
      violation.impact === "serious" || violation.impact === "critical",
  );

  const report = violations
    .map(
      (violation) =>
        `[${violation.impact}] ${violation.id}: ${violation.help}\n${violation.nodes
          .map((node) => `  ${node.target.join(" ")}`)
          .join("\n")}`,
    )
    .join("\n\n");

  expect(violations, report).toEqual([]);
}

for (const entry of pages) {
  test(`${entry.name} has no serious accessibility violations`, async ({
    page,
  }) => {
    await page.goto(entry.path);
    await expect(
      page.getByRole("heading", { level: 1, name: entry.heading }),
    ).toBeVisible({ timeout: 30_000 });

    await expectNoSeriousViolations(page);
  });
}
