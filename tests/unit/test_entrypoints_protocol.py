from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

import cleandrop.__main__ as entrypoint
from cleandrop.domain.models import MediaType, ResourceLimits
from cleandrop.worker import protocol, worker_main


@pytest.mark.parametrize(
    ("argv", "target", "expected"),
    [
        (["cleandrop"], "gui_main", 11),
        (["cleandrop", "doctor"], "cli_main", 12),
        (["cleandrop", "--worker"], "worker_main", 13),
    ],
)
def test_entrypoint_routes_to_expected_surface(
    monkeypatch: pytest.MonkeyPatch,
    argv: list[str],
    target: str,
    expected: int,
) -> None:
    monkeypatch.setattr(sys, "argv", argv.copy())
    monkeypatch.setattr(entrypoint, target, lambda: expected)

    assert entrypoint.main() == expected
    if target == "worker_main":
        assert "--worker" not in sys.argv


def test_protocol_serializes_supported_values_and_rejects_unknown() -> None:
    assert protocol._default(Path("output.pdf")) == "output.pdf"
    assert protocol._default(MediaType.PDF) == "application/pdf"
    serialized_limits = protocol._default(ResourceLimits(max_pdf_pages=7))
    assert serialized_limits["max_pdf_pages"] == 7

    with pytest.raises(TypeError):
        protocol._default(object())

    sink = protocol.JsonLineEventSink(io.StringIO())
    with pytest.raises(ValueError, match="Unsupported worker event"):
        sink.emit("debug", "job", {})


@pytest.mark.parametrize(
    "request_json",
    [
        "[]",
        '{"protocol_version":"1.0","payload":{}}',
        '{"protocol_version":"1.0","command":"inspect","payload":[]}',
    ],
)
def test_protocol_rejects_invalid_request_shapes(request_json: str) -> None:
    with pytest.raises(ValueError):
        protocol.parse_request(request_json)


def test_worker_main_handles_empty_invalid_and_cleanup_requests(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output = io.StringIO()
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    monkeypatch.setattr(sys, "stdout", output)
    monkeypatch.setattr(sys, "stderr", io.StringIO())
    assert worker_main.main() == 10
    assert output.getvalue() == ""

    output = io.StringIO()
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"protocol_version":"0"}\n'))
    monkeypatch.setattr(sys, "stdout", output)
    assert worker_main.main() == 10
    event = json.loads(output.getvalue())
    assert event["payload"]["error_code"] == "INVALID_WORKER_REQUEST"

    output = io.StringIO()
    request = {
        "protocol_version": "1.0",
        "command": "cleanup",
        "job_id": "cleanup-test",
        "payload": {"directories": [str(tmp_path)], "worker_pid": 0},
    }
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(request) + "\n"))
    monkeypatch.setattr(sys, "stdout", output)
    assert worker_main.main() == 0
    event = json.loads(output.getvalue())
    assert event["event_type"] == "completed"
    assert event["payload"]["removed_temporary_paths"] == 0


def test_worker_handle_rejects_unsupported_command() -> None:
    output = io.StringIO()
    sink = protocol.JsonLineEventSink(output)
    code = worker_main.handle(
        {"command": "not-a-command", "payload": {}, "job_id": "bad"},
        sink,
    )
    assert code == 10
    event = json.loads(output.getvalue())
    assert event["payload"]["error_code"] == "INVALID_WORKER_REQUEST"
