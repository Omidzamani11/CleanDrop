from __future__ import annotations

import hashlib
import tempfile
import uuid
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QStackedWidget

from cleandrop.ui.i18n import error_text, text
from cleandrop.ui.pages import (
    DropPage,
    InspectionPage,
    ProgressPage,
    ResultPage,
    ReviewPage,
)
from cleandrop.ui.worker_client import WorkerClient


class MainWindow(QMainWindow):
    def __init__(self, language: str = "fa") -> None:
        super().__init__()
        self.language = language
        self.setMinimumSize(1100, 720)
        self.resize(1320, 850)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.drop_page = DropPage(language)
        self.inspection_page = InspectionPage(language)
        self.review_page = ReviewPage(language)
        self.progress_page = ProgressPage(language)
        self.result_page = ResultPage(language)
        for page in (
            self.drop_page,
            self.inspection_page,
            self.review_page,
            self.progress_page,
            self.result_page,
        ):
            self.stack.addWidget(page)

        self.worker = WorkerClient(self)
        self.worker.event_received.connect(self._worker_event)
        self.worker.failed.connect(self._worker_failed)
        self.worker.finished.connect(self._worker_finished)
        self.preview_worker: WorkerClient | None = None
        self.preview_temp = tempfile.TemporaryDirectory(prefix="cleandrop-preview-")
        self.mode = ""
        self.cancelled = False
        self.errors: list[str] = []
        self.paths: list[str] = []
        self.valid_paths: list[str] = []
        self.inspections: list[dict[str, Any]] = []
        self.inspect_index = 0
        self.current_inspection: dict[str, Any] | None = None
        self.finding_count = 0
        self.sanitize_jobs: list[dict[str, Any]] = []
        self.sanitize_index = 0
        self.current_report: dict[str, Any] | None = None
        self.reports: list[dict[str, Any]] = []
        self.output_dir = ""
        self.cancelled_worker_pid = 0

        self.drop_page.inspect_requested.connect(self._start_inspections)
        self.drop_page.language_changed.connect(self.set_language)
        self.inspection_page.cancel_requested.connect(self._cancel)
        self.review_page.preview_requested.connect(self._request_preview)
        self.review_page.clean_requested.connect(self._start_sanitization)
        self.review_page.back_requested.connect(lambda: self.stack.setCurrentWidget(self.drop_page))
        self.progress_page.cancel_requested.connect(self._cancel)
        self.result_page.new_job_requested.connect(self._new_job)
        self.result_page.open_folder_requested.connect(self._open_output_folder)
        self.set_language(language)
        self.stack.setCurrentWidget(self.drop_page)

    def set_language(self, language: str) -> None:
        self.language = language if language in {"fa", "en"} else "en"
        direction = (
            Qt.LayoutDirection.RightToLeft
            if self.language == "fa"
            else Qt.LayoutDirection.LeftToRight
        )
        application = QApplication.instance()
        if isinstance(application, QApplication):
            application.setLayoutDirection(direction)
        self.setWindowTitle(text(self.language, "window_title"))
        for page in (
            self.drop_page,
            self.inspection_page,
            self.review_page,
            self.progress_page,
            self.result_page,
        ):
            page.retranslate(self.language)

    def _start_inspections(self, paths: list[str]) -> None:
        if not paths:
            return
        self.paths = list(paths)
        self.valid_paths = []
        self.inspections = []
        self.inspect_index = 0
        self.errors = []
        self.cancelled = False
        self.mode = "inspect"
        self.stack.setCurrentWidget(self.inspection_page)
        self._inspect_next()

    def _inspect_next(self) -> None:
        if self.cancelled:
            return
        if self.inspect_index >= len(self.paths):
            if not self.inspections:
                errors = self.errors or ["NO_VALID_FILES"]
                self._show_error("\n".join(error_text(self.language, code) for code in errors))
                self.stack.setCurrentWidget(self.drop_page)
                return
            self.review_page.set_data(self.valid_paths, self.inspections)
            self.stack.setCurrentWidget(self.review_page)
            if self.errors:
                self.statusBar().showMessage(
                    " • ".join(error_text(self.language, code) for code in self.errors),
                    10000,
                )
            return
        path = self.paths[self.inspect_index]
        self.current_inspection = None
        self.finding_count = 0
        self.inspection_page.set_status(Path(path).name, 5, 0)
        try:
            self.worker.start("inspect", {"input_path": path, "run_ocr": True})
        except RuntimeError:
            self.errors.append("WORKER_START_FAILED")
            self.inspect_index += 1
            self._inspect_next()

    def _start_sanitization(self, config: dict[str, Any]) -> None:
        jobs = config.get("jobs", [])
        if not isinstance(jobs, list) or not jobs:
            return
        self.sanitize_jobs = [job for job in jobs if isinstance(job, dict)]
        self.output_dir = str(config.get("output_dir", ""))
        self.sanitize_index = 0
        self.current_report = None
        self.reports = []
        self.errors = []
        self.cancelled = False
        self.mode = "sanitize"
        self.stack.setCurrentWidget(self.progress_page)
        self._sanitize_next()

    def _sanitize_next(self) -> None:
        if self.cancelled:
            return
        if self.sanitize_index >= len(self.sanitize_jobs):
            if not self.reports:
                errors = self.errors or ["NO_OUTPUT_CREATED"]
                self._show_error("\n".join(error_text(self.language, code) for code in errors))
                self.stack.setCurrentWidget(self.review_page)
                return
            self.result_page.set_reports(self.reports)
            self.stack.setCurrentWidget(self.result_page)
            if self.errors:
                self.statusBar().showMessage(
                    " • ".join(error_text(self.language, code) for code in self.errors),
                    12000,
                )
            return
        job = self.sanitize_jobs[self.sanitize_index]
        self.current_report = None
        name = Path(str(job.get("input_path", ""))).name
        self.progress_page.set_status(name, "validating", 2)
        try:
            self.worker.start("sanitize", job)
        except RuntimeError:
            self.errors.append("WORKER_START_FAILED")
            self.sanitize_index += 1
            self._sanitize_next()

    def _worker_event(self, event: dict[str, Any]) -> None:
        event_type = str(event.get("event_type", ""))
        payload = event.get("payload", {})
        if not isinstance(payload, dict):
            return
        if event_type == "error":
            code = str(payload.get("error_code", "WORKER_ERROR"))
            self.errors.append(code)
            return
        if self.mode == "inspect":
            if event_type == "finding":
                self.finding_count += 1
            if event_type in {"progress", "stage_started"}:
                progress = int(payload.get("progress", 20))
                path = self.paths[self.inspect_index]
                self.inspection_page.set_status(
                    Path(path).name,
                    progress,
                    self.finding_count,
                )
            if event_type == "completed" and isinstance(payload.get("inspection"), dict):
                self.current_inspection = payload["inspection"]
                self.inspection_page.set_status(
                    Path(self.paths[self.inspect_index]).name,
                    100,
                    self.finding_count,
                )
        elif self.mode == "sanitize":
            job = self.sanitize_jobs[self.sanitize_index]
            name = Path(str(job.get("input_path", ""))).name
            if event_type == "stage_started":
                self.progress_page.set_status(
                    name,
                    str(payload.get("stage", "sanitizing")),
                    int(payload.get("progress", 50)),
                )
            elif event_type == "progress":
                self.progress_page.set_status(
                    name,
                    "sanitizing",
                    int(payload.get("progress", 50)),
                )
            elif event_type == "completed" and isinstance(payload.get("report"), dict):
                report = dict(payload["report"])
                private_output_path = payload.get("private_output_path")
                if payload.get("private_review") is True and private_output_path:
                    report["_private_output_path"] = str(private_output_path)
                self.current_report = report
                self.progress_page.set_status(name, "verifying", 100)

    def _worker_failed(self, code: str) -> None:
        self.errors.append(code)

    def _worker_finished(self, _exit_code: int) -> None:
        if self.cancelled:
            if self.mode == "sanitize" and self.cancelled_worker_pid > 0:
                directories = sorted(
                    {
                        str(Path(str(job.get("output_path", ""))).parent)
                        for job in self.sanitize_jobs
                    }
                )
                self.mode = "cleanup"
                try:
                    self.worker.start(
                        "cleanup",
                        {
                            "directories": directories,
                            "worker_pid": self.cancelled_worker_pid,
                        },
                    )
                    return
                except RuntimeError:
                    pass
            self.stack.setCurrentWidget(self.drop_page)
            QMessageBox.information(
                self,
                text(self.language, "cancel"),
                text(self.language, "cancelled_message"),
            )
            return
        if self.mode == "inspect":
            if self.current_inspection is not None:
                self.valid_paths.append(self.paths[self.inspect_index])
                self.inspections.append(self.current_inspection)
            self.inspect_index += 1
            self._inspect_next()
        elif self.mode == "sanitize":
            if self.current_report is not None:
                self.reports.append(self.current_report)
            self.sanitize_index += 1
            self._sanitize_next()

    def _request_preview(self, source: str, page_index: int) -> None:
        if self.preview_worker is not None and self.preview_worker.running:
            self.preview_worker.cancel()
        worker = WorkerClient(self)
        self.preview_worker = worker
        digest = hashlib.sha256(source.encode("utf-8", errors="replace")).hexdigest()[:12]
        output = Path(self.preview_temp.name) / (
            f"{digest}-{page_index}-{uuid.uuid4().hex[:8]}.png"
        )

        def on_event(event: dict[str, Any]) -> None:
            payload = event.get("payload", {})
            if (
                event.get("event_type") == "completed"
                and isinstance(payload, dict)
                and payload.get("preview_path")
            ):
                self.review_page.set_preview(
                    str(payload["preview_path"]),
                    int(payload.get("page_index", 0)),
                )

        worker.event_received.connect(on_event)

        def preview_finished(_code: int) -> None:
            if self.preview_worker is worker:
                self.preview_worker = None
            worker.deleteLater()

        worker.finished.connect(preview_finished)
        try:
            worker.start(
                "preview",
                {
                    "input_path": source,
                    "page_index": page_index,
                    "output_path": str(output),
                },
            )
        except RuntimeError:
            worker.deleteLater()

    def _cancel(self) -> None:
        self.cancelled = True
        if self.worker.running:
            self.cancelled_worker_pid = self.worker.last_pid
            self.worker.cancel()
        else:
            self.stack.setCurrentWidget(self.drop_page)

    def _new_job(self) -> None:
        self.drop_page.clear()
        self.stack.setCurrentWidget(self.drop_page)

    def _open_output_folder(self) -> None:
        if self.output_dir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.output_dir))

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(
            self,
            text(self.language, "error_title"),
            message,
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.worker.running:
            self.worker.cancel()
        if self.preview_worker is not None:
            try:
                if self.preview_worker.running:
                    self.preview_worker.cancel()
            except RuntimeError:
                self.preview_worker = None
        self.preview_temp.cleanup()
        event.accept()
