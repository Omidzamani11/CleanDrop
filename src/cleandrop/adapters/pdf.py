from __future__ import annotations

import hashlib
import os
import tempfile
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any

import fitz
import pikepdf
from PIL import Image, ImageDraw

from cleandrop.adapters.metadata import ExifToolMetadataInspector
from cleandrop.adapters.ocr import OcrToken, TesseractOcrEngine
from cleandrop.adapters.redaction_verification import verify_redaction_crops_with_ocr
from cleandrop.detectors.pii import DetectorSuite
from cleandrop.domain.errors import (
    ExternalToolError,
    InspectionError,
    ResourceLimitError,
    SanitizationError,
    VerificationError,
)
from cleandrop.domain.models import (
    CheckStatus,
    Finding,
    FindingKind,
    FindingSource,
    InspectionReport,
    MediaType,
    NormalizedRect,
    RedactionRegion,
    ResourceLimits,
    SanitizationPlan,
    Severity,
    VerificationCheck,
    VerificationResult,
    VerificationStatus,
)
from cleandrop.security.paths import hash_path, sha256_file


def _finding(
    kind: FindingKind,
    source: FindingSource,
    key: str,
    value: str,
    page_index: int | None = None,
    rect: NormalizedRect | None = None,
    severity: Severity = Severity.HIGH,
) -> Finding:
    evidence = f"{key}:{value}"
    return Finding(
        id=str(uuid.uuid4()),
        kind=kind,
        source=source,
        severity=severity,
        confidence=1.0,
        masked_preview=f"{key}: [hidden]",
        evidence_hash=hashlib.sha256(evidence.encode("utf-8", errors="replace")).hexdigest(),
        page_index=page_index,
        rect=rect,
        metadata_key=key if source is FindingSource.METADATA else None,
    )


def _root_has(root: Any, name: str) -> bool:
    try:
        return name in root
    except (TypeError, ValueError):
        return False


def _structure_findings(pdf: pikepdf.Pdf) -> list[Finding]:
    findings: list[Finding] = []
    for key, value in pdf.docinfo.items():
        findings.append(
            _finding(FindingKind.METADATA, FindingSource.METADATA, str(key), str(value))
        )
    root = pdf.Root
    if _root_has(root, "/Metadata"):
        findings.append(_finding(FindingKind.METADATA, FindingSource.METADATA, "XMP", "present"))
    for key in ("/OpenAction", "/AA"):
        if _root_has(root, key):
            findings.append(
                _finding(FindingKind.PDF_ACTION, FindingSource.STRUCTURE, key[1:], "present")
            )
    if _root_has(root, "/AcroForm"):
        findings.append(
            _finding(FindingKind.PDF_FORM, FindingSource.STRUCTURE, "AcroForm", "present")
        )
    try:
        attachment_names = list(pdf.attachments)
    except (AttributeError, TypeError, ValueError):
        attachment_names = []
    for name in attachment_names:
        findings.append(
            _finding(
                FindingKind.PDF_ATTACHMENT,
                FindingSource.STRUCTURE,
                "Attachment",
                str(name),
                severity=Severity.CRITICAL,
            )
        )
    try:
        names = root.get("/Names")
        if names is not None and "/JavaScript" in names:
            findings.append(
                _finding(
                    FindingKind.PDF_JAVASCRIPT,
                    FindingSource.STRUCTURE,
                    "JavaScript",
                    "present",
                    severity=Severity.CRITICAL,
                )
            )
    except (AttributeError, TypeError, ValueError):
        pass
    for page_index, page in enumerate(pdf.pages):
        try:
            annotations = page.obj.get("/Annots")
        except (AttributeError, TypeError, ValueError):
            annotations = None
        if annotations:
            findings.append(
                _finding(
                    FindingKind.PDF_ANNOTATION,
                    FindingSource.STRUCTURE,
                    "Annotation",
                    f"page-{page_index + 1}",
                    page_index=page_index,
                )
            )
    return findings


def _ocr_line_groups(tokens: list[OcrToken]) -> list[tuple[str, int, NormalizedRect]]:
    grouped: dict[tuple[int, int, int, int], list[OcrToken]] = {}
    for token in tokens:
        key = (token.page_index, token.block, token.paragraph, token.line)
        grouped.setdefault(key, []).append(token)
    results: list[tuple[str, int, NormalizedRect]] = []
    for line_tokens in grouped.values():
        left = min(token.rect.x for token in line_tokens)
        top = min(token.rect.y for token in line_tokens)
        right = max(token.rect.x + token.rect.width for token in line_tokens)
        bottom = max(token.rect.y + token.rect.height for token in line_tokens)
        results.append(
            (
                " ".join(token.text for token in line_tokens),
                line_tokens[0].page_index,
                NormalizedRect(
                    left,
                    top,
                    max(0.000001, min(1 - left, right - left)),
                    max(0.000001, min(1 - top, bottom - top)),
                ),
            )
        )
    return results


class PdfMediaAdapter:
    def __init__(
        self,
        ocr: TesseractOcrEngine | None = None,
        metadata: ExifToolMetadataInspector | None = None,
        detectors: DetectorSuite | None = None,
    ) -> None:
        self.ocr = ocr or TesseractOcrEngine()
        self.metadata = metadata or ExifToolMetadataInspector()
        self.detectors = detectors or DetectorSuite()

    def inspect(
        self,
        path: Path,
        limits: ResourceLimits,
        run_ocr: bool = True,
    ) -> InspectionReport:
        warnings: list[str] = []
        try:
            extended_metadata = self.metadata.inspect(path)
        except ExternalToolError as exc:
            extended_metadata = {}
            warnings.append(f"Extended metadata inspection was limited: {type(exc).__name__}")
        try:
            with pikepdf.open(path) as structural:
                if structural.is_encrypted:
                    raise InspectionError("Encrypted PDF files are not supported")
                structure_findings = _structure_findings(structural)
            document = fitz.open(path)
        except (pikepdf.PdfError, pikepdf.PasswordError, fitz.FileDataError, OSError) as exc:
            raise InspectionError("The PDF is damaged, encrypted, or unsupported") from exc
        try:
            if document.page_count > limits.max_pdf_pages:
                raise ResourceLimitError("PDF exceeds the configured page limit")
            findings = list(structure_findings)
            existing_metadata_keys = {
                str(finding.metadata_key).lower() for finding in findings if finding.metadata_key
            }
            for key, value in extended_metadata.items():
                lowered = key.lower()
                if lowered in existing_metadata_keys:
                    continue
                if any(
                    marker in lowered
                    for marker in (
                        "author",
                        "title",
                        "subject",
                        "keywords",
                        "xmp",
                        "gps",
                        "location",
                        "latitude",
                        "longitude",
                        "creator",
                    )
                ):
                    kind = (
                        FindingKind.GPS
                        if any(
                            marker in lowered
                            for marker in ("gps", "location", "latitude", "longitude")
                        )
                        else FindingKind.METADATA
                    )
                    findings.append(_finding(kind, FindingSource.METADATA, key, str(value)))
            dimensions: list[tuple[int, int]] = []
            for page_index, page in enumerate(document):
                page_rect = page.rect
                dimensions.append((round(page_rect.width), round(page_rect.height)))
                blocks = page.get_text("blocks")
                native_text_length = 0
                for block in blocks:
                    x0, y0, x1, y1, text = block[:5]
                    text_value = str(text).strip()
                    native_text_length += len(text_value)
                    if not text_value or page_rect.width <= 0 or page_rect.height <= 0:
                        continue
                    rect = NormalizedRect(
                        max(0.0, x0 / page_rect.width),
                        max(0.0, y0 / page_rect.height),
                        max(0.000001, min(1 - x0 / page_rect.width, (x1 - x0) / page_rect.width)),
                        max(0.000001, min(1 - y0 / page_rect.height, (y1 - y0) / page_rect.height)),
                    )
                    findings.extend(
                        self.detectors.detect(
                            text_value,
                            FindingSource.TEXT_LAYER,
                            page_index,
                            rect,
                        )
                    )
                if run_ocr and native_text_length < 8:
                    if not self.ocr.available:
                        warnings.append(f"OCR unavailable for scanned page {page_index + 1}")
                        continue
                    with tempfile.TemporaryDirectory(prefix="cleandrop-ocr-") as temp_dir:
                        preview = Path(temp_dir) / f"page-{page_index + 1}.png"
                        self.render_page(path, page_index, 200, preview)
                        try:
                            tokens = self.ocr.extract(
                                preview,
                                page_index,
                                timeout_seconds=limits.max_ocr_seconds_per_page,
                            )
                        except (ExternalToolError, OSError, ValueError) as exc:
                            warnings.append(
                                f"OCR failed for page {page_index + 1}: {type(exc).__name__}"
                            )
                            continue
                        for text, token_page, rect in _ocr_line_groups(tokens):
                            findings.extend(
                                self.detectors.detect(
                                    text,
                                    FindingSource.OCR,
                                    token_page,
                                    rect,
                                )
                            )
            return InspectionReport(
                input_path_hash=hash_path(path),
                input_name=path.name,
                input_sha256=sha256_file(path),
                media_type=MediaType.PDF,
                size_bytes=path.stat().st_size,
                page_count=document.page_count,
                dimensions=dimensions,
                findings=findings,
                capabilities={"ocr": self.ocr.available, "exiftool": self.metadata.available},
                warnings=warnings,
            )
        finally:
            document.close()

    def render_page(self, path: Path, page_index: int, dpi: int, output: Path) -> Path:
        with fitz.open(path) as document:
            if page_index < 0 or page_index >= document.page_count:
                raise IndexError("PDF page index is out of range")
            pixmap = document[page_index].get_pixmap(dpi=dpi, alpha=False)
            output.parent.mkdir(parents=True, exist_ok=True)
            pixmap.save(output)
        return output

    def sanitize(self, source: Path, plan: SanitizationPlan) -> Path:
        output = Path(plan.output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            with (
                fitz.open(source) as original,
                tempfile.TemporaryDirectory(
                    prefix=f".cleandrop-{os.getpid()}-",
                    dir=output.parent,
                ) as temp_dir,
            ):
                temp_path = Path(temp_dir) / output.name
                cleaned = fitz.open()
                try:
                    for page_index, source_page in enumerate(original):
                        pixmap = source_page.get_pixmap(dpi=plan.dpi, alpha=False)
                        image = Image.open(BytesIO(pixmap.tobytes("png"))).convert("RGB")
                        draw = ImageDraw.Draw(image)
                        for region in plan.redactions:
                            if region.page_index == page_index:
                                draw.rectangle(
                                    region.rect.to_pixels(*image.size),
                                    fill=(0, 0, 0),
                                )
                        buffer = BytesIO()
                        image.save(buffer, format="PNG", optimize=True)
                        page = cleaned.new_page(
                            width=source_page.rect.width,
                            height=source_page.rect.height,
                        )
                        page.insert_image(page.rect, stream=buffer.getvalue())
                    cleaned.set_metadata({})
                    cleaned.save(
                        temp_path,
                        garbage=4,
                        deflate=True,
                        clean=True,
                    )
                finally:
                    cleaned.close()
                verification = self.verify(source, temp_path, plan.redactions)
                if not verification.passed:
                    raise VerificationError("The rebuilt PDF did not pass verification")
                os.replace(temp_path, output)
        except (fitz.FileDataError, OSError, ValueError) as exc:
            raise SanitizationError("PDF secure flatten failed") from exc
        return output

    def verify(
        self,
        source: Path,
        output: Path,
        redactions: list[RedactionRegion],
    ) -> VerificationResult:
        checks: list[VerificationCheck] = []

        def add(name: str, condition: bool, message: str = "") -> None:
            checks.append(
                VerificationCheck(
                    name,
                    CheckStatus.PASSED if condition else CheckStatus.FAILED,
                    message,
                )
            )

        add("OUTPUT_EXISTS", output.exists())
        add("OUTPUT_NON_EMPTY", output.exists() and output.stat().st_size > 0)
        add("MEDIA_TYPE_MATCH", output.exists() and output.read_bytes()[:5] == b"%PDF-")
        source_pages = -1
        output_pages = -2
        native_text = ""
        annotations = 0
        redactions_ok = True
        redaction_crops: list[Image.Image] = []
        try:
            with fitz.open(source) as original, fitz.open(output) as cleaned:
                source_pages = original.page_count
                output_pages = cleaned.page_count
                native_text = "".join(page.get_text() for page in cleaned)
                annotations = sum(1 for page in cleaned for _annotation in (page.annots() or []))
                for region in redactions:
                    if region.page_index >= cleaned.page_count:
                        redactions_ok = False
                        continue
                    page = cleaned[region.page_index]
                    pixmap = page.get_pixmap(dpi=150, alpha=False)
                    image = Image.open(BytesIO(pixmap.tobytes("png"))).convert("RGB")
                    crop = image.crop(region.rect.to_pixels(*image.size))
                    redaction_crops.append(crop.copy())
                    pixel_count = crop.width * crop.height
                    if pixel_count <= 0:
                        redactions_ok = False
                        continue
                    black = sum(crop.convert("L").histogram()[:13])
                    if black / pixel_count < 0.94:
                        redactions_ok = False
                add("OUTPUT_REOPENABLE", True)
        except (fitz.FileDataError, OSError):
            add("OUTPUT_REOPENABLE", False)
        add("PAGE_COUNT_MATCH", source_pages >= 0 and source_pages == output_pages)
        add("NO_NATIVE_TEXT_IN_SECURE_PDF", not native_text.strip())
        add("NO_ANNOTATIONS", annotations == 0)
        structural: dict[str, bool] = {
            "NO_BLOCKED_METADATA": False,
            "NO_XMP": False,
            "NO_ATTACHMENTS": False,
            "NO_JAVASCRIPT": False,
            "NO_LAUNCH_ACTION": False,
            "NO_FORMS": False,
        }
        try:
            with pikepdf.open(output) as pdf:
                root = pdf.Root
                docinfo_keys = [str(key) for key in pdf.docinfo]
                structural["NO_BLOCKED_METADATA"] = not any(
                    key
                    for key in docinfo_keys
                    if key not in {"/Producer", "/Creator", "/CreationDate", "/ModDate"}
                )
                structural["NO_XMP"] = not _root_has(root, "/Metadata")
                structural["NO_ATTACHMENTS"] = not list(pdf.attachments)
                structural["NO_LAUNCH_ACTION"] = not any(
                    _root_has(root, key) for key in ("/OpenAction", "/AA")
                )
                structural["NO_FORMS"] = not _root_has(root, "/AcroForm")
                try:
                    names = root.get("/Names")
                    structural["NO_JAVASCRIPT"] = names is None or "/JavaScript" not in names
                except (AttributeError, TypeError, ValueError):
                    structural["NO_JAVASCRIPT"] = True
        except (pikepdf.PdfError, OSError):
            pass
        for name, passed in structural.items():
            add(name, passed)
        add("REDACTION_REGIONS_APPLIED", redactions_ok)
        checks.append(verify_redaction_crops_with_ocr(redaction_crops, self.ocr))
        digest = sha256_file(output) if output.exists() and output.stat().st_size else ""
        add("OUTPUT_HASH_CREATED", bool(digest))
        if not self.metadata.available:
            checks.append(
                VerificationCheck(
                    "EXIFTOOL_NO_BLOCKED_METADATA",
                    CheckStatus.WARNING,
                    "ExifTool was unavailable; metadata verification was limited",
                )
            )
        else:
            try:
                metadata = self.metadata.inspect(output)
            except ExternalToolError:
                checks.append(
                    VerificationCheck(
                        "EXIFTOOL_NO_BLOCKED_METADATA",
                        CheckStatus.WARNING,
                        "ExifTool could not complete metadata verification",
                    )
                )
            else:
                blocked = [
                    key
                    for key in metadata
                    if any(
                        marker in key.lower()
                        for marker in ("author", "title", "subject", "keywords", "xmp", "gps")
                    )
                ]
                checks.append(
                    VerificationCheck(
                        "EXIFTOOL_NO_BLOCKED_METADATA",
                        CheckStatus.PASSED if not blocked else CheckStatus.FAILED,
                        ", ".join(blocked),
                    )
                )
        has_failure = any(check.status is CheckStatus.FAILED for check in checks)
        has_warning = any(check.status is CheckStatus.WARNING for check in checks)
        status = (
            VerificationStatus.FAILED
            if has_failure
            else VerificationStatus.PASSED_WITH_WARNINGS
            if has_warning
            else VerificationStatus.PASSED
        )
        return VerificationResult(status, digest, checks)
