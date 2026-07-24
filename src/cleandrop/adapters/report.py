from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any


def _json_default(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


class JsonReportWriter:
    def write(self, report: Any, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            report,
            default=_json_default,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                prefix=f".cleandrop-report-{os.getpid()}-",
                suffix=".tmp",
                dir=path.parent,
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            if temp_path is None:
                raise OSError("Could not create a temporary report")
            os.replace(temp_path, path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()
        return path


def to_json(value: Any, *, indent: int | None = 2) -> str:
    return json.dumps(
        value,
        default=_json_default,
        ensure_ascii=False,
        indent=indent,
        sort_keys=True,
    )
