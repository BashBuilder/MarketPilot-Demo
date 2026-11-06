/**
 * Backend asset URIs are usually file names relative to the backend's asset
 * directory (for example `fake-8b9a.png`), not browser URLs. Absolute web
 * URIs keep working; everything else goes through the same-origin asset proxy,
 * which serves the configured backend asset directory.
 */
const ABSOLUTE_URI = /^(?:https?:|data:|blob:|\/\/)/i;

export function resolveAssetUrl(uri: string): string {
  if (ABSOLUTE_URI.test(uri)) {
    return uri;
  }

  const segments = uri
    .replace(/^\/+/, "")
    .split("/")
    .filter(Boolean)
    .map(encodeURIComponent);

  return `/api/assets/${segments.join("/")}`;
}
