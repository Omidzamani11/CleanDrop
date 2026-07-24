from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QApplication

from cleandrop.adapters.image import ImageMediaAdapter
from cleandrop.adapters.ocr import TesseractOcrEngine
from cleandrop.domain.models import FindingKind, ResourceLimits


def _application() -> QApplication:
    instance = QApplication.instance()
    if isinstance(instance, QApplication):
        return instance
    return QApplication([])


def _render_text(path: Path, text: str, *, rtl: bool = False) -> Path:
    _application()
    image = QImage(1800, 500, QImage.Format.Format_RGB32)
    image.fill(QColor("white"))
    painter = QPainter(image)
    painter.setPen(QColor("black"))
    painter.setFont(QFont("Tahoma", 72))
    painter.setLayoutDirection(
        Qt.LayoutDirection.RightToLeft if rtl else Qt.LayoutDirection.LeftToRight
    )
    painter.drawText(
        QRect(50, 50, 1700, 350),
        Qt.AlignmentFlag.AlignCenter,
        text,
    )
    painter.end()
    assert image.save(str(path))
    return path


@pytest.mark.integration
def test_bundled_ocr_reads_persian_and_english(tmp_path: Path) -> None:
    engine = TesseractOcrEngine()
    if not engine.available:
        pytest.skip("Bundled OCR runtime is unavailable")
    persian = (
        "\u0627\u0637\u0644\u0627\u0639\u0627\u062a "
        "\u062a\u0645\u0627\u0633 "
        "\u0645\u062d\u0631\u0645\u0627\u0646\u0647"
    )
    persian_path = _render_text(tmp_path / "persian.png", persian, rtl=True)
    persian_text = " ".join(token.text for token in engine.extract(persian_path))
    assert "\u0627\u0637\u0644\u0627\u0639\u0627\u062a" in persian_text
    assert "\u062a\u0645\u0627\u0633" in persian_text

    english_path = _render_text(
        tmp_path / "نمونه محرمانه.png",
        "owner@example.com 09123456789",
    )
    report = ImageMediaAdapter(ocr=engine).inspect(
        english_path,
        ResourceLimits(),
        run_ocr=True,
    )
    kinds = {finding.kind for finding in report.findings}
    assert FindingKind.EMAIL in kinds
    assert FindingKind.PHONE in kinds
    assert all(
        finding.rect is not None
        for finding in report.findings
        if finding.kind in {FindingKind.EMAIL, FindingKind.PHONE}
    )
