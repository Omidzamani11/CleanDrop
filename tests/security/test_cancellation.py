from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import fitz
import pytest

from cleandrop.security.tempfiles import cleanup_worker_temporary_files


@pytest.mark.security
def test_terminated_worker_leaves_no_final_or_partial_output(tmp_path: Path) -> None:
    source = tmp_path / "large-private.pdf"
    with fitz.open() as document:
        for _ in range(24):
            page = document.new_page(width=595, height=842)
            page.insert_text((40, 80), "private@example.com 09123456789")
        document.save(source)

    output = tmp_path / "large-private.cleaned.pdf"
    request = {
        "protocol_version": "1.0",
        "command": "sanitize",
        "job_id": "cancel-security-test",
        "payload": {
            "input_path": str(source),
            "output_path": str(output),
            "selected_finding_ids": [],
            "manual_redactions": [],
            "run_ocr": False,
            "dpi": 300,
        },
    }
    process = subprocess.Popen(
        [sys.executable, "-m", "cleandrop.worker.worker_main"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert process.stdin is not None
    assert process.stdout is not None
    process.stdin.write(json.dumps(request) + "\n")
    process.stdin.close()

    reached_sanitizing = False
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        line = process.stdout.readline()
        if not line:
            break
        event = json.loads(line)
        payload = event.get("payload", {})
        if (
            event.get("event_type") == "stage_started"
            and isinstance(payload, dict)
            and payload.get("stage") == "sanitizing"
        ):
            reached_sanitizing = True
            process.terminate()
            break

    if process.poll() is None:
        process.kill()
    process.wait(timeout=15)
    assert reached_sanitizing
    cleanup_worker_temporary_files([tmp_path], process.pid)
    assert source.exists()
    assert not output.exists()
    assert not list(tmp_path.glob(f".cleandrop-{process.pid}-*"))
    assert not list(tmp_path.glob(f".cleandrop-report-{process.pid}-*"))
