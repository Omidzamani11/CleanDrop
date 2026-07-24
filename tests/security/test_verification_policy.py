from __future__ import annotations

from pathlib import Path

import fitz
from PIL import Image, PngImagePlugin

from cleandrop.adapters.image import ImageMediaAdapter
from cleandrop.adapters.pdf import PdfMediaAdapter
from cleandrop.domain.errors import ExternalToolError
from cleandrop.domain.models import (
    CheckStatus,
    NormalizedRect,
    RedactionRegion,
    VerificationResult,
)


class MissingOcr:
    available = False


class MetadataResult:
    available = True

    def __init__(self, result: dict[str, object] | None = None, *, fail: bool = False) -> None:
        self.result = result or {}
        self.fail = fail

    def inspect(self, _path: Path) -> dict[str, object]:
        if self.fail:
            raise ExternalToolError("controlled metadata verification failure")
        return self.result


def _check_status(result: VerificationResult, name: str) -> CheckStatus:
    return next(check.status for check in result.checks if check.name == name)


def test_image_verification_rejects_metadata_and_incomplete_redactions(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (100, 100), "white").save(source)
    output = tmp_path / "unsafe.png"
    exif = Image.Exif()
    exif[305] = "private editor"
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("XML:com.adobe.xmp", "private xmp")
    Image.new("RGB", (100, 100), "white").save(output, exif=exif, pnginfo=metadata)

    adapter = ImageMediaAdapter(
        ocr=MissingOcr(),
        metadata=MetadataResult({"EXIF:GPSLatitude": "35.0"}),
    )
    redactions = [
        RedactionRegion(1, NormalizedRect(0.1, 0.1, 0.2, 0.2)),
        RedactionRegion(0, NormalizedRect(0.2, 0.2, 0.2, 0.2)),
        RedactionRegion(0, NormalizedRect(0.0, 0.0, 0.000001, 0.000001)),
    ]
    verification = adapter.verify(source, output, redactions)

    assert not verification.passed
    assert _check_status(verification, "NO_BLOCKED_METADATA") is CheckStatus.FAILED
    assert _check_status(verification, "NO_XMP") is CheckStatus.FAILED
    assert _check_status(verification, "REDACTION_REGIONS_APPLIED") is CheckStatus.FAILED
    assert _check_status(verification, "EXIFTOOL_NO_BLOCKED_METADATA") is CheckStatus.FAILED


def test_image_verification_records_exiftool_runtime_failure(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    output = tmp_path / "output.jpg"
    Image.new("RGB", (40, 40), "white").save(source)
    Image.new("RGB", (40, 40), "white").save(output)
    adapter = ImageMediaAdapter(
        ocr=MissingOcr(),
        metadata=MetadataResult(fail=True),
    )

    verification = adapter.verify(source, output, [])

    assert verification.passed
    assert verification.status.value == "passed_with_warnings"
    assert _check_status(verification, "EXIFTOOL_NO_BLOCKED_METADATA") is CheckStatus.WARNING


def test_pdf_verification_rejects_native_content_and_bad_redactions(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    with fitz.open() as document:
        page = document.new_page(width=200, height=120)
        page.insert_text((20, 40), "owner@example.com")
        page.add_text_annot((20, 70), "private note")
        document.set_metadata({"author": "Private Person"})
        document.save(source)

    adapter = PdfMediaAdapter(
        ocr=MissingOcr(),
        metadata=MetadataResult({"PDF:Author": "Private Person"}),
    )
    redactions = [
        RedactionRegion(3, NormalizedRect(0.1, 0.1, 0.2, 0.2)),
        RedactionRegion(0, NormalizedRect(0.1, 0.1, 0.2, 0.2)),
        RedactionRegion(0, NormalizedRect(0.0, 0.0, 0.000001, 0.000001)),
    ]

    verification = adapter.verify(source, source, redactions)

    assert not verification.passed
    assert _check_status(verification, "NO_NATIVE_TEXT_IN_SECURE_PDF") is CheckStatus.FAILED
    assert _check_status(verification, "NO_ANNOTATIONS") is CheckStatus.FAILED
    assert _check_status(verification, "REDACTION_REGIONS_APPLIED") is CheckStatus.FAILED
    assert _check_status(verification, "EXIFTOOL_NO_BLOCKED_METADATA") is CheckStatus.FAILED


def test_pdf_verification_records_exiftool_runtime_failure(
    scanned_pdf: Path,
) -> None:
    adapter = PdfMediaAdapter(
        ocr=MissingOcr(),
        metadata=MetadataResult(fail=True),
    )

    verification = adapter.verify(scanned_pdf, scanned_pdf, [])

    assert verification.passed
    assert verification.status.value == "passed_with_warnings"
    assert _check_status(verification, "EXIFTOOL_NO_BLOCKED_METADATA") is CheckStatus.WARNING
