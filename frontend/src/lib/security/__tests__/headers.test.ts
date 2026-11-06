import { describe, expect, it } from "vitest";
import {
  DEFAULT_API_URL,
  securityHeaders,
  type SecurityHeader,
} from "@/lib/security/headers";

function headerMap(headers: readonly SecurityHeader[]): Map<string, string> {
  return new Map(headers.map(({ key, value }) => [key, value]));
}

function directives(policy: string): Map<string, string> {
  return new Map(
    policy.split(";").map((directive) => {
      const [name, ...values] = directive.trim().split(/\s+/);
      return [name, values.join(" ")];
    }),
  );
}

describe("securityHeaders", () => {
  it("sets every required security header", () => {
    const headers = headerMap(securityHeaders({ apiUrl: DEFAULT_API_URL }));

    expect(headers.get("Content-Security-Policy")).toBeTruthy();
    expect(headers.get("X-Content-Type-Options")).toBe("nosniff");
    expect(headers.get("Referrer-Policy")).toBe(
      "strict-origin-when-cross-origin",
    );
    expect(headers.get("X-Frame-Options")).toBe("DENY");
  });

  it("allows the API origin for fetches and images", () => {
    const headers = headerMap(
      securityHeaders({ apiUrl: "https://api.example.com/api/v1" }),
    );
    const policy = directives(headers.get("Content-Security-Policy") ?? "");

    expect(policy.get("connect-src")).toContain("'self'");
    expect(policy.get("connect-src")).toContain("https://api.example.com");
    expect(policy.get("img-src")).toContain("'self'");
    expect(policy.get("img-src")).toContain("https://api.example.com");
    expect(policy.get("frame-ancestors")).toBe("'none'");
    expect(policy.get("object-src")).toBe("'none'");
  });

  it("only relaxes script and socket rules in development", () => {
    const production = directives(
      headerMap(
        securityHeaders({ apiUrl: DEFAULT_API_URL, isDevelopment: false }),
      ).get("Content-Security-Policy") ?? "",
    );
    const development = directives(
      headerMap(
        securityHeaders({ apiUrl: DEFAULT_API_URL, isDevelopment: true }),
      ).get("Content-Security-Policy") ?? "",
    );

    expect(production.get("script-src")).not.toContain("'unsafe-eval'");
    expect(production.get("connect-src")).not.toContain("ws:");
    expect(development.get("script-src")).toContain("'unsafe-eval'");
    expect(development.get("connect-src")).toContain("ws:");
  });

  it("falls back to a same-origin policy when the API URL is invalid", () => {
    const policy = directives(
      headerMap(securityHeaders({ apiUrl: "not a url" })).get(
        "Content-Security-Policy",
      ) ?? "",
    );

    expect(policy.get("connect-src")).toBe("'self'");
    expect(policy.get("img-src")).toBe("'self' data: blob:");
  });
});
