from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from cleandrop.cli import (
    EXIT_OK,
    EXIT_VALIDATION,
    EXIT_VERIFICATION,
    EXIT_WARNINGS,
    main,
)


def test_doctor_and_human_inspection(
    jpg_with_metadata: Path,
    capsys: object,
) -> None:
    assert main(["doctor"]) == EXIT_OK
    doctor = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert doctor["Tesseract"]["available"]
    assert doctor["ExifTool"]["available"]
    exit_code = main(["inspect", str(jpg_with_metadata), "--no-ocr"])
    assert exit_code in {EXIT_OK, EXIT_WARNINGS}
    human = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "SHA-256:" in human
    assert "Findings:" in human


def test_verify_and_batch_commands(
    jpg_with_metadata: Path,
    png_with_text: Path,
    tmp_path: Path,
    capsys: object,
) -> None:
    output = tmp_path / "clean.jpg"
    sanitize_exit = main(
        [
            "sanitize",
            str(jpg_with_metadata),
            "--output",
            str(output),
            "--no-ocr",
            "--no-auto-redact",
        ]
    )
    assert sanitize_exit in {EXIT_OK, EXIT_WARNINGS}
    capsys.readouterr()  # type: ignore[attr-defined]
    assert main(["verify", str(output), "--source", str(jpg_with_metadata), "--json"]) == EXIT_OK
    verification = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert verification["status"] in {"passed", "passed_with_warnings"}

    output_dir = tmp_path / "batch"
    batch_exit = main(
        [
            "batch",
            str(jpg_with_metadata),
            str(png_with_text),
            "--output-dir",
            str(output_dir),
            "--no-ocr",
            "--json",
        ]
    )
    assert batch_exit in {EXIT_OK, EXIT_WARNINGS}
    batch = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert len(batch) == 2
    assert all("output_name" in result for result in batch)


def test_cli_validation_and_failed_verification(tmp_path: Path, capsys: object) -> None:
    image = tmp_path / "image.jpg"
    Image.new("RGB", (40, 40), "white").save(image)
    assert (
        main(
            [
                "sanitize",
                str(image),
                "--redact",
                "bad",
                "--no-ocr",
            ]
        )
        == EXIT_VALIDATION
    )
    assert "VALIDATION_ERROR" in capsys.readouterr().err  # type: ignore[attr-defined]
    fake = tmp_path / "fake.jpg"
    fake.write_bytes(b"\xff\xd8\xffbroken")
    assert main(["verify", str(fake)]) in {EXIT_VERIFICATION, 20}
