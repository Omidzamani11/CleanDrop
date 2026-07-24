from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


def _is_ascii(path: Path) -> bool:
    try:
        str(path).encode("ascii")
    except UnicodeEncodeError:
        return False
    return True


@contextmanager
def ascii_tool_input(path: Path) -> Iterator[Path]:
    """Give legacy Windows CLIs an ASCII path without altering the original."""
    if _is_ascii(path):
        yield path
        return
    suffix = path.suffix.lower()
    if not suffix.isascii() or len(suffix) > 12:
        suffix = ".bin"
    with tempfile.TemporaryDirectory(prefix="cleandrop-tool-input-") as temp_dir:
        safe_path = Path(temp_dir) / f"input{suffix}"
        try:
            os.link(path, safe_path)
        except OSError:
            shutil.copyfile(path, safe_path)
        yield safe_path
