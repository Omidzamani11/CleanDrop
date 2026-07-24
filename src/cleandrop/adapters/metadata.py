from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from cleandrop.domain.errors import ExternalToolError


def _runtime_root() -> Path:
    import sys

    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[3]


class ExifToolMetadataInspector:
    def __init__(self, executable: Path | None = None, timeout_seconds: int = 30) -> None:
        bundled = _runtime_root() / "vendor" / "exiftool" / "exiftool.exe"
        discovered = shutil.which("exiftool")
        self.executable = executable or (bundled if bundled.exists() else None)
        if self.executable is None and discovered:
            self.executable = Path(discovered)
        self.timeout_seconds = timeout_seconds

    @property
    def available(self) -> bool:
        return self.executable is not None and self.executable.exists()

    def inspect(self, path: Path) -> dict[str, Any]:
        if not self.available or self.executable is None:
            return {}
        environment = os.environ.copy()
        environment["LANG"] = "C.UTF-8"
        with tempfile.TemporaryDirectory(prefix="cleandrop-exiftool-") as temp_dir:
            argument_file = Path(temp_dir) / "input.args"
            argument_file.write_text(f"{path}\n", encoding="utf-8", newline="\n")
            command = [
                str(self.executable),
                "-json",
                "-struct",
                "-G1",
                "-charset",
                "filename=UTF8",
                "-@",
                str(argument_file),
            ]
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=self.timeout_seconds,
                    check=False,
                    shell=False,
                    env=environment,
                )
            except subprocess.TimeoutExpired as exc:
                raise ExternalToolError("ExifTool timed out") from exc
            except OSError as exc:
                raise ExternalToolError("ExifTool could not start") from exc
        if result.returncode != 0:
            raise ExternalToolError(f"ExifTool failed with exit code {result.returncode}")
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ExternalToolError("ExifTool returned invalid JSON") from exc
        if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
            raise ExternalToolError("ExifTool returned an invalid metadata response")
        return {str(key): value for key, value in payload[0].items() if key != "SourceFile"}
