import { expect, test } from "@playwright/test";

test("the app serves the configured security headers", async ({ request }) => {
  const response = await request.get("/");
  expect(response.ok()).toBe(true);

  const headers = response.headers();
  const policy = headers["content-security-policy"];

  expect(policy).toBeTruthy();
  expect(policy).toContain("default-src 'self'");
  expect(policy).toContain("connect-src 'self'");
  expect(policy).toMatch(/connect-src[^;]*https?:\/\//);
  expect(policy).toMatch(/img-src[^;]*data:/);
  expect(policy).toMatch(/img-src[^;]*https:\/\/res\.cloudinary\.com/);
  expect(policy).toContain("frame-ancestors 'none'");
  expect(headers["x-content-type-options"]).toBe("nosniff");
  expect(headers["referrer-policy"]).toBe("strict-origin-when-cross-origin");
  expect(headers["x-frame-options"]).toBe("DENY");
});
