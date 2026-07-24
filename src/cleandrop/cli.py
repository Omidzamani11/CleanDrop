from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

import fitz
import pikepdf
import PIL
import PySide6

from cleandrop import __version__
from cleandrop.adapters.filetypes import MagicByteSniffer
from cleandrop.adapters.metadata import ExifToolMetadataInspector
from cleandrop.adapters.ocr import TesseractOcrEngine
from cleandrop.adapters.report import to_json
from cleandrop.composition import (
    build_inspect_service,
    build_job_service,
    build_verify_service,
)
from cleandrop.domain.errors import CleanDropError
from cleandrop.domain.models import NormalizedRect, RedactionRegion, ResourceLimits
from cleandrop.security.paths import next_output_path, validate_input_path

EXIT_OK = 0
EXIT_WARNINGS = 2
EXIT_VALIDATION = 10
EXIT_PROCESSING = 20
EXIT_VERIFICATION = 30
EXIT_CANCELLED = 40
EXIT_INTERNAL = 70


def _configure_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cleandrop",
        description="Local-first privacy cleaning for images and PDFs.",
    )
    parser.add_argument("--version", action="version", version=f"CleanDrop {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect = subparsers.add_parser("inspect", help="Inspect metadata and sensitive content")
    inspect.add_argument("input", type=Path)
    inspect.add_argument("--json", action="store_true")
    inspect.add_argument("--no-ocr", action="store_true")

    sanitize = subparsers.add_parser("sanitize", help="Create and verify a cleaned copy")
    sanitize.add_argument("input", type=Path)
    sanitize.add_argument("--profile", choices=["secure-flatten", "pixel-rebuild"])
    sanitize.add_argument("--dpi", type=int, choices=[150, 200, 300], default=200)
    sanitize.add_argument("--output", type=Path)
    sanitize.add_argument("--report", type=Path)
    sanitize.add_argument("--no-ocr", action="store_true")
    sanitize.add_argument("--no-auto-redact", action="store_true")
    sanitize.add_argument(
        "--redact",
        action="append",
        default=[],
        metavar="PAGE,X,Y,W,H",
        help="Add a manual normalized redaction rectangle",
    )
    sanitize.add_argument("--json", action="store_true")

    verify = subparsers.add_parser("verify", help="Verify a cleaned output")
    verify.add_argument("output", type=Path)
    verify.add_argument("--source", type=Path)
    verify.add_argument("--policy", choices=["secure-share"], default="secure-share")
    verify.add_argument("--json", action="store_true")

    batch = subparsers.add_parser("batch", help="Sanitize multiple files")
    batch.add_argument("inputs", type=Path, nargs="+")
    batch.add_argument("--output-dir", type=Path, required=True)
    batch.add_argument("--dpi", type=int, choices=[150, 200, 300], default=200)
    batch.add_argument("--no-ocr", action="store_true")
    batch.add_argument("--json", action="store_true")

    subparsers.add_parser("doctor", help="Check runtime capabilities")
    return parser


def _manual_regions(values: list[str]) -> list[RedactionRegion]:
    regions: list[RedactionRegion] = []
    for value in values:
        parts = value.split(",")
        if len(parts) != 5:
            raise ValueError("--redact requires PAGE,X,Y,W,H")
        page = int(parts[0]) - 1
        if page < 0:
            raise ValueError("Redaction page numbers start at 1")
        regions.append(
            RedactionRegion(
                page,
                NormalizedRect(*(float(part) for part in parts[1:])),
                reason="manual",
            )
        )
    return regions


def _print_human_inspection(report: Any) -> None:
    print(f"File: {report.input_name}")
    print(f"Type: {report.media_type.value}")
    print(f"SHA-256: {report.input_sha256}")
    print(f"Pages: {report.page_count}")
    print(f"Findings: {len(report.findings)}")
    for finding in report.findings:
        page = f", page {finding.page_index + 1}" if finding.page_index is not None else ""
        print(
            f"  - {finding.kind.value}: {finding.masked_preview} ({finding.confidence:.0%}{page})"
        )
    for warning in report.warnings:
        print(f"Warning: {warning}")


def _doctor() -> int:
    ocr = TesseractOcrEngine()
    metadata = ExifToolMetadataInspector()
    temp_writable = False
    try:
        with tempfile.NamedTemporaryFile():
            temp_writable = True
    except OSError:
        pass
    capabilities = {
        "CleanDrop": {"available": True, "version": __version__},
        "Python": {"available": True, "version": sys.version.split()[0]},
        "PySide6": {"available": True, "version": PySide6.__version__},
        "PyMuPDF": {"available": True, "version": fitz.VersionBind},
        "pikepdf": {"available": True, "version": pikepdf.__version__},
        "Pillow": {"available": True, "version": PIL.__version__},
        "Tesseract": {"available": ocr.available, "path": str(ocr.executable or "")},
        "fas.traineddata": {"available": ocr.languages()["fas"]},
        "eng.traineddata": {"available": ocr.languages()["eng"]},
        "osd.traineddata": {"available": ocr.languages()["osd"]},
        "ExifTool": {
            "available": metadata.available,
            "path": str(metadata.executable or ""),
        },
        "Temporary directory": {"available": temp_writable},
        "Write permission": {"available": temp_writable},
    }
    print(to_json(capabilities))
    required = (
        "CleanDrop",
        "Python",
        "PySide6",
        "PyMuPDF",
        "pikepdf",
        "Pillow",
        "Temporary directory",
        "Write permission",
    )
    return EXIT_OK if all(capabilities[key]["available"] for key in required) else EXIT_PROCESSING


def _run(args: argparse.Namespace) -> int:
    if args.command == "doctor":
        return _doctor()
    if args.command == "inspect":
        inspection_report = build_inspect_service().inspect(
            args.input,
            run_ocr=not args.no_ocr,
        )
        print(to_json(asdict(inspection_report)) if args.json else "")
        if not args.json:
            _print_human_inspection(inspection_report)
        return EXIT_WARNINGS if inspection_report.warnings else EXIT_OK
    if args.command == "sanitize":
        validated = validate_input_path(args.input, ResourceLimits())
        media_type = MagicByteSniffer().detect(validated)
        expected_profile = (
            "secure-flatten" if media_type.value == "application/pdf" else "pixel-rebuild"
        )
        if args.profile is not None and args.profile != expected_profile:
            raise ValueError(f"{args.profile} is not valid for this file; use {expected_profile}")
        manual = _manual_regions(args.redact)
        selected: set[str] | None = None
        if args.no_auto_redact:
            selected = set()
        job_report = build_job_service().run(
            args.input,
            output=args.output,
            report_path=args.report,
            selected_finding_ids=selected,
            manual_redactions=manual,
            dpi=args.dpi,
            run_ocr=not args.no_ocr,
        )
        if args.json:
            print(to_json(job_report.to_dict()))
        else:
            print(f"Output: {job_report.output_path}")
            print(f"State: {job_report.state.value}")
            print(f"Output SHA-256: {job_report.verification.output_sha256}")
        return EXIT_WARNINGS if job_report.warnings else EXIT_OK
    if args.command == "verify":
        output = validate_input_path(args.output, ResourceLimits())
        source = validate_input_path(args.source, ResourceLimits()) if args.source else output
        media_type = MagicByteSniffer().detect(output)
        verification = build_verify_service().verify(source, output, media_type, [])
        if args.json:
            print(to_json(asdict(verification)))
        else:
            for check in verification.checks:
                print(f"{check.status.value.upper():7} {check.name} {check.message}".rstrip())
        return EXIT_OK if verification.passed else EXIT_VERIFICATION
    if args.command == "batch":
        if len(args.inputs) > ResourceLimits().max_batch_files:
            raise ValueError("Batch exceeds the configured file limit")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        results: list[dict[str, Any]] = []
        highest_exit = EXIT_OK
        job_service = build_job_service()
        for source in args.inputs:
            try:
                output = next_output_path(
                    source,
                    args.output_dir / f"{source.stem}.cleaned{source.suffix.lower()}",
                )
                batch_report = job_service.run(
                    source,
                    output=output,
                    dpi=args.dpi,
                    run_ocr=not args.no_ocr,
                )
                results.append(
                    {
                        "input_name": source.name,
                        "output_name": Path(batch_report.output_path).name,
                        "state": batch_report.state.value,
                    }
                )
                if batch_report.warnings:
                    highest_exit = max(highest_exit, EXIT_WARNINGS)
            except CleanDropError as exc:
                results.append(
                    {"input_name": source.name, "error_code": exc.code, "message": str(exc)}
                )
                highest_exit = max(highest_exit, EXIT_PROCESSING)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            for result in results:
                print(result)
        return highest_exit
    return EXIT_INTERNAL


def main(argv: Sequence[str] | None = None) -> int:
    _configure_streams()
    args = _parser().parse_args(argv)
    try:
        return _run(args)
    except ValueError as exc:
        print(f"VALIDATION_ERROR: {exc}", file=sys.stderr)
        return EXIT_VALIDATION
    except CleanDropError as exc:
        print(f"{exc.code}: {exc}", file=sys.stderr)
        return EXIT_PROCESSING
    except KeyboardInterrupt:
        print("JOB_CANCELLED: interrupted by user", file=sys.stderr)
        return EXIT_CANCELLED


if __name__ == "__main__":
    raise SystemExit(main())
