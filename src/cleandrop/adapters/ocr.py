from __future__ import annotations

import csv
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

from PIL import Image

from cleandrop.domain.errors import ExternalToolError
from cleandrop.domain.models import NormalizedRect
from cleandrop.security.external_paths import ascii_tool_input


@dataclass(frozen=True, slots=True)
class OcrToken:
    text: str
    confidence: float
    rect: NormalizedRect
    page_index: int
    block: int
    paragraph: int
    line: int


def _runtime_root() -> Path:
    import sys

    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[3]


class TesseractOcrEngine:
    def __init__(
        self,
        executable: Path | None = None,
        tessdata: Path | None = None,
        timeout_seconds: int = 60,
    ) -> None:
        bundled = _runtime_root() / "vendor" / "tesseract" / "tesseract.exe"
        discovered = shutil.which("tesseract")
        self.executable = executable or (bundled if bundled.exists() else None)
        if self.executable is None and discovered:
            self.executable = Path(discovered)
        bundled_data = _runtime_root() / "vendor" / "tesseract" / "tessdata"
        self.tessdata = tessdata or (bundled_data if bundled_data.exists() else None)
        self.timeout_seconds = timeout_seconds

    @property
    def available(self) -> bool:
        if self.executable is None or not self.executable.exists():
            return False
        if self.tessdata is None:
            return True
        return all(
            (self.tessdata / f"{language}.traineddata").exists() for language in ("fas", "eng")
        )

    def languages(self) -> dict[str, bool]:
        if self.tessdata is None:
            if not self.available or self.executable is None:
                return {"fas": False, "eng": False, "osd": False}
            try:
                result = subprocess.run(
                    [str(self.executable), "--list-langs"],
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=min(15, self.timeout_seconds),
                    check=False,
                    shell=False,
                )
            except (subprocess.TimeoutExpired, OSError):
                return {"fas": False, "eng": False, "osd": False}
            available_languages = {
                line.strip()
                for line in f"{result.stdout}\n{result.stderr}".splitlines()
                if line.strip() in {"fas", "eng", "osd"}
            }
            return {language: language in available_languages for language in ("fas", "eng", "osd")}
        return {
            language: (self.tessdata / f"{language}.traineddata").exists()
            for language in ("fas", "eng", "osd")
        }

    def extract(
        self,
        image_path: Path,
        page_index: int = 0,
        *,
        timeout_seconds: int | float | None = None,
    ) -> list[OcrToken]:
        if not self.available or self.executable is None:
            return []
        active_timeout = float(timeout_seconds or self.timeout_seconds)
        started = time.monotonic()
        active_path = image_path
        temp_directory: tempfile.TemporaryDirectory[str] | None = None
        rotation = self.orientation_degrees(image_path, timeout_seconds=active_timeout)
        remaining = active_timeout - (time.monotonic() - started)
        if remaining <= 0:
            raise ExternalToolError("OCR timed out for this page")
        if rotation:
            temp_directory = tempfile.TemporaryDirectory(prefix="cleandrop-osd-")
            active_path = Path(temp_directory.name) / "oriented.png"
            with Image.open(image_path) as image:
                image.rotate(-rotation, expand=True).save(active_path, format="PNG")
        environment = os.environ.copy()
        if self.tessdata is not None:
            environment["TESSDATA_PREFIX"] = str(self.tessdata)
        with ascii_tool_input(active_path) as tool_path:
            command = [
                str(self.executable),
                str(tool_path),
                "stdout",
                "-l",
                "fas+eng",
                "--psm",
                "6",
                "tsv",
            ]
            try:
                result = subprocess.run(
                    command,
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=remaining,
                    check=False,
                    shell=False,
                    env=environment,
                )
            except subprocess.TimeoutExpired as exc:
                if temp_directory is not None:
                    temp_directory.cleanup()
                raise ExternalToolError("OCR timed out for this page") from exc
            except OSError as exc:
                if temp_directory is not None:
                    temp_directory.cleanup()
                raise ExternalToolError("Tesseract could not start") from exc
        if result.returncode != 0:
            if temp_directory is not None:
                temp_directory.cleanup()
            raise ExternalToolError(f"Tesseract failed with exit code {result.returncode}")
        with Image.open(active_path) as image:
            page_width, page_height = image.size
        tokens = parse_tsv(result.stdout, page_index, page_width, page_height)
        if temp_directory is not None:
            temp_directory.cleanup()
        return tokens

    def orientation_degrees(
        self,
        image_path: Path,
        *,
        timeout_seconds: int | float | None = None,
    ) -> int:
        if (
            self.executable is None
            or not self.available
            or self.tessdata is None
            or not (self.tessdata / "osd.traineddata").exists()
        ):
            return 0
        environment = os.environ.copy()
        environment["TESSDATA_PREFIX"] = str(self.tessdata)
        with ascii_tool_input(image_path) as tool_path:
            command = [
                str(self.executable),
                str(tool_path),
                "stdout",
                "-l",
                "osd",
                "--psm",
                "0",
            ]
            try:
                result = subprocess.run(
                    command,
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=min(15, timeout_seconds or self.timeout_seconds),
                    check=False,
                    shell=False,
                    env=environment,
                )
            except (subprocess.TimeoutExpired, OSError):
                return 0
        if result.returncode != 0:
            return 0
        match = re.search(r"Rotate:\s*(0|90|180|270)", result.stdout)
        return int(match.group(1)) if match else 0


def parse_tsv(
    data: str,
    page_index: int = 0,
    page_width: int | None = None,
    page_height: int | None = None,
) -> list[OcrToken]:
    tokens: list[OcrToken] = []
    rows = csv.DictReader(StringIO(data), delimiter="\t")
    for row in rows:
        text = (row.get("text") or "").strip()
        try:
            confidence_raw = float(row.get("conf") or -1)
            left = int(row.get("left") or 0)
            top = int(row.get("top") or 0)
            width = int(row.get("width") or 0)
            height = int(row.get("height") or 0)
        except ValueError:
            continue
        if not text or confidence_raw < 0 or width <= 0 or height <= 0:
            continue
        active_width = page_width or max(left + width, 1)
        active_height = page_height or max(top + height, 1)
        rect = NormalizedRect(
            max(0.0, min(1.0, left / active_width)),
            max(0.0, min(1.0, top / active_height)),
            max(1 / active_width, min(1.0 - left / active_width, width / active_width)),
            max(1 / active_height, min(1.0 - top / active_height, height / active_height)),
        )
        tokens.append(
            OcrToken(
                text=text,
                confidence=max(0.0, min(1.0, confidence_raw / 100)),
                rect=rect,
                page_index=page_index,
                block=int(row.get("block_num") or 0),
                paragraph=int(row.get("par_num") or 0),
                line=int(row.get("line_num") or 0),
            )
        )
    return tokens
