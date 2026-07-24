from __future__ import annotations

import pytest

from cleandrop.detectors.pii import DetectorSuite, _luhn, _valid_iran_national_id
from cleandrop.domain.models import FindingKind, FindingSource, NormalizedRect


@pytest.mark.parametrize(
    ("number", "valid"),
    [
        ("4111 1111 1111 1111", True),
        ("4111-1111-1111-1112", False),
        ("1111111111111111", False),
        ("123", False),
    ],
)
def test_luhn(number: str, valid: bool) -> None:
    assert _luhn(number) is valid


def test_iran_national_id_checksum() -> None:
    assert _valid_iran_national_id("0013548999")
    assert _valid_iran_national_id("۰۰۱۳۵۴۸۹۹۹")
    assert not _valid_iran_national_id("1111111111")
    assert not _valid_iran_national_id("0013548998")


def test_suite_detects_and_masks_supported_pii() -> None:
    text = (
        "Email owner@example.com phone 09123456789 url https://example.com "
        "card 4111 1111 1111 1111 national 0013548999"
    )
    rect = NormalizedRect(0.1, 0.1, 0.8, 0.2)
    findings = DetectorSuite().detect(text, FindingSource.OCR, 0, rect)
    kinds = {finding.kind for finding in findings}
    assert {
        FindingKind.EMAIL,
        FindingKind.PHONE,
        FindingKind.URL,
        FindingKind.CREDIT_CARD,
        FindingKind.IRAN_NATIONAL_ID,
    } <= kinds
    assert all("owner@example.com" not in finding.masked_preview for finding in findings)
    assert all(len(finding.evidence_hash) == 64 for finding in findings)
    assert all(finding.rect == rect for finding in findings)


def test_phone_without_prefix_has_lower_confidence() -> None:
    findings = DetectorSuite().detect("9123456789", FindingSource.TEXT_LAYER)
    phone = next(item for item in findings if item.kind is FindingKind.PHONE)
    assert phone.confidence <= 0.75
