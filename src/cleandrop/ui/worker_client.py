from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QProcess, QTimer, Signal, Slot


class WorkerClient(QObject):
    event_received = Signal(dict)
    finished = Signal(int)
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self.process.readyReadStandardOutput.connect(self._read_stdout)
        self.process.readyReadStandardError.connect(self._read_stderr)
        self.process.finished.connect(self._process_finished)
        self._buffer = ""
        self._stderr_seen = False
        self.last_pid = 0

    @property
    def running(self) -> bool:
        return self.process.state() is not QProcess.ProcessState.NotRunning

    def start(self, command: str, payload: dict[str, Any]) -> str:
        if self.running:
            raise RuntimeError("Worker is already running")
        job_id = str(uuid.uuid4())
        request = {
            "protocol_version": "1.0",
            "command": command,
            "job_id": job_id,
            "payload": payload,
        }
        program = sys.executable
        arguments = (
            ["--worker"]
            if getattr(sys, "frozen", False)
            else [
                "-m",
                "cleandrop.worker.worker_main",
            ]
        )
        self._buffer = ""
        self._stderr_seen = False
        self.process.setWorkingDirectory(str(Path.cwd()))
        self.process.start(program, arguments)
        if not self.process.waitForStarted(5000):
            raise RuntimeError("The local worker could not start")
        self.last_pid = int(self.process.processId())
        self.process.write((json.dumps(request, ensure_ascii=False) + "\n").encode("utf-8"))
        self.process.closeWriteChannel()
        return job_id

    def cancel(self) -> None:
        if not self.running:
            return
        self.process.terminate()
        QTimer.singleShot(2000, self._force_kill_if_running)

    @Slot()
    def _force_kill_if_running(self) -> None:
        if self.running:
            self.process.kill()

    @Slot()
    def _read_stdout(self) -> None:
        raw = self.process.readAllStandardOutput().data()
        self._buffer += bytes(raw).decode("utf-8", errors="replace")
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                self.failed.emit("INVALID_WORKER_RESPONSE")
                continue
            if isinstance(event, dict):
                self.event_received.emit(event)

    @Slot()
    def _read_stderr(self) -> None:
        # Never surface raw stderr: external tools may echo sensitive file content.
        self.process.readAllStandardError()
        self._stderr_seen = True

    @Slot(int, QProcess.ExitStatus)
    def _process_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        self._read_stdout()
        if self._stderr_seen and exit_code != 0:
            self.failed.emit("WORKER_PROCESS_FAILED")
        self.finished.emit(exit_code)
