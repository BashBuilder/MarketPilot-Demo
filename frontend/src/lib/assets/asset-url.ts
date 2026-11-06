/**
 * Backend asset URIs come in two shapes. Hosted deployments return Cloudinary
 * HTTPS URLs, which the browser loads directly. Local deployments return file
 * names relative to the backend's asset directory (for example `fake-8b9a.png`),
 * which go through the same-origin asset proxy. Absolute web and inline URIs
 * keep working unchanged.
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
