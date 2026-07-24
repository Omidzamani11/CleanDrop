from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from cleandrop.adapters.redaction_verification import verify_redaction_crops_with_ocr
from cleandrop.domain.errors import ExternalToolError
from cleandrop.domain.models import CheckStatus


@dataclass
class Token:
    text: str
    confidence: float


class FakeOcr:
    def __init__(self, *, available: bool, tokens: list[Token] | None = None) -> None:
        self._available = available
        self.tokens = tokens or []

    @property
    def available(self) -> bool:
        return self._available

    def extract(
        self,
        _image_path: Path,
        page_index: int = 0,
        *,
        timeout_seconds: int | None = None,
    ) -> list[Token]:
        del page_index, timeout_seconds
        return self.tokens


def test_redaction_ocr_check_handles_empty_unavailable_clean_and_residual() -> None:
    crop = Image.new("RGB", (30, 20), "black")
    assert (
        verify_redaction_crops_with_ocr([], FakeOcr(available=False)).status is CheckStatus.PASSED
    )
    assert (
        verify_redaction_crops_with_ocr([crop], FakeOcr(available=False)).status
        is CheckStatus.WARNING
    )
    assert (
        verify_redaction_crops_with_ocr([crop], FakeOcr(available=True)).status
        is CheckStatus.PASSED
    )
    residual = FakeOcr(available=True, tokens=[Token("private", 0.9)])
    assert verify_redaction_crops_with_ocr([crop], residual).status is CheckStatus.FAILED


def test_redaction_ocr_failure_is_a_warning() -> None:
    class BrokenOcr(FakeOcr):
        def extract(
            self,
            _image_path: Path,
            page_index: int = 0,
            *,
            timeout_seconds: int | None = None,
        ) -> list[Token]:
            del page_index, timeout_seconds
            raise ExternalToolError("external tool failed")

    check = verify_redaction_crops_with_ocr(
        [Image.new("RGB", (10, 10), "black")],
        BrokenOcr(available=True),
    )
    assert check.status is CheckStatus.WARNING
