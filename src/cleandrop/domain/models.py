from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class MediaType(StrEnum):
    JPEG = "image/jpeg"
    PNG = "image/png"
    PDF = "application/pdf"


class FindingKind(StrEnum):
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    CREDIT_CARD = "credit_card"
    IRAN_NATIONAL_ID = "iran_national_id"
    GPS = "gps"
    METADATA = "metadata"
    PDF_JAVASCRIPT = "pdf_javascript"
    PDF_ATTACHMENT = "pdf_attachment"
    PDF_ANNOTATION = "pdf_annotation"
    PDF_FORM = "pdf_form"
    PDF_ACTION = "pdf_action"


class FindingSource(StrEnum):
    OCR = "ocr"
    TEXT_LAYER = "text_layer"
    METADATA = "metadata"
    STRUCTURE = "structure"
    MANUAL = "manual"


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SanitizationProfile(StrEnum):
    PIXEL_REBUILD = "pixel-rebuild"
    SECURE_FLATTEN = "secure-flatten"


class JobState(StrEnum):
    CREATED = "created"
    VALIDATING = "validating"
    INSPECTING = "inspecting"
    REVIEW_REQUIRED = "review_required"
    PLAN_READY = "plan_ready"
    SANITIZING = "sanitizing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    REJECTED = "rejected"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CheckStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    NOT_RUN = "not_run"


class VerificationStatus(StrEnum):
    PASSED = "passed"
    PASSED_WITH_WARNINGS = "passed_with_warnings"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class NormalizedRect:
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        values = (self.x, self.y, self.width, self.height)
        if any(value < 0 or value > 1 for value in values):
            raise ValueError("NormalizedRect values must be between 0 and 1")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("NormalizedRect dimensions must be positive")
        if self.x + self.width > 1.000001 or self.y + self.height > 1.000001:
            raise ValueError("NormalizedRect must stay inside the page")

    def to_pixels(self, width: int, height: int) -> tuple[int, int, int, int]:
        left = max(0, round(self.x * width))
        top = max(0, round(self.y * height))
        right = min(width, round((self.x + self.width) * width))
        bottom = min(height, round((self.y + self.height) * height))
        return left, top, right, bottom


@dataclass(frozen=True, slots=True)
class Finding:
    id: str
    kind: FindingKind
    source: FindingSource
    severity: Severity
    confidence: float
    masked_preview: str
    evidence_hash: str
    page_index: int | None = None
    rect: NormalizedRect | None = None
    metadata_key: str | None = None
    selected: bool = True

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("Finding confidence must be between 0 and 1")
        if not self.evidence_hash or len(self.evidence_hash) < 16:
            raise ValueError("Finding evidence_hash is required")


@dataclass(frozen=True, slots=True)
class InspectionReport:
    input_path_hash: str
    input_name: str
    input_sha256: str
    media_type: MediaType
    size_bytes: int
    page_count: int
    dimensions: list[tuple[int, int]]
    findings: list[Finding] = field(default_factory=list)
    capabilities: dict[str, bool] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class RedactionRegion:
    page_index: int
    rect: NormalizedRect
    source_finding_id: str | None = None
    fill_mode: str = "black"
    reason: str = "sensitive-data"


@dataclass(frozen=True, slots=True)
class SanitizationPlan:
    profile: SanitizationProfile
    output_path: str
    redactions: list[RedactionRegion]
    dpi: int = 200

    def __post_init__(self) -> None:
        if self.dpi not in {150, 200, 300}:
            raise ValueError("DPI must be 150, 200, or 300")


@dataclass(frozen=True, slots=True)
class VerificationCheck:
    name: str
    status: CheckStatus
    message: str = ""


@dataclass(frozen=True, slots=True)
class VerificationResult:
    status: VerificationStatus
    output_sha256: str
    checks: list[VerificationCheck]

    @property
    def passed(self) -> bool:
        return self.status in {
            VerificationStatus.PASSED,
            VerificationStatus.PASSED_WITH_WARNINGS,
        }


@dataclass(frozen=True, slots=True)
class JobReport:
    schema_version: str
    application_version: str
    job_id: str
    state: JobState
    inspection: InspectionReport
    sanitization_plan: SanitizationPlan
    verification: VerificationResult
    output_path: str
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        inspection = asdict(self.inspection)
        input_name = str(inspection.pop("input_name"))
        input_details = {
            "path_hash": inspection.pop("input_path_hash"),
            "name_hash": hashlib.sha256(input_name.encode("utf-8", errors="replace")).hexdigest(),
            "extension": Path(input_name).suffix.lower(),
            "sha256": inspection.pop("input_sha256"),
            "media_type": inspection.pop("media_type"),
            "size_bytes": inspection.pop("size_bytes"),
        }
        plan = asdict(self.sanitization_plan)
        planned_output_name = Path(str(plan.pop("output_path"))).name
        plan["output_name_hash"] = hashlib.sha256(
            planned_output_name.encode("utf-8", errors="replace")
        ).hexdigest()
        plan["output_extension"] = Path(planned_output_name).suffix.lower()
        verification = asdict(self.verification)
        output_name = Path(self.output_path).name
        return {
            "schema_version": self.schema_version,
            "application_version": self.application_version,
            "job_id": self.job_id,
            "state": self.state,
            "input": input_details,
            "inspection": inspection,
            "sanitization_plan": plan,
            "verification": verification,
            "warnings": list(self.warnings),
            "output": {
                "name_hash": hashlib.sha256(
                    output_name.encode("utf-8", errors="replace")
                ).hexdigest(),
                "extension": Path(output_name).suffix.lower(),
                "sha256": self.verification.output_sha256,
            },
        }


@dataclass(frozen=True, slots=True)
class ResourceLimits:
    max_file_size: int = 500 * 1024 * 1024
    max_pdf_pages: int = 500
    max_image_pixels: int = 150_000_000
    max_ocr_seconds_per_page: int = 60
    max_job_seconds: int = 30 * 60
    max_batch_files: int = 100

    def __post_init__(self) -> None:
        if (
            min(
                self.max_file_size,
                self.max_pdf_pages,
                self.max_image_pixels,
                self.max_ocr_seconds_per_page,
                self.max_job_seconds,
                self.max_batch_files,
            )
            <= 0
        ):
            raise ValueError("All resource limits must be positive")
