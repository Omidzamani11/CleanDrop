from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from cleandrop.adapters.filetypes import MagicByteSniffer
from cleandrop.adapters.ocr import parse_tsv
from cleandrop.adapters.report import JsonReportWriter, _json_default, to_json
from cleandrop.domain.errors import UnsupportedMediaError
from cleandrop.domain.models import MediaType
from cleandrop.worker.protocol import JsonLineEventSink, parse_request


@pytest.mark.parametrize(
    ("header", "media_type"),
    [
        (b"\xff\xd8\xff\x00", MediaType.JPEG),
        (b"\x89PNG\r\n\x1a\n", MediaType.PNG),
        (b"%PDF-1.7", MediaType.PDF),
    ],
)
def test_magic_bytes(tmp_path: Path, header: bytes, media_type: MediaType) -> None:
    path = tmp_path / "wrong.bin"
    path.write_bytes(header)
    assert MagicByteSniffer().detect(path) is media_type


def test_magic_bytes_reject_unknown(tmp_path: Path) -> None:
    path = tmp_path / "fake.jpg"
    path.write_bytes(b"not an image")
    with pytest.raises(UnsupportedMediaError):
        MagicByteSniffer().detect(path)


def test_tesseract_tsv_parser() -> None:
    data = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num"
        "\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t1\t1\t1\t1\t10\t20\t50\t15\t95.5\towner@example.com\n"
        "5\t1\t1\t1\t1\t2\t0\t0\t0\t0\t-1\t\n"
    )
    tokens = parse_tsv(data, page_index=2, page_width=200, page_height=100)
    assert len(tokens) == 1
    assert tokens[0].page_index == 2
    assert tokens[0].confidence == pytest.approx(0.955)
    assert tokens[0].rect.x == pytest.approx(0.05)


def test_atomic_json_report_and_unicode(tmp_path: Path) -> None:
    path = tmp_path / "گزارش.json"
    JsonReportWriter().write({"name": "آزمایش", "value": MediaType.PNG}, path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload == {"name": "آزمایش", "value": "image/png"}
    assert "آزمایش" in to_json(payload)


def test_worker_protocol_round_trip() -> None:
    import io

    stream = io.StringIO()
    sink = JsonLineEventSink(stream)
    sink.emit("progress", "job-1", {"progress": 50})
    event = json.loads(stream.getvalue())
    assert event["protocol_version"] == "1.0"
    assert event["payload"]["progress"] == 50
    request = parse_request(
        '{"protocol_version":"1.0","command":"inspect","payload":{"input_path":"x"}}'
    )
    assert request["command"] == "inspect"
    with pytest.raises(ValueError):
        parse_request('{"protocol_version":"2.0","command":"inspect"}')


def test_report_json_default_supports_dataclass_path_and_rejects_unknown() -> None:
    @dataclass
    class Payload:
        output: Path

    assert _json_default(Payload(Path("result.pdf"))) == {"output": Path("result.pdf")}
    assert _json_default(Path("result.pdf")) == "result.pdf"
    with pytest.raises(TypeError):
        _json_default(object())
