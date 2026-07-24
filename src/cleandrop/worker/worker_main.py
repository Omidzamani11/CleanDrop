from __future__ import annotations

import logging
import sys
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from cleandrop.adapters.filetypes import MagicByteSniffer
from cleandrop.adapters.pdf import PdfMediaAdapter
from cleandrop.composition import (
    build_inspect_service,
    build_job_service,
    build_verify_service,
)
from cleandrop.domain.errors import CleanDropError
from cleandrop.domain.models import NormalizedRect, RedactionRegion, ResourceLimits
from cleandrop.security.paths import validate_input_path
from cleandrop.security.tempfiles import cleanup_worker_temporary_files
from cleandrop.worker.protocol import JsonLineEventSink, parse_request


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )


def _configure_streams() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def _redactions(payload: dict[str, Any]) -> list[RedactionRegion]:
    regions: list[RedactionRegion] = []
    for item in payload.get("manual_redactions", []):
        rect = item["rect"]
        regions.append(
            RedactionRegion(
                page_index=int(item["page_index"]),
                rect=NormalizedRect(
                    float(rect["x"]),
                    float(rect["y"]),
                    float(rect["width"]),
                    float(rect["height"]),
                ),
                source_finding_id=item.get("source_finding_id"),
                fill_mode="black",
                reason=str(item.get("reason", "manual")),
            )
        )
    return regions


def handle(request: dict[str, Any], sink: JsonLineEventSink) -> int:
    command = request["command"]
    payload: dict[str, Any] = request.get("payload", {})
    job_id = str(request.get("job_id") or uuid.uuid4())
    try:
        if command == "inspect":
            source = Path(str(payload["input_path"]))
            sink.emit("job_started", job_id, {"input_name": source.name})
            sink.emit("stage_started", job_id, {"stage": "inspecting", "progress": 10})
            inspection = build_inspect_service().inspect(
                source,
                ResourceLimits(),
                bool(payload.get("run_ocr", True)),
            )
            for finding in inspection.findings:
                sink.emit(
                    "finding",
                    job_id,
                    {
                        "finding": asdict(finding),
                    },
                )
            sink.emit(
                "completed",
                job_id,
                {
                    "progress": 100,
                    "inspection": asdict(inspection),
                    "private_review": True,
                },
            )
            return 0
        if command == "sanitize":
            source = Path(str(payload["input_path"]))
            report = build_job_service(event_sink=sink).run(
                source,
                output=Path(str(payload["output_path"])) if payload.get("output_path") else None,
                report_path=Path(str(payload["report_path"]))
                if payload.get("report_path")
                else None,
                selected_finding_ids=set(payload.get("selected_finding_ids", [])),
                manual_redactions=_redactions(payload),
                dpi=int(payload.get("dpi", 200)),
                run_ocr=bool(payload.get("run_ocr", True)),
            )
            sink.emit(
                "completed",
                report.job_id,
                {
                    "progress": 100,
                    "report": report.to_dict(),
                    "private_output_path": report.output_path,
                    "private_review": True,
                },
            )
            return 0
        if command == "verify":
            output = validate_input_path(Path(str(payload["output_path"])), ResourceLimits())
            source_value = payload.get("source_path")
            source = (
                validate_input_path(Path(str(source_value)), ResourceLimits())
                if source_value
                else output
            )
            media_type = MagicByteSniffer().detect(output)
            result = build_verify_service().verify(source, output, media_type, [])
            sink.emit(
                "completed",
                job_id,
                {"progress": 100, "verification": asdict(result)},
            )
            return 0 if result.passed else 30
        if command == "preview":
            source = validate_input_path(Path(str(payload["input_path"])), ResourceLimits())
            destination = Path(str(payload["output_path"]))
            page_index = int(payload.get("page_index", 0))
            media_type = MagicByteSniffer().detect(source)
            if media_type.value == "application/pdf":
                PdfMediaAdapter().render_page(source, page_index, 120, destination)
            else:
                with Image.open(source) as opened:
                    opened.load()
                    preview = ImageOps.exif_transpose(opened).convert("RGB")
                    preview.thumbnail((1800, 1800))
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    preview.save(destination, format="PNG", optimize=True)
            sink.emit(
                "completed",
                job_id,
                {
                    "progress": 100,
                    "preview_path": str(destination),
                    "page_index": page_index,
                },
            )
            return 0
        if command == "cleanup":
            directories = [
                Path(str(value))
                for value in payload.get("directories", [])
                if isinstance(value, str)
            ]
            removed = cleanup_worker_temporary_files(
                directories,
                int(payload.get("worker_pid", 0)),
            )
            sink.emit(
                "completed",
                job_id,
                {"progress": 100, "removed_temporary_paths": removed},
            )
            return 0
        raise ValueError(f"Unsupported worker command: {command}")
    except CleanDropError as exc:
        sink.emit("error", job_id, {"error_code": exc.code, "message": str(exc)})
        return 20
    except (KeyError, TypeError, ValueError) as exc:
        sink.emit(
            "error",
            job_id,
            {"error_code": "INVALID_WORKER_REQUEST", "message": str(exc)},
        )
        return 10


def main() -> int:
    _configure_streams()
    _configure_logging()
    line = sys.stdin.readline()
    if not line:
        return 10
    sink = JsonLineEventSink(sys.stdout)
    try:
        request = parse_request(line)
    except (ValueError, TypeError) as exc:
        sink.emit(
            "error",
            str(uuid.uuid4()),
            {"error_code": "INVALID_WORKER_REQUEST", "message": str(exc)},
        )
        return 10
    return handle(request, sink)


if __name__ == "__main__":
    raise SystemExit(main())
