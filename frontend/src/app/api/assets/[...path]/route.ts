import { readFile } from "node:fs/promises";
import { assetRoot, resolveLocalAsset } from "@/lib/assets/local-file";

interface AssetRouteContext {
  params: Promise<{ path: string[] }>;
}

/**
 * Same-origin proxy for backend-generated images. The backend contract exposes
 * relative asset URIs but no HTTP asset endpoint, so the frontend serves the
 * shared asset directory when it is configured.
 */
export async function GET(
  _request: Request,
  { params }: AssetRouteContext,
): Promise<Response> {
  const { path: segments } = await params;
  const root = assetRoot();
  if (!root) {
    return new Response("Asset proxy is not configured", { status: 404 });
  }

  try {
    const file = await resolveLocalAsset(root, segments);
    if (!file) return new Response("Not found", { status: 404 });

    const body = await readFile(file.path);
    return new Response(new Uint8Array(body), {
      headers: {
        "Cache-Control": "private, max-age=300",
        "Content-Type": file.contentType,
        "X-Content-Type-Options": "nosniff",
      },
    });
  } catch {
    return new Response("Not found", { status: 404 });
  }
}
