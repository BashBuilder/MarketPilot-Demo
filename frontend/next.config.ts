import type { NextConfig } from "next";
import { securityHeaders } from "./src/lib/security/headers";

const nextConfig: NextConfig = {
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: securityHeaders({
          apiUrl: process.env.NEXT_PUBLIC_API_URL,
          isDevelopment: process.env.NODE_ENV !== "production",
        }),
      },
    ];
  },
  turbopack: {
    // MSW 3 marks `msw/browser` as null under the node condition, which makes
    // Turbopack reject the client component during its SSR build. Point at the
    // browser entry directly; it is only executed by MockProvider's effect.
    resolveAlias: {
      "msw/browser": "./node_modules/msw/lib/browser/index.js",
    },
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
