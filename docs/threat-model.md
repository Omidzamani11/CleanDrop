# Threat model

## Protected assets

- the original file and its bytes;
- sensitive image pixels and PDF text;
- EXIF, XMP, GPS, document properties, attachments, annotations, and forms;
- raw OCR text and detected personal information;
- local paths that may reveal a user name or folder structure;
- integrity of a cleaned output and its verification report.

## Trust boundaries

Inputs are untrusted. File extensions, embedded actions, metadata values, PDF
objects, OCR output, filenames, and external-tool stderr are treated as
attacker-controlled. The local operating system, signed application process, and
libraries loaded by that process are trusted for this product boundary.

The desktop UI does not parse documents. Untrusted work runs in a separate worker
process. Tesseract and ExifTool are local subprocesses invoked with explicit
argument arrays and `shell=False`.

## Threats addressed

| Threat | Control |
|---|---|
| Misleading extension | Magic-byte detection |
| Original overwritten | Path policy, collision naming, atomic destination |
| Metadata copied into image | Fresh pixel buffer and re-encode |
| PDF text recoverable after visual rectangle | Rasterize and build a new image-only PDF |
| Active PDF content transferred | No source-object copy; structural verification |
| Raw PII in logs/reports | Masked preview and evidence hash |
| Full input path disclosed | Path hash in public report; raw path kept in local process memory |
| Command injection through a filename | Argument lists, `shell=False`, no document auto-open |
| Partial file left after cancellation | PID-scoped temp directories and cleanup |
| Excessive resource consumption | File, page, pixel, OCR, job, and batch limits |
| Unverified output presented as success | Enforced state machine and required checks |
| Symlink path confusion | Supported symlink inputs rejected |

## Explicit non-goals

CleanDrop:

- is **not a malware scanner or antivirus**;
- is **not a steganography detector**;
- does **not guarantee absolute or 100% security**;
- may miss or misread content because OCR can fail;
- does **not delete or securely erase the original file**;
- does **not make an infected or compromised operating system safe**;
- does not inspect DOCX, XLSX, encrypted PDFs, hidden filesystem streams, or
  unsupported formats;
- does not detect faces, watermarks, or every possible personal identifier;
- cannot stop another local process from reading a file while CleanDrop runs.

## Residual risks

- A visual identifier may not match a configured text detector.
- OCR may omit low-contrast, stylized, rotated, handwritten, or unsupported text.
- Raster output can still visibly contain sensitive content the user did not
  select or manually cover.
- The output filename itself may contain sensitive words chosen by the user.
- PDF rasterization trades semantic content and accessibility for a simpler
  sharing surface.
- Unsigned binaries can be imitated; users must verify the release source and digest.
- Dependencies may contain undiscovered vulnerabilities.

## Safe-use guidance

Review every finding and every page preview. Add manual rectangles for visual
details that text detectors cannot understand. Read warnings in the JSON report.
Share only the newly named cleaned copy. Keep the original in a protected
location and delete it separately if that is your intent.

The success statement means only:

> No sensitive data was detected under the selected verification policy.

It is not an assurance that the file contains no sensitive information.
