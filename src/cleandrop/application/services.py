from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from cleandrop import __version__
from cleandrop.application.ports import (
    ImageInspector,
    ImageSanitizer,
    ImageVerifier,
    MediaSniffer,
    PdfBuilder,
    PdfInspector,
    PdfVerifier,
    ReportWriter,
    WorkerEventSink,
)
from cleandrop.domain.errors import CleanDropError, JobCancelledError, ResourceLimitError
from cleandrop.domain.models import (
    Finding,
    InspectionReport,
    JobReport,
    JobState,
    MediaType,
    RedactionRegion,
    ResourceLimits,
    SanitizationPlan,
    SanitizationProfile,
    VerificationResult,
    VerificationStatus,
)
from cleandrop.domain.state_machine import JobStateMachine
from cleandrop.security.paths import next_output_path, validate_input_path


class NullEventSink:
    def emit(self, event_type: str, job_id: str, payload: dict[str, Any]) -> None:
        return


class InspectService:
    def __init__(
        self,
        image: ImageInspector,
        pdf: PdfInspector,
        sniffer: MediaSniffer,
    ) -> None:
        self.image = image
        self.pdf = pdf
        self.sniffer = sniffer

    def inspect(
        self,
        path: Path,
        limits: ResourceLimits | None = None,
        run_ocr: bool = True,
    ) -> InspectionReport:
        active_limits = limits or ResourceLimits()
        validated = validate_input_path(path, active_limits)
        media_type = self.sniffer.detect(validated)
        if media_type is MediaType.PDF:
            return self.pdf.inspect(validated, active_limits, run_ocr)
        return self.image.inspect(validated, active_limits, run_ocr)


class PlanningService:
    def create_plan(
        self,
        source: Path,
        inspection: InspectionReport,
        output: Path | None = None,
        selected_finding_ids: set[str] | None = None,
        manual_redactions: list[RedactionRegion] | None = None,
        dpi: int = 200,
    ) -> SanitizationPlan:
        selected = selected_finding_ids
        redactions = [
            RedactionRegion(
                page_index=finding.page_index or 0,
                rect=finding.rect,
                source_finding_id=finding.id,
                reason=finding.kind.value,
            )
            for finding in inspection.findings
            if finding.rect is not None
            and finding.selected
            and (selected is None or finding.id in selected)
        ]
        redactions.extend(manual_redactions or [])
        profile = (
            SanitizationProfile.SECURE_FLATTEN
            if inspection.media_type is MediaType.PDF
            else SanitizationProfile.PIXEL_REBUILD
        )
        valid_extensions = {
            MediaType.JPEG: {".jpg", ".jpeg"},
            MediaType.PNG: {".png"},
            MediaType.PDF: {".pdf"},
        }[inspection.media_type]
        preferred_extension = {
            MediaType.JPEG: ".jpg",
            MediaType.PNG: ".png",
            MediaType.PDF: ".pdf",
        }[inspection.media_type]
        if output is None:
            extension = (
                source.suffix.lower()
                if source.suffix.lower() in valid_extensions
                else preferred_extension
            )
            requested_output = source.with_name(f"{source.stem}.cleaned{extension}")
        else:
            requested_output = (
                output
                if output.suffix.lower() in valid_extensions
                else output.with_suffix(preferred_extension)
            )
        return SanitizationPlan(
            profile=profile,
            output_path=str(next_output_path(source, requested_output)),
            redactions=redactions,
            dpi=dpi,
        )


class SanitizeService:
    def __init__(
        self,
        image: ImageSanitizer,
        pdf: PdfBuilder,
    ) -> None:
        self.image = image
        self.pdf = pdf

    def sanitize(
        self,
        source: Path,
        media_type: MediaType,
        plan: SanitizationPlan,
    ) -> Path:
        if media_type is MediaType.PDF:
            return self.pdf.sanitize(source, plan)
        return self.image.sanitize(source, plan)


class VerifyService:
    def __init__(
        self,
        image: ImageVerifier,
        pdf: PdfVerifier,
    ) -> None:
        self.image = image
        self.pdf = pdf

    def verify(
        self,
        source: Path,
        output: Path,
        media_type: MediaType,
        redactions: list[RedactionRegion],
    ) -> VerificationResult:
        if media_type is MediaType.PDF:
            return self.pdf.verify(source, output, redactions)
        return self.image.verify(source, output, redactions)


class ReportService:
    def __init__(self, writer: ReportWriter) -> None:
        self.writer = writer

    def write(self, report: JobReport, path: Path) -> Path:
        return self.writer.write(report.to_dict(), path)


class JobService:
    def __init__(
        self,
        inspect_service: InspectService,
        planning_service: PlanningService,
        sanitize_service: SanitizeService,
        verify_service: VerifyService,
        report_service: ReportService,
        event_sink: WorkerEventSink | None = None,
    ) -> None:
        self.inspect_service = inspect_service
        self.planning_service = planning_service
        self.sanitize_service = sanitize_service
        self.verify_service = verify_service
        self.report_service = report_service
        self.event_sink = event_sink or NullEventSink()

    def run(
        self,
        source: Path,
        *,
        output: Path | None = None,
        report_path: Path | None = None,
        selected_finding_ids: set[str] | None = None,
        manual_redactions: list[RedactionRegion] | None = None,
        dpi: int = 200,
        run_ocr: bool = True,
        limits: ResourceLimits | None = None,
        cancel_check: Any | None = None,
    ) -> JobReport:
        job_id = str(uuid.uuid4())
        state = JobStateMachine()
        active_limits = limits or ResourceLimits()
        started = time.monotonic()

        def cancelled() -> bool:
            return bool(cancel_check and cancel_check())

        def guard() -> None:
            if cancelled():
                state.transition(JobState.CANCELLED)
                raise JobCancelledError("The job was cancelled")
            if time.monotonic() - started > active_limits.max_job_seconds:
                raise ResourceLimitError("The job exceeded the configured time limit")

        def stage(target: JobState, progress: int) -> None:
            state.transition(target)
            self.event_sink.emit(
                "stage_started",
                job_id,
                {"stage": target.value, "progress": progress},
            )
            guard()

        self.event_sink.emit("job_started", job_id, {"input_name": source.name})
        try:
            stage(JobState.VALIDATING, 2)
            stage(JobState.INSPECTING, 8)
            inspection = self.inspect_service.inspect(source, active_limits, run_ocr)
            self.event_sink.emit(
                "progress",
                job_id,
                {"progress": 38, "finding_count": len(inspection.findings)},
            )
            stage(JobState.REVIEW_REQUIRED, 42)
            guard()
            plan = self.planning_service.create_plan(
                source,
                inspection,
                output,
                selected_finding_ids,
                manual_redactions,
                dpi,
            )
            stage(JobState.PLAN_READY, 48)
            stage(JobState.SANITIZING, 52)
            output_path = self.sanitize_service.sanitize(source, inspection.media_type, plan)
            stage(JobState.VERIFYING, 88)
            verification = self.verify_service.verify(
                source,
                output_path,
                inspection.media_type,
                plan.redactions,
            )
            if not verification.passed:
                state.transition(JobState.FAILED)
                raise CleanDropError("Verification failed; no successful result was declared")
            warnings = list(inspection.warnings)
            warnings.extend(
                check.message
                for check in verification.checks
                if check.status.value == "warning" and check.message
            )
            terminal = (
                JobState.COMPLETED_WITH_WARNINGS
                if verification.status is VerificationStatus.PASSED_WITH_WARNINGS or warnings
                else JobState.COMPLETED
            )
            state.transition(terminal)
            report = JobReport(
                schema_version="1.0",
                application_version=__version__,
                job_id=job_id,
                state=terminal,
                inspection=inspection,
                sanitization_plan=plan,
                verification=verification,
                output_path=str(output_path),
                warnings=warnings,
            )
            destination = report_path or output_path.with_suffix(
                f"{output_path.suffix}.cleandrop.json"
            )
            self.report_service.write(report, destination)
            self.event_sink.emit(
                "completed",
                job_id,
                {
                    "progress": 100,
                    "state": terminal.value,
                    "output_name": output_path.name,
                    "report_name": destination.name,
                },
            )
            return report
        except JobCancelledError:
            self.event_sink.emit("cancelled", job_id, {})
            raise
        except CleanDropError as exc:
            self.event_sink.emit(
                "error",
                job_id,
                {"error_code": exc.code, "message": str(exc)},
            )
            raise


def selected_ids(findings: list[Finding]) -> set[str]:
    return {finding.id for finding in findings if finding.selected}
