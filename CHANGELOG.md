# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and semantic versioning.

## [1.0.0] - 2026-07-24

### Added

- Windows desktop application with Persian RTL and English LTR interfaces.
- Magic-byte inspection for JPG, JPEG, PNG, and unencrypted PDF.
- Local metadata inspection with Pillow, pikepdf, and bundled ExifTool.
- Persian and English OCR through bundled Tesseract `fas+eng` and OSD.
- Detectors for email, phone, URL, Luhn-valid cards, Iranian national IDs, and GPS.
- Review screen with finding selection, PDF page navigation, zoom, and manual redaction.
- Orientation-aware image pixel rebuild and image verification.
- PDF secure flattening with structural active-content detection.
- Redaction verification by pixel coverage and a second OCR pass on selected regions.
- Batch processing, safe cancellation, isolated workers, JSONL events, and atomic outputs.
- CLI commands: `inspect`, `sanitize`, `verify`, `batch`, and `doctor`.
- Versioned privacy-preserving JSON reports with input and output SHA-256 values.
- PyInstaller, Inno Setup, CI, security scanning, and tagged-release automation.

### Security

- Original files are never overwritten.
- Public events and reports do not include raw OCR/PII values or full input paths.
- Encrypted, damaged, oversized, and symlinked inputs are rejected safely.
- Verification is mandatory before a job can enter a successful terminal state.
