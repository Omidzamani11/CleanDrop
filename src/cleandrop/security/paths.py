from __future__ import annotations

import hashlib
import re
from pathlib import Path

from cleandrop.domain.errors import UnsafePathError, ValidationError
from cleandrop.domain.models import ResourceLimits

_UNSAFE_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def validate_input_path(path: Path, limits: ResourceLimits) -> Path:
    if path.is_symlink():
        raise UnsafePathError("Symbolic links are not accepted")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ValidationError("Input file does not exist or cannot be opened") from exc
    if not resolved.is_file():
        raise ValidationError("Input must be a regular file")
    size = resolved.stat().st_size
    if size <= 0:
        raise ValidationError("Input file is empty")
    if size > limits.max_file_size:
        raise ValidationError("Input exceeds the configured maximum file size")
    return resolved


def sanitize_filename(name: str) -> str:
    cleaned = _UNSAFE_FILENAME.sub("_", Path(name).name).strip(" .")
    if not cleaned:
        return "cleaned-output"
    return cleaned[:180]


def next_output_path(source: Path, requested: Path | None = None) -> Path:
    if requested is not None:
        candidate = requested.resolve(strict=False)
        if candidate == source.resolve(strict=True):
            raise UnsafePathError("The output may not overwrite the original file")
        candidate.parent.mkdir(parents=True, exist_ok=True)
        if not candidate.exists():
            return candidate
        index = 2
        while True:
            numbered = candidate.with_name(f"{candidate.stem}-{index}{candidate.suffix}")
            if not numbered.exists():
                return numbered
            index += 1
    base = source.with_name(f"{source.stem}.cleaned{source.suffix.lower()}")
    if not base.exists():
        return base
    index = 2
    while True:
        candidate = source.with_name(f"{source.stem}.cleaned-{index}{source.suffix.lower()}")
        if not candidate.exists():
            return candidate
        index += 1


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_path(path: Path) -> str:
    return hashlib.sha256(str(path).encode("utf-8", errors="replace")).hexdigest()
