from __future__ import annotations

from pathlib import Path

import fitz
import pikepdf
import pytest
from PIL import Image

from cleandrop.adapters.ocr import OcrToken
from cleandrop.adapters.pdf import PdfMediaAdapter
from cleandrop.application.services import PlanningService
from cleandrop.domain.errors import InspectionError, ResourceLimitError
from cleandrop.domain.models import FindingKind, NormalizedRect, RedactionRegion, ResourceLimits


class MissingTool:
    available = False

    def inspect(self, _path: Path) -> dict[str, object]:
        return {}


class MissingOcr:
    available = False


class FixedOcr:
    available = True

    def extract(
        self,
        _path: Path,
        page_index: int = 0,
        *,
        timeout_seconds: int | float | None = None,
    ) -> list[OcrToken]:
        del timeout_seconds
        return [
            OcrToken(
                text="owner@example.com",
                confidence=0.98,
                rect=NormalizedRect(0.1, 0.1, 0.4, 0.1),
                page_index=page_index,
                block=1,
                paragraph=1,
                line=1,
            )
        ]


def test_pdf_inspection_finds_structure_and_pii(text_pdf: Path) -> None:
    adapter = PdfMediaAdapter(ocr=MissingOcr(), metadata=MissingTool())  # type: ignore[arg-type]
    report = adapter.inspect(text_pdf, ResourceLimits(), run_ocr=False)
    kinds = {finding.kind for finding in report.findings}
    assert FindingKind.METADATA in kinds
    assert FindingKind.PDF_ANNOTATION in kinds
    assert FindingKind.EMAIL in kinds
    assert FindingKind.PHONE in kinds


def test_pdf_secure_flatten_removes_active_content(text_pdf: Path, tmp_path: Path) -> None:
    adapter = PdfMediaAdapter(ocr=MissingOcr(), metadata=MissingTool())  # type: ignore[arg-type]
    inspection = adapter.inspect(text_pdf, ResourceLimits(), run_ocr=False)
    output = tmp_path / "flattened.pdf"
    manual = RedactionRegion(0, NormalizedRect(0.05, 0.15, 0.8, 0.2), reason="manual")
    plan = PlanningService().create_plan(
        text_pdf,
        inspection,
        output,
        selected_finding_ids=set(),
        manual_redactions=[manual],
        dpi=150,
    )
    adapter.sanitize(text_pdf, plan)
    verification = adapter.verify(text_pdf, output, [manual])
    assert verification.passed
    with fitz.open(output) as cleaned:
        assert cleaned.page_count == 1
        assert not cleaned[0].get_text().strip()
        assert list(cleaned[0].annots() or []) == []
    with pikepdf.open(output) as structural:
        assert not list(structural.attachments)
        assert "/Metadata" not in structural.Root
    with fitz.open(output) as cleaned:
        pixmap = cleaned[0].get_pixmap(dpi=150, alpha=False)
        image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        crop = image.crop(manual.rect.to_pixels(*image.size))
        assert sum(crop.convert("L").histogram()[:20]) / (crop.width * crop.height) > 0.94


def test_pdf_page_limit(text_pdf: Path) -> None:
    adapter = PdfMediaAdapter(ocr=MissingOcr(), metadata=MissingTool())  # type: ignore[arg-type]

    with fitz.open() as document:
        document.new_page()
        document.new_page()
        oversized = text_pdf.with_name("two-pages.pdf")
        document.save(oversized)

    with pytest.raises(ResourceLimitError):
        adapter.inspect(oversized, ResourceLimits(max_pdf_pages=1), run_ocr=False)


def test_pdf_inspection_rejects_encrypted_and_broken_files(
    text_pdf: Path,
    tmp_path: Path,
) -> None:
    adapter = PdfMediaAdapter(ocr=MissingOcr(), metadata=MissingTool())  # type: ignore[arg-type]
    encrypted = tmp_path / "encrypted.pdf"
    with pikepdf.open(text_pdf) as document:
        document.save(
            encrypted,
            encryption=pikepdf.Encryption(owner="owner-secret", user="user-secret"),
        )
    with pytest.raises(InspectionError):
        adapter.inspect(encrypted, ResourceLimits(), run_ocr=False)

    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"%PDF-1.7\nnot a real document")
    with pytest.raises(InspectionError):
        adapter.inspect(broken, ResourceLimits(), run_ocr=False)


def test_pdf_inspection_finds_embedded_and_active_content(
    text_pdf: Path,
    tmp_path: Path,
) -> None:
    secret = tmp_path / "secret.txt"
    secret.write_text("private attachment", encoding="utf-8")
    active = tmp_path / "active.pdf"
    with pikepdf.open(text_pdf) as document:
        document.attachments["secret.txt"] = pikepdf.AttachedFileSpec.from_filepath(
            document,
            secret,
        )
        javascript = pikepdf.Dictionary(
            S=pikepdf.Name("/JavaScript"),
            JS=pikepdf.String("app.alert('private')"),
        )
        document.Root.OpenAction = javascript
        document.Root.AA = pikepdf.Dictionary(O=javascript)
        document.Root.AcroForm = pikepdf.Dictionary(Fields=pikepdf.Array())
        xmp = document.make_stream(b"<x:xmpmeta xmlns:x='adobe:ns:meta/'/>")
        xmp.Type = pikepdf.Name("/Metadata")
        xmp.Subtype = pikepdf.Name("/XML")
        document.Root.Metadata = xmp
        names = document.Root.get("/Names", pikepdf.Dictionary())
        names.JavaScript = pikepdf.Dictionary(
            Names=pikepdf.Array([pikepdf.String("private"), javascript])
        )
        document.Root.Names = names
        document.save(active)

    adapter = PdfMediaAdapter(ocr=MissingOcr(), metadata=MissingTool())  # type: ignore[arg-type]
    report = adapter.inspect(active, ResourceLimits(), run_ocr=False)
    kinds = {finding.kind for finding in report.findings}
    assert {
        FindingKind.PDF_ATTACHMENT,
        FindingKind.PDF_JAVASCRIPT,
        FindingKind.PDF_ACTION,
        FindingKind.PDF_FORM,
    } <= kinds
    assert any(finding.metadata_key == "XMP" for finding in report.findings)


def test_pdf_render_page_bounds_and_failed_verification(
    text_pdf: Path,
    tmp_path: Path,
) -> None:
    adapter = PdfMediaAdapter(ocr=MissingOcr(), metadata=MissingTool())  # type: ignore[arg-type]
    preview = adapter.render_page(text_pdf, 0, 120, tmp_path / "preview.png")
    assert preview.exists()
    with pytest.raises(IndexError):
        adapter.render_page(text_pdf, 1, 120, tmp_path / "bad.png")

    broken = tmp_path / "broken-output.pdf"
    broken.write_bytes(b"%PDF-broken")
    verification = adapter.verify(text_pdf, broken, [])
    assert not verification.passed


def test_scanned_pdf_uses_ocr_coordinates(scanned_pdf: Path) -> None:
    adapter = PdfMediaAdapter(ocr=FixedOcr(), metadata=MissingTool())  # type: ignore[arg-type]
    report = adapter.inspect(scanned_pdf, ResourceLimits(), run_ocr=True)
    email = next(finding for finding in report.findings if finding.kind is FindingKind.EMAIL)
    assert email.source.value == "ocr"
    assert email.page_index == 0
    assert email.rect is not None


def test_secure_flatten_removes_text_hidden_under_visual_rectangle(
    tmp_path: Path,
) -> None:
    source = tmp_path / "visually-covered.pdf"
    with fitz.open() as document:
        page = document.new_page(width=400, height=250)
        page.insert_text((60, 100), "owner@example.com")
        page.draw_rect(
            fitz.Rect(50, 75, 260, 115),
            color=(0, 0, 0),
            fill=(0, 0, 0),
            overlay=True,
        )
        document.save(source)

    adapter = PdfMediaAdapter(ocr=MissingOcr(), metadata=MissingTool())  # type: ignore[arg-type]
    inspection = adapter.inspect(source, ResourceLimits(), run_ocr=False)
    assert any(finding.kind is FindingKind.EMAIL for finding in inspection.findings)
    output = tmp_path / "visually-covered.cleaned.pdf"
    plan = PlanningService().create_plan(source, inspection, output)
    adapter.sanitize(source, plan)
    with fitz.open(output) as cleaned:
        assert not cleaned[0].get_text().strip()
    assert adapter.verify(source, output, plan.redactions).passed
