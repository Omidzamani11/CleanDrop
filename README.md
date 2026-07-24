# CleanDrop

> Clean files locally before you share them.

[فارسی](README.fa.md) · [Privacy](docs/privacy.md) ·
[Threat model](docs/threat-model.md) · [Verification policy](docs/verification-policy.md)

![CleanDrop Persian desktop interface](docs/assets/cleandrop-desktop-fa.png)

CleanDrop is a Windows desktop application and command-line tool for preparing
JPG, JPEG, PNG, and unencrypted PDF files for safer sharing. It detects metadata
and selected sensitive text, lets you review or add redactions, rebuilds a new
file from pixels, verifies the result, and writes a versioned JSON report.

The processing pipeline is enforced in this order:

`Inspect → Detect → Review → Plan → Sanitize → Verify → Report`

No file is reported as successfully cleaned unless verification has run.

## Why CleanDrop

- Local-first: files are never uploaded and the application contains no network client.
- Real type detection: input is identified from magic bytes, not its extension.
- Pixel reconstruction: images are decoded, orientation-corrected, copied to a new
  pixel buffer, redacted, and re-encoded without source metadata.
- Secure PDF flattening: every page is rasterized into a brand-new PDF; source
  objects, text layers, forms, annotations, attachments, actions, and scripts are
  not copied.
- Persian and English OCR: the Windows build includes Tesseract with `fas+eng`
  and orientation data.
- Review before action: automatic findings can be selected or deselected, and
  manual pixel redactions can be drawn on the preview.
- Verifiable outputs: every cleaned file is reopened and checked, with a
  SHA-256 digest and adjacent JSON report.
- Batch-ready: up to 100 files per job.
- Bilingual: Persian RTL and English LTR desktop interfaces.
- Automation-friendly: independent CLI with documented exit codes.

## Install on Windows

1. Download `CleanDrop-Setup-1.0.0.exe` from the
   [latest release](https://github.com/Omidzamani11/CleanDrop/releases/latest).
2. Compare its SHA-256 value with `SHA256SUMS.txt` from the same release.
3. Run the installer. CleanDrop installs for the current user and does not need
   administrator access.
4. Open **CleanDrop** from the Start menu.

The release also provides a portable ZIP. Extract the complete directory before
launching `CleanDrop.exe`; do not move the executable away from its `_internal`
directory.

The first public build is not code-signed. Windows SmartScreen may therefore show
an “unknown publisher” warning. Verify the release URL and checksum before
continuing. See [release verification](docs/verification-policy.md#verifying-a-download).

## Desktop workflow

1. Drop one or more supported files, or choose them with the file picker.
2. Wait for local inspection and OCR.
3. Review detected items and draw any extra rectangles on the preview.
4. Choose an output folder and PDF DPI (`150`, `200`, or `300`).
5. Create cleaned copies.
6. Review the verification checks and JSON report.

Original files are never overwritten or deleted.

## CLI

The installer includes `cleandrop-cli.exe`. From the installation directory:

```powershell
.\cleandrop-cli.exe doctor
.\cleandrop-cli.exe inspect .\sample.jpg --json
.\cleandrop-cli.exe sanitize .\document.pdf --profile secure-flatten --dpi 200 --output .\document.cleaned.pdf
.\cleandrop-cli.exe verify .\document.cleaned.pdf --policy secure-share --json
.\cleandrop-cli.exe batch .\one.jpg .\two.png --output-dir .\cleaned --json
```

Exit codes:

| Code | Meaning |
|---:|---|
| `0` | Completed with all required checks passing |
| `2` | Completed with warnings from optional or limited checks |
| `10` | Invalid input or request |
| `20` | Inspection or processing failed |
| `30` | Verification failed |
| `40` | Cancelled |
| `70` | Unexpected internal failure |

## Supported formats

| Input | Sanitization |
|---|---|
| JPG / JPEG | Orientation-aware pixel rebuild and JPEG re-encode |
| PNG | Pixel rebuild and PNG re-encode |
| Unencrypted PDF | Full-page rasterization and new image-only PDF |

Encrypted PDFs, office documents, mobile apps, cloud storage, accounts, LLMs,
AI APIs, face detection, malware scanning, steganography detection, browser
extensions, and watermark removal are intentionally out of scope.

See [supported formats](docs/supported-formats.md) for details and limits.

## Privacy and security

CleanDrop performs no uploads, analytics, update checks, account login, or remote
API calls. Tesseract and ExifTool are launched locally with argument lists and
`shell=False`. Public reports contain masked previews and evidence hashes rather
than raw OCR or PII values.

CleanDrop is not a malware scanner, does not detect steganography, and cannot
guarantee that every sensitive item is found. OCR can be wrong. A compromised
operating system is outside the protection boundary. Always review the preview
and verification report before sharing.

Use this wording for a successful policy result:

> No sensitive data was detected under the selected verification policy.

Never interpret it as a guarantee of “100% safe.”

## Development

Requirements: Python 3.12, Git, and Windows build tools for release packaging.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy src\cleandrop
```

Run the desktop application:

```powershell
.\.venv\Scripts\python.exe -m cleandrop
```

Build a Windows release:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\provision_windows_tools.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

More detail is in [development.md](docs/development.md) and
[architecture.md](docs/architecture.md).

## Roadmap

The 1.x roadmap stays within the product boundary:

- signed Windows releases and reproducible provenance;
- broader adversarial PDF fixtures and fuzzing;
- accessibility and keyboard-navigation improvements;
- faster large-batch processing with the same verification policy;
- additional local-only metadata rules and translations.

Excluded features remain excluded unless the threat model and product scope are
deliberately revised.

## License

CleanDrop is free software licensed under
**GNU Affero General Public License v3.0 or later** (`AGPL-3.0-or-later`).
This license choice is compatible with the use of PyMuPDF under AGPL.
See [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
