from __future__ import annotations

from cleandrop.adapters.filetypes import MagicByteSniffer
from cleandrop.adapters.image import ImageMediaAdapter
from cleandrop.adapters.pdf import PdfMediaAdapter
from cleandrop.adapters.report import JsonReportWriter
from cleandrop.application.ports import (
    ImageInspector,
    ImageSanitizer,
    ImageVerifier,
    MediaSniffer,
    PdfBuilder,
    PdfInspector,
    PdfVerifier,
    WorkerEventSink,
)
from cleandrop.application.services import (
    InspectService,
    JobService,
    PlanningService,
    ReportService,
    SanitizeService,
    VerifyService,
)


def build_inspect_service(
    *,
    image: ImageInspector | None = None,
    pdf: PdfInspector | None = None,
    sniffer: MediaSniffer | None = None,
) -> InspectService:
    return InspectService(
        image=image or ImageMediaAdapter(),
        pdf=pdf or PdfMediaAdapter(),
        sniffer=sniffer or MagicByteSniffer(),
    )


def build_verify_service(
    *,
    image: ImageVerifier | None = None,
    pdf: PdfVerifier | None = None,
) -> VerifyService:
    return VerifyService(
        image=image or ImageMediaAdapter(),
        pdf=pdf or PdfMediaAdapter(),
    )


def build_job_service(event_sink: WorkerEventSink | None = None) -> JobService:
    image = ImageMediaAdapter()
    pdf = PdfMediaAdapter()
    return JobService(
        inspect_service=InspectService(image, pdf, MagicByteSniffer()),
        planning_service=PlanningService(),
        sanitize_service=SanitizeService(image, pdf),
        verify_service=VerifyService(image, pdf),
        report_service=ReportService(JsonReportWriter()),
        event_sink=event_sink,
    )


def build_sanitize_service(
    *,
    image: ImageSanitizer | None = None,
    pdf: PdfBuilder | None = None,
) -> SanitizeService:
    return SanitizeService(
        image=image or ImageMediaAdapter(),
        pdf=pdf or PdfMediaAdapter(),
    )
