from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image

from cleandrop.application.ports import OcrEngine
from cleandrop.domain.errors import ExternalToolError
from cleandrop.domain.models import CheckStatus, VerificationCheck


def verify_redaction_crops_with_ocr(
    crops: list[Image.Image],
    ocr: OcrEngine,
) -> VerificationCheck:
    """Check redacted pixels with OCR without retaining or reporting recognized text."""
    if not crops:
        return VerificationCheck("REDACTION_OCR_CLEAN", CheckStatus.PASSED)
    if not ocr.available:
        return VerificationCheck(
            "REDACTION_OCR_CLEAN",
            CheckStatus.WARNING,
            "OCR was unavailable; redaction verification used pixel coverage only",
        )
    try:
        with tempfile.TemporaryDirectory(prefix="cleandrop-verify-ocr-") as temp_dir:
            directory = Path(temp_dir)
            for index, crop in enumerate(crops):
                path = directory / f"region-{index}.png"
                crop.convert("RGB").save(path, format="PNG")
                tokens = ocr.extract(path)
                if any(
                    bool(getattr(token, "text", "").strip())
                    and float(getattr(token, "confidence", 0.0)) >= 0.25
                    for token in tokens
                ):
                    return VerificationCheck(
                        "REDACTION_OCR_CLEAN",
                        CheckStatus.FAILED,
                        "OCR detected residual text in a selected redaction region",
                    )
    except (ExternalToolError, OSError, ValueError):
        return VerificationCheck(
            "REDACTION_OCR_CLEAN",
            CheckStatus.WARNING,
            "OCR could not complete the redaction-region verification",
        )
    return VerificationCheck("REDACTION_OCR_CLEAN", CheckStatus.PASSED)
