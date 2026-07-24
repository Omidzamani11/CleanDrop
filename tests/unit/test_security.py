from __future__ import annotations

from pathlib import Path

import pytest

from cleandrop.domain.errors import UnsafePathError, ValidationError
from cleandrop.domain.models import ResourceLimits
from cleandrop.security.external_paths import ascii_tool_input
from cleandrop.security.paths import (
    hash_path,
    next_output_path,
    sanitize_filename,
    sha256_file,
    validate_input_path,
)
from cleandrop.security.tempfiles import cleanup_worker_temporary_files


def test_filename_and_hash_helpers(tmp_path: Path) -> None:
    path = tmp_path / "data.bin"
    path.write_bytes(b"abc")
    assert sha256_file(path).startswith("ba7816bf")
    assert len(hash_path(path)) == 64
    assert sanitize_filename(' bad<>:"name?.jpg ') == "bad____name_.jpg"
    assert sanitize_filename("...") == "cleaned-output"


def test_unicode_input_gets_temporary_ascii_path_for_legacy_tools(tmp_path: Path) -> None:
    source = tmp_path / "نمونه محرمانه.png"
    source.write_bytes(b"private test bytes")

    with ascii_tool_input(source) as safe_path:
        assert safe_path != source
        assert str(safe_path).isascii()
        assert safe_path.read_bytes() == source.read_bytes()
        temporary_path = safe_path

    assert source.exists()
    assert not temporary_path.exists()


def test_validate_input_rejects_empty_and_large(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        validate_input_path(tmp_path / "missing.jpg", ResourceLimits())
    with pytest.raises(ValidationError):
        validate_input_path(tmp_path, ResourceLimits())
    empty = tmp_path / "empty.jpg"
    empty.write_bytes(b"")
    with pytest.raises(ValidationError):
        validate_input_path(empty, ResourceLimits())
    large = tmp_path / "large.jpg"
    large.write_bytes(b"12345")
    with pytest.raises(ValidationError):
        validate_input_path(large, ResourceLimits(max_file_size=4))


def test_output_never_overwrites_and_increments(tmp_path: Path) -> None:
    source = tmp_path / "photo.jpg"
    source.write_bytes(b"\xff\xd8\xff")
    with pytest.raises(UnsafePathError):
        next_output_path(source, source)
    first = next_output_path(source)
    assert first.name == "photo.cleaned.jpg"
    first.write_bytes(b"x")
    assert next_output_path(source).name == "photo.cleaned-2.jpg"
    requested = tmp_path / "shared.jpg"
    requested.write_bytes(b"old")
    assert next_output_path(source, requested).name == "shared-2.jpg"
    (tmp_path / "shared-2.jpg").write_bytes(b"old")
    assert next_output_path(source, requested).name == "shared-3.jpg"
    (tmp_path / "photo.cleaned-2.jpg").write_bytes(b"old")
    assert next_output_path(source).name == "photo.cleaned-3.jpg"


def test_symlink_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jpg"
    source.write_bytes(b"x")
    link = tmp_path / "link.jpg"
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == link)
    with pytest.raises(UnsafePathError):
        validate_input_path(link, ResourceLimits())


def test_worker_temp_cleanup_is_pid_scoped(tmp_path: Path) -> None:
    assert cleanup_worker_temporary_files([tmp_path], 0) == 0
    worker_dir = tmp_path / ".cleandrop-1234-job"
    worker_dir.mkdir()
    (worker_dir / "partial.bin").write_bytes(b"partial")
    report = tmp_path / ".cleandrop-report-1234-result.tmp"
    report.write_text("partial", encoding="utf-8")
    unrelated = tmp_path / ".cleandrop-9876-keep"
    unrelated.mkdir()
    ordinary = tmp_path / "keep.txt"
    ordinary.write_text("keep", encoding="utf-8")

    assert cleanup_worker_temporary_files([tmp_path], 1234) == 2
    assert not worker_dir.exists()
    assert not report.exists()
    assert unrelated.exists()
    assert ordinary.exists()


def test_worker_temp_cleanup_ignores_missing_and_symlinked_roots(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing"
    assert cleanup_worker_temporary_files([missing], 1234) == 0

    target = tmp_path / "target"
    target.mkdir()
    linked = tmp_path / "linked"
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == linked)
    assert cleanup_worker_temporary_files([linked], 1234) == 0
