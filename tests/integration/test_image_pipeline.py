from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from cleandrop.adapters.image import ImageMediaAdapter
from cleandrop.application.services import PlanningService
from cleandrop.composition import build_inspect_service
from cleandrop.domain.errors import InspectionError, ResourceLimitError
from cleandrop.domain.models import (
    CheckStatus,
    FindingKind,
    NormalizedRect,
    RedactionRegion,
    ResourceLimits,
)


class MissingTool:
    available = False

    def inspect(self, _path: Path) -> dict[str, object]:
        return {}


class MissingOcr:
    available = False


def test_image_inspection_detects_metadata(jpg_with_metadata: Path) -> None:
    adapter = ImageMediaAdapter(ocr=MissingOcr(), metadata=MissingTool())  # type: ignore[arg-type]
    report = adapter.inspect(jpg_with_metadata, ResourceLimits(), run_ocr=False)
    assert report.input_name == "عکس دارای فاصله.jpg"
    assert report.input_sha256
    assert any(item.kind is FindingKind.METADATA for item in report.findings)
    assert not any("Secret Camera Corp" in item.masked_preview for item in report.findings)


def test_image_pixel_rebuild_and_redaction(jpg_with_metadata: Path, tmp_path: Path) -> None:
    adapter = ImageMediaAdapter(ocr=MissingOcr(), metadata=MissingTool())  # type: ignore[arg-type]
    report = adapter.inspect(jpg_with_metadata, ResourceLimits(), run_ocr=False)
    output = tmp_path / "result.jpg"
    redaction = RedactionRegion(0, NormalizedRect(0.1, 0.1, 0.3, 0.3), reason="manual")
    plan = PlanningService().create_plan(
        jpg_with_metadata,
        report,
        output,
        selected_finding_ids=set(),
        manual_redactions=[redaction],
    )
    result = adapter.sanitize(jpg_with_metadata, plan)
    assert result == output
    assert jpg_with_metadata.exists()
    with Image.open(output) as image:
        assert not image.getexif()
        crop = image.convert("RGB").crop(redaction.rect.to_pixels(*image.size))
        assert sum(crop.convert("L").histogram()[:20]) / (crop.width * crop.height) > 0.95
    verification = adapter.verify(jpg_with_metadata, output, [redaction])
    assert verification.passed
    assert all(check.status is not CheckStatus.FAILED for check in verification.checks)


def test_png_text_metadata_removed(png_with_text: Path, tmp_path: Path) -> None:
    adapter = ImageMediaAdapter(ocr=MissingOcr(), metadata=MissingTool())  # type: ignore[arg-type]
    report = build_inspect_service(image=adapter).inspect(png_with_text, run_ocr=False)
    assert any(item.kind is FindingKind.METADATA for item in report.findings)
    plan = PlanningService().create_plan(png_with_text, report, tmp_path / "cleaned.png")
    output = adapter.sanitize(png_with_text, plan)
    with Image.open(output) as cleaned:
        assert "Description" not in cleaned.info


def test_image_inspection_rejects_broken_and_oversized_files(tmp_path: Path) -> None:
    adapter = ImageMediaAdapter(ocr=MissingOcr(), metadata=MissingTool())  # type: ignore[arg-type]
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"\x89PNG\r\n\x1a\nbroken")
    with pytest.raises(InspectionError):
        adapter.inspect(broken, ResourceLimits(), run_ocr=False)

    oversized = tmp_path / "large.png"
    Image.new("RGB", (20, 20), "white").save(oversized)
    with pytest.raises(ResourceLimitError):
        adapter.inspect(
            oversized,
            ResourceLimits(max_image_pixels=100),
            run_ocr=False,
        )


def test_image_verification_fails_for_broken_output(
    jpg_with_metadata: Path,
    tmp_path: Path,
) -> None:
    adapter = ImageMediaAdapter(ocr=MissingOcr(), metadata=MissingTool())  # type: ignore[arg-type]
    broken = tmp_path / "broken.jpg"
    broken.write_bytes(b"not an image")
    verification = adapter.verify(jpg_with_metadata, broken, [])
    assert not verification.passed


def test_exif_orientation_is_applied_before_pixel_rebuild(
    jpg_with_orientation: Path,
    tmp_path: Path,
) -> None:
    adapter = ImageMediaAdapter(ocr=MissingOcr(), metadata=MissingTool())  # type: ignore[arg-type]
    inspection = adapter.inspect(jpg_with_orientation, ResourceLimits(), run_ocr=False)
    assert inspection.dimensions == [(40, 80)]
    plan = PlanningService().create_plan(
        jpg_with_orientation,
        inspection,
        tmp_path / "oriented.cleaned.jpg",
    )
    output = adapter.sanitize(jpg_with_orientation, plan)
    with Image.open(output) as cleaned:
        assert cleaned.size == (40, 80)
        assert not cleaned.getexif()
    assert adapter.verify(jpg_with_orientation, output, []).passed


def test_gps_metadata_is_detected_and_removed(
    jpg_with_gps: Path,
    tmp_path: Path,
) -> None:
    adapter = ImageMediaAdapter(ocr=MissingOcr(), metadata=MissingTool())  # type: ignore[arg-type]
    inspection = adapter.inspect(jpg_with_gps, ResourceLimits(), run_ocr=False)
    assert any(finding.kind is FindingKind.GPS for finding in inspection.findings)
    plan = PlanningService().create_plan(
        jpg_with_gps,
        inspection,
        tmp_path / "location.cleaned.jpg",
    )
    output = adapter.sanitize(jpg_with_gps, plan)
    with Image.open(output) as cleaned:
        assert not cleaned.getexif()
    assert adapter.verify(jpg_with_gps, output, []).passed


def test_magic_bytes_drive_output_format_for_disguised_extension(tmp_path: Path) -> None:
    source = tmp_path / "holiday.upload"
    Image.new("RGB", (80, 50), "white").save(source, format="JPEG")
    adapter = ImageMediaAdapter(ocr=MissingOcr(), metadata=MissingTool())  # type: ignore[arg-type]
    inspection = build_inspect_service(image=adapter).inspect(source, run_ocr=False)

    plan = PlanningService().create_plan(source, inspection)
    output = adapter.sanitize(source, plan)

    assert output.name == "holiday.cleaned.jpg"
    with Image.open(output) as cleaned:
        assert cleaned.format == "JPEG"
    assert adapter.verify(source, output, []).passed
