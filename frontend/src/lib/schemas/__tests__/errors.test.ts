import { describe, expect, it } from "vitest";
import { apiErrorBody } from "@/lib/schemas";

describe("API error schema", () => {
  it("parses the contract error envelope", () => {
    expect(
      apiErrorBody.safeParse({
        error: {
          code: "validation_error",
          message: "Idea is required",
          details: [{ path: ["idea"], message: "Required" }],
        },
      }).success,
    ).toBe(true);
  });

  it("allows details to be omitted", () => {
    expect(
      apiErrorBody.safeParse({
        error: { code: "not_found", message: "Campaign not found" },
      }).success,
    ).toBe(true);
  });

  it("rejects a missing message", () => {
    expect(
      apiErrorBody.safeParse({ error: { code: "not_found" } }).success,
    ).toBe(false);
  });

  it("rejects a non-object payload", () => {
    expect(apiErrorBody.safeParse("not an error").success).toBe(false);
  });
});
