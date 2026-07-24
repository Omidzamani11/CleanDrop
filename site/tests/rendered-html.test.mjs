import assert from "node:assert/strict";
import { access, readFile, stat } from "node:fs/promises";
import test from "node:test";

const siteRoot = new URL("../", import.meta.url);

async function render(host = "cleandrop.example") {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request(`https://${host}/`, {
      headers: {
        accept: "text/html",
        host,
        "x-forwarded-host": host,
        "x-forwarded-proto": "https",
      },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the complete Persian CleanDrop download page", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<html[^>]*lang="fa"[^>]*dir="rtl"/i);
  assert.match(html, /<title>CleanDrop — پاک‌سازی خصوصی تصویر و PDF<\/title>/);
  assert.match(html, /قبل از ارسال/);
  assert.match(html, /پردازش کاملاً محلی/);
  assert.match(html, /CleanDrop-Setup-1\.0\.0\.exe/);
  assert.match(html, /CleanDrop-1\.0\.0-win-x64\.zip/);
  assert.match(html, /SHA256SUMS\.txt/);
  assert.match(html, /Windows SmartScreen/);
  assert.match(html, /AGPL-3\.0-or-later/);
  assert.doesNotMatch(html, /Your site is taking shape|codex-preview/);
});

test("derives social metadata from the request host", async () => {
  const response = await render("download.cleandrop.test");
  const html = await response.text();

  assert.match(
    html,
    /<meta[^>]+property="og:image"[^>]+content="https:\/\/download\.cleandrop\.test\/og\.png"/i,
  );
  assert.match(
    html,
    /<meta[^>]+name="twitter:card"[^>]+content="summary_large_image"/i,
  );
});

test("ships the real desktop screenshot, brand mark, and social card", async () => {
  const assets = [
    ["public/cleandrop-desktop-fa.png", 30_000],
    ["public/cleandrop-icon.png", 100_000],
    ["public/og.png", 100_000],
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

test("keeps download links and checksum synchronized with the release", async () => {
  const page = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");

  assert.match(
    page,
    /releases\/latest\/download/,
  );
  assert.match(
    page,
    /9e1109ff296a887d875837ff6b35898fb265e297d29979febc21bc0e51ff15d6/,
  );
  assert.doesNotMatch(page, /react-loading-skeleton|SkeletonPreview/);
});
