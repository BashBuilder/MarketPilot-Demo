/**
 * Security headers are built here rather than inline in next.config so the
 * policy can be unit-tested and the API origin is derived from the same
 * environment variable the API client uses.
 */

export const DEFAULT_API_URL = "http://localhost:8000/api/v1";

export interface SecurityHeader {
  key: string;
  value: string;
}

export interface SecurityHeaderOptions {
  apiUrl?: string;
  isDevelopment?: boolean;
}

function apiOrigin(apiUrl: string | undefined): string | null {
  const value = apiUrl?.trim();
  if (!value) return null;

  try {
    return new URL(value).origin;
  } catch {
    return null;
  }
}

export function securityHeaders(
  options: SecurityHeaderOptions = {},
): SecurityHeader[] {
  const origin = apiOrigin(options.apiUrl ?? DEFAULT_API_URL);
  const isDevelopment = options.isDevelopment ?? false;

  const contentSecurityPolicy = [
    "default-src 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "form-action 'self'",
    `img-src 'self'${origin ? ` ${origin}` : ""} data: blob:`,
    `connect-src 'self'${origin ? ` ${origin}` : ""}${
      isDevelopment ? " ws: wss:" : ""
    }`,
    `script-src 'self' 'unsafe-inline'${isDevelopment ? " 'unsafe-eval'" : ""}`,
    "style-src 'self' 'unsafe-inline'",
    "font-src 'self'",
    "worker-src 'self' blob:",
    "manifest-src 'self'",
  ].join("; ");

  return [
    { key: "Content-Security-Policy", value: contentSecurityPolicy },
    { key: "X-Content-Type-Options", value: "nosniff" },
    {
      key: "Referrer-Policy",
      value: "strict-origin-when-cross-origin",
    },
    { key: "X-Frame-Options", value: "DENY" },
  ];
}
