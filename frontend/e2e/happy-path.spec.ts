import { expect, test } from "@playwright/test";

const idea =
  "Launch a fictional hair-care line for busy commuters aged 25 to 40";

test.describe.configure({ timeout: 300_000 });

test.beforeEach(({}, testInfo) => {
  test.skip(
    testInfo.project.name === "real" && !process.env.E2E_API_URL,
    "Set E2E_API_URL to run the real-backend project.",
  );
});

test("submits an idea, follows the live run, and approves the version", async ({
  page,
}, testInfo) => {
  await page.goto("/campaigns/new");

  if (testInfo.project.name === "mock") {
    // The POST is served by MSW; wait until its worker controls the page.
    await page.waitForFunction(
      () => Boolean(navigator.serviceWorker?.controller),
      undefined,
      { timeout: 30_000 },
    );
  }

  await page.getByLabel("Campaign idea").fill(idea);
  await page.getByRole("button", { name: "Start campaign" }).click();

  await expect(page).toHaveURL(/\/campaigns\/[^/]+\/run\/[^/]+$/);
  await expect(
    page.getByRole("heading", { level: 1, name: "Ready for your review" }),
  ).toBeVisible({ timeout: 120_000 });

  await page.getByRole("link", { name: "Review version 1" }).click();

  await expect(
    page.getByRole("heading", { level: 1, name: "Version 1" }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Approve", exact: true }).click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Approve version 1" }).click();

  await expect(
    page.getByRole("heading", { name: "Version 1 approved" }),
  ).toBeVisible();
});
