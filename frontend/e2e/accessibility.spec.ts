import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { appPages } from "./pages";

const THEME_STORAGE_KEY = "marketpilot-theme";
const themes = ["light", "dark"] as const;
type Theme = (typeof themes)[number];

async function openInTheme(
  page: Page,
  path: string,
  theme: Theme,
): Promise<void> {
  await page.addInitScript(
    ([key, value]) => {
      window.localStorage.setItem(key, value);
    },
    [THEME_STORAGE_KEY, theme],
  );
  await page.goto(path);

  const root = page.locator("html");
  if (theme === "dark") {
    await expect(root).toHaveClass(/dark/);
  } else {
    await expect(root).not.toHaveClass(/dark/);
  }
}

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

for (const theme of themes) {
  for (const entry of appPages) {
    test(`${entry.name} has no serious violations in the ${theme} theme`, async ({
      page,
    }) => {
      await openInTheme(page, entry.path, theme);
      await expect(
        page.getByRole("heading", { level: 1, name: entry.heading }),
      ).toBeVisible({ timeout: 30_000 });

      await expectNoSeriousViolations(page);
    });
  }
}
