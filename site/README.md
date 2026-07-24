# CleanDrop download site

Public, Persian-first download page for CleanDrop 1.0.

## Purpose

- Explain the local-first privacy model without overstating safety.
- Offer the signed-off Windows installer, portable ZIP, and checksum file.
- Show the real Persian desktop interface.
- Link to the public source, security policy, and AGPL license.

The site has no uploads, accounts, database, analytics, or application API.
CleanDrop processing happens only inside the installed Windows application.

## Local development

Requires Node.js 22.13 or newer.

```bash
npm ci
npm run dev
```

The default build targets OpenAI Sites:

```bash
npm run build
npm test
```

The alternative Vercel build uses the same Next.js source:

```bash
npm run build:vercel
```

## Release synchronization

Before publishing a new CleanDrop release, update these values together:

- filenames and version in `app/page.tsx`
- installer SHA-256 in `app/page.tsx`
- release assets on GitHub
- package version in `package.json`

The rendered-page tests guard the current version, filenames, and checksum.
