from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from cleandrop.cli import EXIT_OK, EXIT_WARNINGS, _configure_streams, main


def test_cli_forces_utf8_for_windows_unicode_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ConfigurableStream:
        def __init__(self) -> None:
            self.configuration: dict[str, str] = {}

        def reconfigure(self, **configuration: str) -> None:
            self.configuration = configuration

    stdout = ConfigurableStream()
    stderr = ConfigurableStream()
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "stderr", stderr)

    _configure_streams()

    assert stdout.configuration == {"encoding": "utf-8", "errors": "replace"}
    assert stderr.configuration == {"encoding": "utf-8", "errors": "replace"}


def test_cli_inspect_json(jpg_with_metadata: Path, capsys: object) -> None:
    exit_code = main(["inspect", str(jpg_with_metadata), "--json", "--no-ocr"])
    assert exit_code in {EXIT_OK, EXIT_WARNINGS}
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    payload = json.loads(captured.out)
    assert payload["media_type"] == "image/jpeg"
    assert payload["input_sha256"]


def test_cli_sanitize_creates_output_and_report(
    jpg_with_metadata: Path,
    tmp_path: Path,
    capsys: object,
) -> None:
    output = tmp_path / "share.jpg"
    exit_code = main(
        [
            "sanitize",
            str(jpg_with_metadata),
            "--output",
            str(output),
            "--no-ocr",
            "--json",
            "--redact",
            "1,0.1,0.1,0.2,0.2",
        ]
    )
    assert exit_code in {EXIT_OK, EXIT_WARNINGS}
    assert output.exists()
    assert output.with_suffix(".jpg.cleandrop.json").exists()
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    payload = json.loads(captured.out)
    assert payload["verification"]["status"] in {"passed", "passed_with_warnings"}
    assert set(payload) >= {
        "schema_version",
        "application_version",
        "job_id",
        "input",
        "inspection",
        "sanitization_plan",
        "verification",
        "warnings",
        "output",
    }
    serialized = json.dumps(payload, ensure_ascii=False)
    assert str(tmp_path) not in serialized
    assert jpg_with_metadata.name not in serialized
    assert output.name not in serialized
    assert payload["input"]["sha256"]
    assert payload["output"]["sha256"]
