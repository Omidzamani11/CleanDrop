import assert from "node:assert/strict";
import { access, readFile, stat } from "node:fs/promises";
import test from "node:test";

const siteRoot = new URL("../", import.meta.url);

test("exports a complete GitHub Pages download site under /CleanDrop", async () => {
  const htmlUrl = new URL("out/index.html", siteRoot);
  await access(htmlUrl);
  const html = await readFile(htmlUrl, "utf8");

  assert.match(html, /<html[^>]*lang="fa"[^>]*dir="rtl"/i);
  assert.match(
    html,
    /<meta[^>]+property="og:image"[^>]+content="https:\/\/omidzamani11\.github\.io\/CleanDrop\/og\.png"/i,
  );
  assert.match(html, /\/CleanDrop\/_next\/static\//);
  assert.match(html, /\/CleanDrop\/cleandrop-icon\.png/);
  assert.match(html, /\/CleanDrop\/cleandrop-desktop-fa\.png/);
  assert.match(html, /releases\/latest\/download\/CleanDrop-Setup-1\.0\.0\.exe/);
  assert.match(html, /releases\/latest\/download\/CleanDrop-1\.0\.0-win-x64\.zip/);
  assert.match(html, /releases\/latest\/download\/SHA256SUMS\.txt/);
  assert.doesNotMatch(html, /src="\/cleandrop-/);
});

test("includes every required static image asset", async () => {
  const assets = [
    ["out/cleandrop-desktop-fa.png", 30_000],
    ["out/cleandrop-icon.png", 100_000],
    ["out/og.png", 100_000],
  ];

  for (const [relativePath, minimumBytes] of assets) {
    const assetUrl = new URL(relativePath, siteRoot);
    await access(assetUrl);
    const details = await stat(assetUrl);
    assert.ok(
      details.size >= minimumBytes,
      `${relativePath} should be a real image asset`,
    );
  }
});
