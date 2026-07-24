from __future__ import annotations

import json
import threading
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

from cleandrop.application.ports import WorkerEventSink

PROTOCOL_VERSION = "1.0"
ALLOWED_EVENTS = frozenset(
    {
        "job_started",
        "stage_started",
        "progress",
        "finding",
        "warning",
        "error",
        "cancelled",
        "completed",
    }
)


class JsonLineEventSink(WorkerEventSink):
    def __init__(self, stream: TextIO) -> None:
        self.stream = stream
        self._lock = threading.Lock()

    def emit(self, event_type: str, job_id: str, payload: dict[str, Any]) -> None:
        if event_type not in ALLOWED_EVENTS:
            raise ValueError(f"Unsupported worker event: {event_type}")
        event = {
            "protocol_version": PROTOCOL_VERSION,
            "event_type": event_type,
            "job_id": job_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": payload,
        }
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":"), default=_default)
        with self._lock:
            self.stream.write(line + "\n")
            self.stream.flush()


def _default(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def parse_request(line: str) -> dict[str, Any]:
    request = json.loads(line)
    if not isinstance(request, dict):
        raise ValueError("Worker request must be a JSON object")
    if request.get("protocol_version") != PROTOCOL_VERSION:
        raise ValueError("Unsupported worker protocol version")
    if not isinstance(request.get("command"), str):
        raise ValueError("Worker request command is required")
    if not isinstance(request.get("payload", {}), dict):
        raise ValueError("Worker request payload must be an object")
    return request
