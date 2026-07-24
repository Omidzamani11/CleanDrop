from __future__ import annotations

import shutil
from collections.abc import Iterable
from pathlib import Path


def cleanup_worker_temporary_files(
    directories: Iterable[Path],
    worker_pid: int,
) -> int:
    """Remove only temporary paths created by one terminated CleanDrop worker."""
    if worker_pid <= 0:
        return 0
    prefixes = (
        f".cleandrop-{worker_pid}-",
        f".cleandrop-report-{worker_pid}-",
    )
    removed = 0
    for directory in directories:
        if directory.is_symlink() or not directory.is_dir():
            continue
        try:
            root = directory.resolve(strict=True)
        except OSError:
            continue
        for child in root.iterdir():
            if child.is_symlink() or not child.name.startswith(prefixes):
                continue
            try:
                if child.parent.resolve(strict=True) != root:
                    continue
                if child.is_dir():
                    shutil.rmtree(child)
                elif child.is_file():
                    child.unlink()
                else:
                    continue
                removed += 1
            except OSError:
                continue
    return removed
