# Verification policy

CleanDrop verifies the temporary output before atomically publishing it. A failed
required check prevents a successful result. An unavailable optional external
check produces `COMPLETED_WITH_WARNINGS`.

## Checks

| Check | Applies to | Requirement |
|---|---|---|
| `OUTPUT_EXISTS` | All | Temporary output exists |
| `OUTPUT_NON_EMPTY` | All | Output has bytes |
| `OUTPUT_REOPENABLE` | All | Primary parser can reopen it |
| `MEDIA_TYPE_MATCH` | All | Encoded type matches the selected output |
| `PAGE_COUNT_MATCH` | PDF | Output page count equals source |
| `DIMENSIONS_VALID` | Images | Orientation-corrected dimensions match |
| `NO_BLOCKED_METADATA` | All | Blocked metadata is absent |
| `NO_XMP` | All | XMP is absent |
| `NO_ATTACHMENTS` | PDF | No embedded files |
| `NO_JAVASCRIPT` | PDF | No JavaScript name tree |
| `NO_LAUNCH_ACTION` | PDF | No open or additional root action |
| `NO_FORMS` | PDF | No AcroForm |
| `NO_ANNOTATIONS` | PDF | No annotation |
| `NO_NATIVE_TEXT_IN_SECURE_PDF` | PDF | No extractable native text |
| `REDACTION_REGIONS_APPLIED` | Redactions | At least 94% of crop pixels match black fill tolerance |
| `REDACTION_OCR_CLEAN` | Redactions | A second OCR pass finds no confident residual text |
| `OUTPUT_HASH_CREATED` | All | SHA-256 digest exists |
| `EXIFTOOL_NO_BLOCKED_METADATA` | All | ExifTool confirms blocked keys are absent |

If ExifTool or redaction-crop OCR is unavailable, the corresponding check is a
warning and the result cannot be a warning-free completion. Structural PDF checks
and primary parser checks are required.

## Status meanings

- `PASSED`: all required and available checks passed.
- `PASSED_WITH_WARNINGS`: required checks passed, but an optional check was
  unavailable or limited.
- `FAILED`: at least one required check failed.

The policy does not assert that every sensitive item was detected. It verifies
the transformations selected by the user and the absence of known blocked
structures.

## Verifying a download

PowerShell:

```powershell
Get-FileHash .\CleanDrop-Setup-1.0.0.exe -Algorithm SHA256
```

Compare the full hexadecimal value with the matching line in
`SHA256SUMS.txt` attached to the same GitHub Release. Do not use a checksum copied
from an unrelated website or message.

## Verifying a cleaned file

```powershell
.\cleandrop-cli.exe verify .\document.cleaned.pdf --policy secure-share --json
```

For the strongest comparison, also pass the source:

```powershell
.\cleandrop-cli.exe verify .\document.cleaned.pdf --source .\document.pdf --policy secure-share --json
```

The adjacent `*.cleandrop.json` report stores the output hash and check statuses.
