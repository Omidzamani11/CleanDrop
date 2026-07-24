# Supported formats and limits

## Formats

| Format | Accepted | Inspection | Output strategy |
|---|---:|---|---|
| JPG / JPEG | Yes | EXIF, extended metadata, OCR, PII | Orientation-aware RGB pixel rebuild |
| PNG | Yes | text chunks, extended metadata, OCR, PII | RGB/RGBA pixel rebuild |
| PDF without password | Yes | structure, text layer, scanned-page OCR | Secure flatten to image-only PDF |
| Encrypted PDF | No | Safely rejected | None |
| DOCX / XLSX / other office formats | No | Safely rejected | None |
| Other images | No | Safely rejected | None |

An extension is not authoritative. A `.jpg` containing PDF bytes is treated as
PDF; unknown magic bytes are rejected.

## Default limits

| Limit | Default |
|---|---:|
| File size | 500 MB |
| PDF pages | 500 |
| Image pixels | 150,000,000 |
| OCR per page | 60 seconds |
| Total job | 30 minutes |
| Batch | 100 files |

Values are represented by validated `ResourceLimits`. All values must be
positive. The public 1.0 UI uses the documented defaults; programmatic callers
can inject different validated limits.

## PDF quality

- `150 DPI`: smaller and faster; useful for screen sharing.
- `200 DPI`: default balance.
- `300 DPI`: larger and slower; useful for small print.

Secure flatten intentionally removes selectable text, form behavior, links,
annotations, attachments, JavaScript, launch actions, and embedded files. This
also reduces PDF accessibility and searchability.

## OCR

The Windows package contains `fas`, `eng`, and `osd` data. OCR uses `fas+eng`;
orientation detection is attempted with OSD. OCR is best-effort and can miss
handwriting, decorative fonts, poor scans, low contrast, or unsupported scripts.
The application remains usable without OCR but records a warning.
