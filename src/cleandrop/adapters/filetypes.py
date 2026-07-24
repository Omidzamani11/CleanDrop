from __future__ import annotations

from pathlib import Path

from cleandrop.domain.errors import UnsupportedMediaError
from cleandrop.domain.models import MediaType

_SIGNATURES: tuple[tuple[bytes, MediaType], ...] = (
    (b"\xff\xd8\xff", MediaType.JPEG),
    (b"\x89PNG\r\n\x1a\n", MediaType.PNG),
    (b"%PDF-", MediaType.PDF),
)


class MagicByteSniffer:
    def detect(self, path: Path) -> MediaType:
        with path.open("rb") as handle:
            header = handle.read(16)
        for signature, media_type in _SIGNATURES:
            if header.startswith(signature):
                return media_type
        raise UnsupportedMediaError("Only JPEG, PNG, and unencrypted PDF files are supported")
