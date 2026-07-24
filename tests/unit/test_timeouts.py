from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from PIL import Image

from cleandrop.adapters.ocr import TesseractOcrEngine
from cleandrop.application.services import JobService
from cleandrop.domain.errors import ExternalToolError, ResourceLimitError
from cleandrop.domain.models import ResourceLimits


def test_ocr_timeout_is_reported_without_raw_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    executable = tmp_path / "tesseract.exe"
    executable.write_bytes(b"test executable marker")
    image = tmp_path / "page.png"
    Image.new("RGB", (20, 20), "white").save(image)
    engine = TesseractOcrEngine(
        executable=executable,
        tessdata=None,
        timeout_seconds=1,
    )

    def timeout(*_args: object, **_kwargs: object) -> object:
        raise subprocess.TimeoutExpired(["tesseract"], 1, output="private@example.com")

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(ExternalToolError, match="timed out") as caught:
        engine.extract(image)
    assert "private@example.com" not in str(caught.value)


def test_total_job_timeout_is_enforced_before_processing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    values = iter([100.0, 102.0])
    monkeypatch.setattr(
        "cleandrop.application.services.time.monotonic",
        lambda: next(values),
    )
    service = JobService(
        inspect_service=object(),  # type: ignore[arg-type]
        planning_service=object(),  # type: ignore[arg-type]
        sanitize_service=object(),  # type: ignore[arg-type]
        verify_service=object(),  # type: ignore[arg-type]
        report_service=object(),  # type: ignore[arg-type]
    )
    with pytest.raises(ResourceLimitError, match="time limit"):
        service.run(
            tmp_path / "not-opened.jpg",
            limits=ResourceLimits(max_job_seconds=1),
        )
