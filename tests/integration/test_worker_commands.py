from __future__ import annotations

import io
import json
from pathlib import Path

from cleandrop.security.tempfiles import cleanup_worker_temporary_files
from cleandrop.worker.protocol import JsonLineEventSink
from cleandrop.worker.worker_main import handle


def _events(stream: io.StringIO) -> list[dict[str, object]]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line]


def _request(command: str, payload: dict[str, object]) -> dict[str, object]:
    return {
        "protocol_version": "1.0",
        "command": command,
        "job_id": f"job-{command}",
        "payload": payload,
    }


def test_worker_inspect_preview_sanitize_verify(
    jpg_with_metadata: Path,
    tmp_path: Path,
) -> None:
    inspect_stream = io.StringIO()
    assert (
        handle(
            _request(
                "inspect",
                {"input_path": str(jpg_with_metadata), "run_ocr": False},
            ),
            JsonLineEventSink(inspect_stream),
        )
        == 0
    )
    assert any(event["event_type"] == "completed" for event in _events(inspect_stream))

    preview = tmp_path / "preview.png"
    preview_stream = io.StringIO()
    assert (
        handle(
            _request(
                "preview",
                {
                    "input_path": str(jpg_with_metadata),
                    "output_path": str(preview),
                    "page_index": 0,
                },
            ),
            JsonLineEventSink(preview_stream),
        )
        == 0
    )
    assert preview.exists()

    output = tmp_path / "worker-clean.jpg"
    sanitize_stream = io.StringIO()
    assert (
        handle(
            _request(
                "sanitize",
                {
                    "input_path": str(jpg_with_metadata),
                    "output_path": str(output),
                    "selected_finding_ids": [],
                    "manual_redactions": [
                        {
                            "page_index": 0,
                            "rect": {"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2},
                            "reason": "manual",
                        }
                    ],
                    "run_ocr": False,
                },
            ),
            JsonLineEventSink(sanitize_stream),
        )
        == 0
    )
    assert output.exists()
    assert any(
        isinstance(event.get("payload"), dict) and "report" in event["payload"]
        for event in _events(sanitize_stream)
    )

    verify_stream = io.StringIO()
    assert (
        handle(
            _request(
                "verify",
                {"output_path": str(output), "source_path": str(jpg_with_metadata)},
            ),
            JsonLineEventSink(verify_stream),
        )
        == 0
    )
    assert any(
        isinstance(event.get("payload"), dict) and "verification" in event["payload"]
        for event in _events(verify_stream)
    )


def test_worker_cleanup_and_invalid_request(tmp_path: Path) -> None:
    pid = 424242
    first = tmp_path / f".cleandrop-{pid}-one"
    first.mkdir()
    (first / "partial.bin").write_bytes(b"partial")
    report = tmp_path / f".cleandrop-report-{pid}-abc.tmp"
    report.write_text("partial", encoding="utf-8")
    unrelated = tmp_path / ".cleandrop-999-other"
    unrelated.mkdir()
    assert cleanup_worker_temporary_files([tmp_path], pid) == 2
    assert not first.exists()
    assert not report.exists()
    assert unrelated.exists()

    cleanup_stream = io.StringIO()
    assert (
        handle(
            _request(
                "cleanup",
                {"directories": [str(tmp_path)], "worker_pid": pid},
            ),
            JsonLineEventSink(cleanup_stream),
        )
        == 0
    )
    invalid_stream = io.StringIO()
    assert (
        handle(
            _request("unknown", {}),
            JsonLineEventSink(invalid_stream),
        )
        == 10
    )
    assert _events(invalid_stream)[0]["event_type"] == "error"
