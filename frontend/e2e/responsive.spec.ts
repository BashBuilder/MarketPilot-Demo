import { expect, test } from "@playwright/test";
import { appPages } from "./pages";

const widths = [360, 768, 1280] as const;

for (const entry of appPages) {
  for (const width of widths) {
    test(`${entry.name} has no horizontal overflow at ${width}px`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(entry.path);
      await expect(
        page.getByRole("heading", { level: 1, name: entry.heading }),
      ).toBeVisible({ timeout: 30_000 });

      // Let web fonts settle before measuring; glyph widths affect wrapping.
      await page.evaluate(() => document.fonts.ready.then(() => undefined));

      const overflow = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
        bodyScrollWidth: document.body.scrollWidth,
      }));

      expect(
        overflow.scrollWidth,
        `documentElement scrollWidth ${overflow.scrollWidth} exceeds clientWidth ${overflow.clientWidth}`,
      ).toBeLessThanOrEqual(overflow.clientWidth);

      expect(
        overflow.bodyScrollWidth,
        `body scrollWidth ${overflow.bodyScrollWidth} exceeds clientWidth ${overflow.clientWidth}`,
      ).toBeLessThanOrEqual(overflow.clientWidth);
    });
  }
}
