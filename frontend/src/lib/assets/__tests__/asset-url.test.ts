import { describe, expect, it } from "vitest";
import { resolveAssetUrl } from "@/lib/assets/asset-url";

describe("resolveAssetUrl", () => {
  it("proxies backend-relative asset names through the same origin", () => {
    expect(resolveAssetUrl("fake-08b826539d2cfa5b.png")).toBe(
      "/api/assets/fake-08b826539d2cfa5b.png",
    );
  });

  it("keeps nested relative paths and encodes each segment", () => {
    expect(resolveAssetUrl("/revisions/asset 1.webp")).toBe(
      "/api/assets/revisions/asset%201.webp",
    );
  });

  it("leaves absolute web and inline URLs untouched", () => {
    for (const uri of [
      "https://cdn.example.com/asset.png",
      "http://localhost:8000/asset.png",
      "data:image/png;base64,abc",
      "blob:https://app.example.com/id",
      "//cdn.example.com/asset.png",
    ]) {
      expect(resolveAssetUrl(uri)).toBe(uri);
    }
  });
});
