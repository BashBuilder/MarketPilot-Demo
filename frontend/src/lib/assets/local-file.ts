import { realpath, stat } from "node:fs/promises";
import path from "node:path";

const CONTENT_TYPES: Readonly<Record<string, string>> = {
  ".avif": "image/avif",
  ".gif": "image/gif",
  ".jpeg": "image/jpeg",
  ".jpg": "image/jpeg",
  ".png": "image/png",
  ".webp": "image/webp",
};

export interface LocalAssetFile {
  path: string;
  contentType: string;
}

/** The backend asset directory, when an operator has shared it with Next. */
export function assetRoot(): string | null {
  const configured = process.env.BACKEND_ASSET_DIR?.trim();
  return configured ? path.resolve(configured) : null;
}

/**
 * Resolve a requested asset only when it stays inside the configured root and
 * is a supported image. Symlinks are resolved before the containment check so
 * they cannot be used to escape the directory.
 */
export async function resolveLocalAsset(
  root: string,
  segments: readonly string[],
): Promise<LocalAssetFile | null> {
  if (segments.length === 0) return null;

  try {
    const resolvedRoot = await realpath(root);
    const candidate = path.resolve(resolvedRoot, ...segments);
    if (!isInside(resolvedRoot, candidate)) return null;

    const resolved = await realpath(candidate);
    if (!isInside(resolvedRoot, resolved)) return null;

    const info = await stat(resolved);
    if (!info.isFile()) return null;

    const contentType = CONTENT_TYPES[path.extname(resolved).toLowerCase()];
    return contentType ? { path: resolved, contentType } : null;
  } catch {
    return null;
  }
}

function isInside(root: string, target: string): boolean {
  const relative = path.relative(root, target);
  return relative !== "" && !relative.startsWith("..") && !path.isAbsolute(relative);
}
