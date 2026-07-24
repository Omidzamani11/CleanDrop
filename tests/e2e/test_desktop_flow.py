from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import pytest
from PySide6.QtCore import QEventLoop
from PySide6.QtWidgets import QApplication

from cleandrop.ui.main_window import MainWindow
from cleandrop.ui.styles import STYLESHEET


def _application() -> QApplication:
    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        return existing
    application = QApplication([])
    application.setStyle("Fusion")
    application.setStyleSheet(STYLESHEET)
    return application


def _wait_until(predicate: Callable[[], bool], timeout: float = 90) -> None:
    application = _application()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        application.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 100)
        if predicate():
            return
        time.sleep(0.02)
    raise TimeoutError("Desktop flow did not reach the expected state")


@pytest.mark.e2e
def test_desktop_inspect_review_sanitize_result(
    jpg_with_metadata: Path,
    tmp_path: Path,
) -> None:
    application = _application()
    window = MainWindow("en")
    window.show()
    window.drop_page.add_paths([str(jpg_with_metadata)])
    assert window.drop_page.inspect_button.isEnabled()
    window.drop_page.inspect_button.click()
    _wait_until(lambda: window.stack.currentWidget() is window.review_page)
    assert window.inspections
    assert window.review_page.file_combo.count() == 1

    output_dir = tmp_path / "cleaned"
    window.review_page.output_edit.setText(str(output_dir))
    window.review_page.clean.click()
    _wait_until(lambda: window.stack.currentWidget() is window.result_page)
    assert window.reports
    output_path = Path(str(window.reports[0]["_private_output_path"]))
    assert output_path.exists()
    assert output_path.with_suffix(f"{output_path.suffix}.cleandrop.json").exists()
    assert window.result_page.outputs.count() == 1
    window.close()
    application.processEvents()
