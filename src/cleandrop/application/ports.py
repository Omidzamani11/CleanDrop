from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any, Protocol

from cleandrop.domain.models import (
    Finding,
    FindingSource,
    InspectionReport,
    MediaType,
    NormalizedRect,
    RedactionRegion,
    ResourceLimits,
    SanitizationPlan,
    VerificationResult,
)


class ImageInspector(Protocol):
    def inspect(self, path: Path, limits: ResourceLimits, run_ocr: bool) -> InspectionReport: ...


class ImageSanitizer(Protocol):
    def sanitize(self, source: Path, plan: SanitizationPlan) -> Path: ...


class ImageVerifier(Protocol):
    def verify(
        self,
        source: Path,
        output: Path,
        redactions: list[RedactionRegion],
    ) -> VerificationResult: ...


class PdfInspector(Protocol):
    def inspect(self, path: Path, limits: ResourceLimits, run_ocr: bool) -> InspectionReport: ...


class PdfRenderer(Protocol):
    def render_page(self, path: Path, page_index: int, dpi: int, output: Path) -> Path: ...


class PdfBuilder(Protocol):
    def sanitize(self, source: Path, plan: SanitizationPlan) -> Path: ...


class PdfVerifier(Protocol):
    def verify(
        self,
        source: Path,
        output: Path,
        redactions: list[RedactionRegion],
    ) -> VerificationResult: ...


class OcrEngine(Protocol):
    @property
    def available(self) -> bool: ...

    def extract(
        self,
        image_path: Path,
        page_index: int = 0,
        *,
        timeout_seconds: int | float | None = None,
    ) -> list[Any]: ...


class MetadataInspector(Protocol):
    @property
    def available(self) -> bool: ...

    def inspect(self, path: Path) -> dict[str, Any]: ...


class FindingDetector(Protocol):
    def detect(
        self,
        text: str,
        source: FindingSource,
        page_index: int | None = None,
        rect: NormalizedRect | None = None,
    ) -> Iterable[Finding]: ...


class ReportWriter(Protocol):
    def write(self, report: Any, path: Path) -> Path: ...


class WorkerEventSink(Protocol):
    def emit(self, event_type: str, job_id: str, payload: dict[str, Any]) -> None: ...


class MediaSniffer(Protocol):
    def detect(self, path: Path) -> MediaType: ...
