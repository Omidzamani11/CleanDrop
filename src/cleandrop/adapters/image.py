from __future__ import annotations

import hashlib
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

from PIL import ExifTags, Image, ImageDraw, ImageOps, UnidentifiedImageError

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
    RedactionRegion,
    ResourceLimits,
    SanitizationPlan,
    Severity,
    VerificationCheck,
    VerificationResult,
    VerificationStatus,
)
from cleandrop.security.paths import hash_path, sha256_file

_GPS_EXIF_TAG = 34853
_BLOCKED_METADATA_MARKERS = (
    "gps",
    "location",
    "latitude",
    "longitude",
    "author",
    "artist",
    "owner",
    "comment",
    "description",
    "serial",
    "camera",
    "make",
    "model",
    "software",
    "xmp",
    "iptc",
)


def _blocked_external_metadata_key(key: str) -> bool:
    lowered = key.lower()
    group, _, tag = lowered.partition(":")
    if group == "exiftool":
        return False
    if group in {"exif", "xmp", "iptc", "gps"}:
        return True
    return any(marker in tag for marker in _BLOCKED_METADATA_MARKERS)


def _metadata_finding(kind: FindingKind, key: str, value: Any) -> Finding:
    evidence = f"{key}:{value!s}"
    return Finding(
        id=str(uuid.uuid4()),
        kind=kind,
        source=FindingSource.METADATA,
        severity=Severity.HIGH if kind is FindingKind.GPS else Severity.MEDIUM,
        confidence=1.0,
        masked_preview=f"{key}: [hidden]",
        evidence_hash=hashlib.sha256(evidence.encode("utf-8", errors="replace")).hexdigest(),
        metadata_key=key,
    )


def _line_groups(tokens: list[OcrToken]) -> list[tuple[str, int, Any]]:
    grouped: dict[tuple[int, int, int, int], list[OcrToken]] = {}
    for token in tokens:
        key = (token.page_index, token.block, token.paragraph, token.line)
        grouped.setdefault(key, []).append(token)
    lines: list[tuple[str, int, Any]] = []
    for line_tokens in grouped.values():
        text = " ".join(token.text for token in line_tokens)
        left = min(token.rect.x for token in line_tokens)
        top = min(token.rect.y for token in line_tokens)
        right = max(token.rect.x + token.rect.width for token in line_tokens)
        bottom = max(token.rect.y + token.rect.height for token in line_tokens)
        from cleandrop.domain.models import NormalizedRect

        rect = NormalizedRect(left, top, min(1 - left, right - left), min(1 - top, bottom - top))
        lines.append((text, line_tokens[0].page_index, rect))
    return lines


class ImageMediaAdapter:
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
        try:
            with Image.open(path) as opened:
                opened.verify()
            with Image.open(path) as opened:
                opened.load()
                width, height = ImageOps.exif_transpose(opened).size
                if width * height > limits.max_image_pixels:
                    raise ResourceLimitError("Image exceeds the configured pixel limit")
                media_type = MediaType.JPEG if opened.format == "JPEG" else MediaType.PNG
                exif = opened.getexif()
                info_keys = list(opened.info)
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise InspectionError("The image is damaged or unsupported") from exc

        findings: list[Finding] = []
        for tag_id, value in exif.items():
            key = ExifTags.TAGS.get(tag_id, str(tag_id))
            key_text = str(key)
            kind = (
                FindingKind.GPS
                if tag_id == _GPS_EXIF_TAG or "gps" in key_text.lower()
                else FindingKind.METADATA
            )
            findings.append(_metadata_finding(kind, key_text, value))
        for key in info_keys:
            if any(marker in key.lower() for marker in _BLOCKED_METADATA_MARKERS):
                findings.append(_metadata_finding(FindingKind.METADATA, key, "[present]"))

        warnings: list[str] = []
        try:
            exiftool_data = self.metadata.inspect(path)
        except ExternalToolError as exc:
            exiftool_data = {}
            warnings.append(f"Extended metadata inspection was limited: {type(exc).__name__}")
        existing_keys = {finding.metadata_key for finding in findings}
        for key, value in exiftool_data.items():
            lowered = key.lower()
            if key in existing_keys:
                continue
            if _blocked_external_metadata_key(key):
                kind = (
                    FindingKind.GPS
                    if any(
                        marker in lowered for marker in ("gps", "latitude", "longitude", "location")
                    )
                    else FindingKind.METADATA
                )
                findings.append(_metadata_finding(kind, key, value))

        if run_ocr and self.ocr.available:
            try:
                tokens = self.ocr.extract(
                    path,
                    timeout_seconds=limits.max_ocr_seconds_per_page,
                )
                for text, page_index, rect in _line_groups(tokens):
                    findings.extend(
                        self.detectors.detect(text, FindingSource.OCR, page_index, rect)
                    )
            except (ExternalToolError, OSError, ValueError) as exc:
                warnings.append(f"OCR unavailable for this image: {type(exc).__name__}")
        elif run_ocr:
            warnings.append("OCR capability is unavailable")

        return InspectionReport(
            input_path_hash=hash_path(path),
            input_name=path.name,
            input_sha256=sha256_file(path),
            media_type=media_type,
            size_bytes=path.stat().st_size,
            page_count=1,
            dimensions=[(width, height)],
            findings=findings,
            capabilities={"ocr": self.ocr.available, "exiftool": self.metadata.available},
            warnings=warnings,
        )

    def sanitize(self, source: Path, plan: SanitizationPlan) -> Path:
        output = Path(plan.output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            with Image.open(source) as opened:
                opened.load()
                oriented = ImageOps.exif_transpose(opened)
                target_mode = (
                    "RGBA"
                    if oriented.mode in {"RGBA", "LA"} and output.suffix.lower() == ".png"
                    else "RGB"
                )
                pixels = oriented.convert(target_mode)
                rebuilt = Image.new(target_mode, pixels.size)
                rebuilt.paste(pixels)
                draw = ImageDraw.Draw(rebuilt)
                for region in plan.redactions:
                    if region.page_index != 0:
                        continue
                    draw.rectangle(
                        region.rect.to_pixels(*rebuilt.size),
                        fill=(0, 0, 0, 255) if target_mode == "RGBA" else (0, 0, 0),
                    )
                with tempfile.TemporaryDirectory(
                    prefix=f".cleandrop-{os.getpid()}-",
                    dir=output.parent,
                ) as temp_dir:
                    temp = Path(temp_dir) / output.name
                    if output.suffix.lower() in {".jpg", ".jpeg"}:
                        rebuilt.convert("RGB").save(temp, format="JPEG", quality=95, optimize=True)
                    else:
                        rebuilt.save(temp, format="PNG", optimize=True)
                    verification = self.verify(source, temp, plan.redactions)
                    if not verification.passed:
                        raise VerificationError("The rebuilt image did not pass verification")
                    os.replace(temp, output)
        except (OSError, ValueError) as exc:
            raise SanitizationError("Image sanitization failed") from exc
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
        output_size = (0, 0)
        output_format = ""
        blocked: list[str] = []
        redactions_ok = True
        redaction_crops: list[Image.Image] = []
        try:
            with Image.open(source) as original, Image.open(output) as cleaned:
                cleaned.load()
                output_size = cleaned.size
                output_format = cleaned.format or ""
                for key in cleaned.info:
                    if any(marker in key.lower() for marker in _BLOCKED_METADATA_MARKERS):
                        blocked.append(key)
                if cleaned.getexif():
                    blocked.append("EXIF")
                rgb = cleaned.convert("RGB")
                for region in redactions:
                    if region.page_index != 0:
                        continue
                    crop = rgb.crop(region.rect.to_pixels(*rgb.size))
                    redaction_crops.append(crop.copy())
                    pixel_count = crop.width * crop.height
                    if pixel_count <= 0:
                        redactions_ok = False
                        continue
                    histogram = crop.convert("L").histogram()
                    black = sum(histogram[:13])
                    if black / pixel_count < 0.94:
                        redactions_ok = False
                add("OUTPUT_REOPENABLE", True)
                add("DIMENSIONS_VALID", ImageOps.exif_transpose(original).size == output_size)
        except (OSError, UnidentifiedImageError):
            add("OUTPUT_REOPENABLE", False)
            add("DIMENSIONS_VALID", False)
        expected = "JPEG" if output.suffix.lower() in {".jpg", ".jpeg"} else "PNG"
        add("MEDIA_TYPE_MATCH", output_format == expected)
        add("NO_BLOCKED_METADATA", not blocked, ", ".join(blocked))
        add("NO_XMP", not any("xmp" in item.lower() for item in blocked))
        add("REDACTION_REGIONS_APPLIED", redactions_ok)
        checks.append(verify_redaction_crops_with_ocr(redaction_crops, self.ocr))
        digest = sha256_file(output) if output.exists() and output.stat().st_size else ""
        add("OUTPUT_HASH_CREATED", bool(digest))
        if self.metadata.available:
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
                external_blocked = [key for key in metadata if _blocked_external_metadata_key(key)]
                if external_blocked:
                    checks.append(
                        VerificationCheck(
                            "EXIFTOOL_NO_BLOCKED_METADATA",
                            CheckStatus.FAILED,
                            ", ".join(external_blocked),
                        )
                    )
                else:
                    checks.append(
                        VerificationCheck(
                            "EXIFTOOL_NO_BLOCKED_METADATA",
                            CheckStatus.PASSED,
                        )
                    )
        else:
            checks.append(
                VerificationCheck(
                    "EXIFTOOL_NO_BLOCKED_METADATA",
                    CheckStatus.WARNING,
                    "ExifTool was unavailable; metadata verification was limited",
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
