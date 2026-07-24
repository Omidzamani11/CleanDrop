from __future__ import annotations

import hashlib
import re
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from cleandrop.domain.models import (
    Finding,
    FindingKind,
    FindingSource,
    NormalizedRect,
    Severity,
)

_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]{1,64}@(?:[\w-]{1,63}\.)+[A-Za-z]{2,63}(?![\w.-])")
_URL = re.compile(r"\b(?:https?://|www\.)[^\s<>{}\[\]]{4,}", re.IGNORECASE)
_PHONE = re.compile(
    r"(?<!\d)(?:\+98|0098|0)?[\s().-]*(?:9\d{2}|[1-8]\d{1,3})"
    r"(?:[\s().-]*\d){6,8}(?!\d)"
)
_CARD = re.compile(r"(?<!\d)(?:\d[\s-]?){13,19}(?!\d)")
_NATIONAL_ID = re.compile(r"(?<!\d)\d{10}(?!\d)")


def _mask(value: str) -> str:
    clean = value.strip()
    if "@" in clean:
        local, domain = clean.split("@", 1)
        return f"{local[:1]}***@{domain[:1]}***"
    digits = "".join(char for char in clean if char.isdigit())
    if digits:
        return f"***{digits[-4:]}" if len(digits) > 4 else "****"
    return f"{clean[:2]}***" if clean else "***"


def _evidence_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def _luhn(value: str) -> bool:
    digits = [int(char) for char in value if char.isdigit()]
    if not 13 <= len(digits) <= 19 or len(set(digits)) == 1:
        return False
    total = 0
    parity = len(digits) % 2
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def _valid_iran_national_id(value: str) -> bool:
    digits = value.translate(_PERSIAN_DIGITS)
    if len(digits) != 10 or not digits.isdigit() or len(set(digits)) == 1:
        return False
    check = int(digits[-1])
    remainder = sum(int(digits[index]) * (10 - index) for index in range(9)) % 11
    expected = remainder if remainder < 2 else 11 - remainder
    return check == expected


@dataclass(frozen=True, slots=True)
class Detector:
    kind: FindingKind
    pattern: re.Pattern[str]
    severity: Severity
    confidence: float
    validator: Callable[[str], bool] | None = None

    def detect(
        self,
        text: str,
        source: FindingSource,
        page_index: int | None = None,
        rect: NormalizedRect | None = None,
    ) -> Iterable[Finding]:
        normalized = text.translate(_PERSIAN_DIGITS)
        for match in self.pattern.finditer(normalized):
            raw_value = match.group(0).strip(".,;:!?)]}")
            if self.validator is not None and not self.validator(raw_value):
                continue
            confidence = self.confidence
            if self.kind is FindingKind.PHONE and raw_value.startswith("0") is False:
                confidence = min(confidence, 0.75)
            yield Finding(
                id=str(uuid.uuid4()),
                kind=self.kind,
                source=source,
                severity=self.severity,
                confidence=confidence,
                masked_preview=_mask(raw_value),
                evidence_hash=_evidence_hash(raw_value),
                page_index=page_index,
                rect=rect,
            )


class DetectorSuite:
    def __init__(self) -> None:
        self.detectors = (
            Detector(FindingKind.EMAIL, _EMAIL, Severity.HIGH, 0.98),
            Detector(FindingKind.PHONE, _PHONE, Severity.HIGH, 0.88),
            Detector(FindingKind.URL, _URL, Severity.MEDIUM, 0.88),
            Detector(FindingKind.CREDIT_CARD, _CARD, Severity.CRITICAL, 0.99, _luhn),
            Detector(
                FindingKind.IRAN_NATIONAL_ID,
                _NATIONAL_ID,
                Severity.CRITICAL,
                0.99,
                _valid_iran_national_id,
            ),
        )

    def detect(
        self,
        text: str,
        source: FindingSource,
        page_index: int | None = None,
        rect: NormalizedRect | None = None,
    ) -> list[Finding]:
        findings: list[Finding] = []
        seen: set[tuple[FindingKind, str]] = set()
        for detector in self.detectors:
            for finding in detector.detect(text, source, page_index, rect):
                key = (finding.kind, finding.evidence_hash)
                if key not in seen:
                    findings.append(finding)
                    seen.add(key)
        return findings


__all__ = ["DetectorSuite", "_luhn", "_valid_iran_national_id"]
