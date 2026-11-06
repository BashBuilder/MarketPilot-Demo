import { mkdtemp, mkdir, realpath, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { resolveLocalAsset } from "@/lib/assets/local-file";

const roots: string[] = [];

async function makeRoot(): Promise<string> {
  const root = await mkdtemp(path.join(tmpdir(), "marketpilot-assets-"));
  roots.push(root);
  return root;
}

afterEach(async () => {
  await Promise.all(
    roots.splice(0).map((root) => rm(root, { recursive: true, force: true })),
  );
});

describe("resolveLocalAsset", () => {
  it("resolves an image inside the configured root", async () => {
    const root = await makeRoot();
    await writeFile(path.join(root, "hero.png"), new Uint8Array([137, 80, 78, 71]));

    const file = await resolveLocalAsset(root, ["hero.png"]);

    expect(file?.contentType).toBe("image/png");
    expect(file?.path).toBe(await realpath(path.join(root, "hero.png")));
  });

  it("rejects path traversal and missing files", async () => {
    const root = await makeRoot();
    await mkdir(path.join(root, "nested"));
    await writeFile(path.join(root, "nested", "note.txt"), "not an image");

    expect(await resolveLocalAsset(root, ["..", "secret.png"])).toBeNull();
    expect(await resolveLocalAsset(root, ["nested", "note.txt"])).toBeNull();
    expect(await resolveLocalAsset(root, ["missing.png"])).toBeNull();
    expect(await resolveLocalAsset(root, [])).toBeNull();
  });
});
