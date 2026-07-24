from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from cleandrop.ui.canvas import RedactionCanvas
from cleandrop.ui.i18n import text


def _header(title: QLabel, description: QLabel) -> QVBoxLayout:
    layout = QVBoxLayout()
    title.setObjectName("pageTitle")
    description.setObjectName("pageDescription")
    description.setWordWrap(True)
    layout.addWidget(title)
    layout.addWidget(description)
    return layout


class FileDropList(QListWidget):
    files_dropped = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setObjectName("dropList")

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        mime: QMimeData = event.mimeData()
        paths = [
            url.toLocalFile()
            for url in mime.urls()
            if url.isLocalFile() and Path(url.toLocalFile()).is_file()
        ]
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()


class DropPage(QWidget):
    inspect_requested = Signal(list)
    language_changed = Signal(str)

    def __init__(self, language: str) -> None:
        super().__init__()
        self.language = language
        self.paths: list[str] = []
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 36, 48, 40)
        root.setSpacing(22)

        top = QHBoxLayout()
        brand = QLabel("CleanDrop")
        brand.setObjectName("brand")
        top.addWidget(brand)
        top.addStretch()
        self.privacy = QLabel()
        self.privacy.setObjectName("privacyBadge")
        top.addWidget(self.privacy)
        self.language_combo = QComboBox()
        self.language_combo.addItem("فارسی", "fa")
        self.language_combo.addItem("English", "en")
        self.language_combo.setCurrentIndex(0 if language == "fa" else 1)
        self.language_combo.currentIndexChanged.connect(self._language_selected)
        top.addWidget(self.language_combo)
        root.addLayout(top)

        hero = QVBoxLayout()
        self.title = QLabel()
        self.title.setObjectName("heroTitle")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("heroSubtitle")
        self.subtitle.setWordWrap(True)
        hero.addWidget(self.title)
        hero.addWidget(self.subtitle)
        root.addLayout(hero)

        panel = QFrame()
        panel.setObjectName("dropPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(28, 28, 28, 28)
        panel_layout.setSpacing(14)
        self.drop_title = QLabel()
        self.drop_title.setObjectName("dropTitle")
        self.drop_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_subtitle = QLabel()
        self.drop_subtitle.setObjectName("muted")
        self.drop_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_list = FileDropList()
        self.file_list.files_dropped.connect(self.add_paths)
        self.file_list.itemSelectionChanged.connect(self._update_actions)
        panel_layout.addWidget(self.drop_title)
        panel_layout.addWidget(self.drop_subtitle)
        panel_layout.addWidget(self.file_list, 1)
        actions = QHBoxLayout()
        self.choose_button = QPushButton()
        self.choose_button.setObjectName("secondaryButton")
        self.choose_button.clicked.connect(self._choose_files)
        self.remove_button = QPushButton()
        self.remove_button.setObjectName("ghostButton")
        self.remove_button.clicked.connect(self._remove_selected)
        self.clear_button = QPushButton()
        self.clear_button.setObjectName("ghostButton")
        self.clear_button.clicked.connect(self.clear)
        actions.addWidget(self.choose_button)
        actions.addWidget(self.remove_button)
        actions.addWidget(self.clear_button)
        actions.addStretch()
        panel_layout.addLayout(actions)
        root.addWidget(panel, 1)

        bottom = QHBoxLayout()
        self.status = QLabel()
        self.status.setObjectName("muted")
        bottom.addWidget(self.status)
        bottom.addStretch()
        self.inspect_button = QPushButton()
        self.inspect_button.setObjectName("primaryButton")
        self.inspect_button.clicked.connect(lambda: self.inspect_requested.emit(self.paths))
        bottom.addWidget(self.inspect_button)
        root.addLayout(bottom)
        self.retranslate(language)
        self._update_actions()

    def add_paths(self, candidates: list[str]) -> None:
        for candidate in candidates:
            path = str(Path(candidate).expanduser().absolute())
            if path in self.paths:
                continue
            if len(self.paths) >= 100:
                break
            self.paths.append(path)
            size = Path(path).stat().st_size if Path(path).exists() else 0
            suffix = Path(path).suffix.upper().lstrip(".")
            item = QListWidgetItem(f"{Path(path).name}\n{suffix}  •  {self._human_size(size)}")
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.file_list.addItem(item)
        self._update_actions()

    def clear(self) -> None:
        self.paths.clear()
        self.file_list.clear()
        self._update_actions()

    def retranslate(self, language: str) -> None:
        self.language = language
        self.privacy.setText(text(language, "privacy_badge"))
        self.title.setText(text(language, "tagline"))
        self.subtitle.setText(text(language, "drop_subtitle"))
        self.drop_title.setText(text(language, "drop_title"))
        self.drop_subtitle.setText(text(language, "drop_subtitle"))
        self.choose_button.setText(text(language, "choose_files"))
        self.remove_button.setText(text(language, "remove"))
        self.clear_button.setText(text(language, "clear"))
        self.inspect_button.setText(text(language, "start_inspection"))
        self._update_actions()

    def _choose_files(self) -> None:
        paths, _filter = QFileDialog.getOpenFileNames(
            self,
            text(self.language, "choose_files"),
            "",
            text(self.language, "file_filter"),
        )
        self.add_paths(paths)

    def _remove_selected(self) -> None:
        selected = {
            str(item.data(Qt.ItemDataRole.UserRole)) for item in self.file_list.selectedItems()
        }
        self.paths = [path for path in self.paths if path not in selected]
        for row in range(self.file_list.count() - 1, -1, -1):
            item = self.file_list.item(row)
            if item is not None and str(item.data(Qt.ItemDataRole.UserRole)) in selected:
                self.file_list.takeItem(row)
        self._update_actions()

    def _update_actions(self) -> None:
        count = len(self.paths)
        self.status.setText(
            text(self.language, "ready_files", count=count)
            if count
            else text(self.language, "no_files")
        )
        self.inspect_button.setEnabled(count > 0)
        self.remove_button.setEnabled(bool(self.file_list.selectedItems()))
        self.clear_button.setEnabled(count > 0)

    def _language_selected(self) -> None:
        language = str(self.language_combo.currentData())
        if language != self.language:
            self.language_changed.emit(language)

    @staticmethod
    def _human_size(size: int) -> str:
        value = float(size)
        for unit in ("B", "KB", "MB", "GB"):
            if value < 1024 or unit == "GB":
                return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
            value /= 1024
        return f"{size} B"


class InspectionPage(QWidget):
    cancel_requested = Signal()

    def __init__(self, language: str) -> None:
        super().__init__()
        self.language = language
        root = QVBoxLayout(self)
        root.setContentsMargins(64, 56, 64, 56)
        root.setSpacing(28)
        self.title = QLabel()
        self.description = QLabel()
        root.addLayout(_header(self.title, self.description))
        root.addStretch()
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(18)
        self.file_name = QLabel()
        self.file_name.setObjectName("fileName")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.findings = QLabel()
        self.findings.setObjectName("muted")
        card_layout.addWidget(self.file_name)
        card_layout.addWidget(self.progress)
        card_layout.addWidget(self.findings)
        root.addWidget(card)
        root.addStretch()
        self.cancel = QPushButton()
        self.cancel.setObjectName("ghostButton")
        self.cancel.clicked.connect(self.cancel_requested)
        root.addWidget(self.cancel, alignment=Qt.AlignmentFlag.AlignRight)
        self.retranslate(language)

    def set_status(self, file_name: str, progress: int, findings: int) -> None:
        self.file_name.setText(file_name)
        self.progress.setValue(progress)
        self.findings.setText(text(self.language, "findings_count", count=findings))

    def retranslate(self, language: str) -> None:
        self.language = language
        self.title.setText(text(language, "inspect_title"))
        self.description.setText(text(language, "inspect_desc"))
        self.cancel.setText(text(language, "cancel"))
        self.findings.setText(text(language, "findings_count", count=0))


class ReviewPage(QWidget):
    preview_requested = Signal(str, int)
    clean_requested = Signal(dict)
    back_requested = Signal()

    def __init__(self, language: str) -> None:
        super().__init__()
        self.language = language
        self.paths: list[str] = []
        self.inspections: list[dict[str, Any]] = []
        self.checked: dict[str, set[str]] = {}
        self.manual: dict[str, dict[int, list[dict[str, float]]]] = {}
        self.pages: dict[str, int] = {}
        self._current_index = -1
        root = QVBoxLayout(self)
        root.setContentsMargins(34, 26, 34, 30)
        root.setSpacing(16)
        header_row = QHBoxLayout()
        header_labels = QVBoxLayout()
        self.title = QLabel()
        self.description = QLabel()
        header_labels.addLayout(_header(self.title, self.description))
        header_row.addLayout(header_labels, 1)
        self.file_combo = QComboBox()
        self.file_combo.setMinimumWidth(300)
        self.file_combo.currentIndexChanged.connect(self._switch_file)
        header_row.addWidget(self.file_combo)
        root.addLayout(header_row)
        self.capability_warning = QLabel()
        self.capability_warning.setObjectName("warningBadge")
        self.capability_warning.setWordWrap(True)
        self.capability_warning.setVisible(False)
        root.addWidget(self.capability_warning)

        content = QHBoxLayout()
        content.setSpacing(16)
        left = QFrame()
        left.setObjectName("card")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(18, 18, 18, 18)
        self.finding_list = QListWidget()
        self.finding_list.setMinimumWidth(320)
        self.finding_list.itemChanged.connect(self._finding_changed)
        left_layout.addWidget(self.finding_list, 1)
        self.no_findings = QLabel()
        self.no_findings.setObjectName("muted")
        self.no_findings.setWordWrap(True)
        left_layout.addWidget(self.no_findings)
        content.addWidget(left, 0)

        preview_card = QFrame()
        preview_card.setObjectName("card")
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(12, 12, 12, 12)
        self.preview_status = QLabel()
        self.preview_status.setObjectName("muted")
        preview_layout.addWidget(self.preview_status)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.canvas = RedactionCanvas()
        self.canvas.rectangle_added.connect(self._manual_added)
        scroll.setWidget(self.canvas)
        preview_layout.addWidget(scroll, 1)
        nav = QHBoxLayout()
        self.previous = QPushButton()
        self.previous.setObjectName("ghostButton")
        self.previous.clicked.connect(lambda: self._change_page(-1))
        self.page_label = QLabel()
        self.next = QPushButton()
        self.next.setObjectName("ghostButton")
        self.next.clicked.connect(lambda: self._change_page(1))
        self.zoom_out = QPushButton()
        self.zoom_out.setObjectName("ghostButton")
        self.zoom_out.clicked.connect(self.canvas.zoom_out)
        self.zoom_in = QPushButton()
        self.zoom_in.setObjectName("ghostButton")
        self.zoom_in.clicked.connect(self.canvas.zoom_in)
        self.undo = QPushButton()
        self.undo.setObjectName("ghostButton")
        self.undo.clicked.connect(self._undo_manual)
        nav.addWidget(self.previous)
        nav.addWidget(self.page_label)
        nav.addWidget(self.next)
        nav.addStretch()
        nav.addWidget(self.undo)
        nav.addWidget(self.zoom_out)
        nav.addWidget(self.zoom_in)
        preview_layout.addLayout(nav)
        content.addWidget(preview_card, 1)
        root.addLayout(content, 1)

        options = QFrame()
        options.setObjectName("card")
        grid = QGridLayout(options)
        grid.setContentsMargins(18, 14, 18, 14)
        self.output_label = QLabel()
        self.output_edit = QLineEdit()
        self.browse = QPushButton()
        self.browse.setObjectName("secondaryButton")
        self.browse.clicked.connect(self._browse_output)
        self.dpi_label = QLabel()
        self.dpi_combo = QComboBox()
        self.dpi_combo.addItems(["150 DPI", "200 DPI", "300 DPI"])
        self.dpi_combo.setCurrentIndex(1)
        grid.addWidget(self.output_label, 0, 0)
        grid.addWidget(self.output_edit, 0, 1)
        grid.addWidget(self.browse, 0, 2)
        grid.addWidget(self.dpi_label, 0, 3)
        grid.addWidget(self.dpi_combo, 0, 4)
        root.addWidget(options)

        footer = QHBoxLayout()
        self.back = QPushButton()
        self.back.setObjectName("ghostButton")
        self.back.clicked.connect(self.back_requested)
        self.clean = QPushButton()
        self.clean.setObjectName("primaryButton")
        self.clean.clicked.connect(self._emit_clean)
        footer.addWidget(self.back)
        footer.addStretch()
        footer.addWidget(self.clean)
        root.addLayout(footer)
        self.retranslate(language)

    def set_data(
        self,
        paths: list[str],
        inspections: list[dict[str, Any]],
    ) -> None:
        self._current_index = -1
        self.finding_list.clear()
        self.paths = paths
        self.inspections = inspections
        self.checked = {}
        self.manual = {}
        self.pages = {}
        self.file_combo.blockSignals(True)
        self.file_combo.clear()
        for path, inspection in zip(paths, inspections, strict=True):
            self.file_combo.addItem(Path(path).name)
            self.checked[path] = {
                str(finding["id"])
                for finding in inspection.get("findings", [])
                if finding.get("rect")
            }
            self.manual[path] = {}
            self.pages[path] = 0
        self.file_combo.blockSignals(False)
        limited = any(
            not bool(value)
            for inspection in inspections
            for value in inspection.get("capabilities", {}).values()
        )
        warning_messages = [
            str(message)
            for inspection in inspections
            for message in inspection.get("warnings", [])
            if message
        ]
        self.capability_warning.setText(
            text(self.language, "capability_limited")
            + (f"\n{' • '.join(warning_messages)}" if warning_messages else "")
        )
        self.capability_warning.setVisible(limited or bool(warning_messages))
        if paths:
            self.output_edit.setText(str(Path(paths[0]).parent))
            self.file_combo.setCurrentIndex(0)
            self._switch_file(0)

    def set_preview(self, path: str, page_index: int) -> None:
        if self._current_index < 0:
            return
        current_path = self.paths[self._current_index]
        if self.pages[current_path] != page_index:
            return
        self.canvas.set_image(path)
        self.preview_status.setText(text(self.language, "manual_hint"))
        self._refresh_overlays()

    def retranslate(self, language: str) -> None:
        self.language = language
        self.title.setText(text(language, "review_title"))
        self.description.setText(text(language, "review_desc"))
        self.capability_warning.setText(text(language, "capability_limited"))
        self.no_findings.setText(text(language, "no_findings"))
        self.previous.setText(text(language, "previous"))
        self.next.setText(text(language, "next"))
        self.zoom_in.setText(text(language, "zoom_in"))
        self.zoom_out.setText(text(language, "zoom_out"))
        self.undo.setText(text(language, "undo_manual"))
        self.output_label.setText(text(language, "output_folder"))
        self.browse.setText(text(language, "browse"))
        self.dpi_label.setText(text(language, "dpi"))
        self.clean.setText(text(language, "clean_files"))
        self.back.setText(text(language, "back"))
        self.preview_status.setText(text(language, "preview_wait"))
        if self._current_index >= 0:
            self._load_findings()
            self._update_page_controls()

    def _switch_file(self, index: int) -> None:
        if index < 0 or index >= len(self.paths):
            return
        self._save_checks()
        self._current_index = index
        self._load_findings()
        self._update_page_controls()
        self._request_preview()

    def _load_findings(self) -> None:
        if self._current_index < 0:
            return
        path = self.paths[self._current_index]
        findings = self.inspections[self._current_index].get("findings", [])
        self.finding_list.blockSignals(True)
        self.finding_list.clear()
        for finding in findings:
            kind = str(finding.get("kind", "finding")).replace("_", " ").title()
            preview = str(finding.get("masked_preview", ""))
            confidence = round(float(finding.get("confidence", 0)) * 100)
            suffix = text(self.language, "confidence", value=confidence)
            item = QListWidgetItem(f"{kind}\n{preview}  •  {suffix}")
            item.setData(Qt.ItemDataRole.UserRole, finding)
            if finding.get("rect"):
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(
                    Qt.CheckState.Checked
                    if str(finding["id"]) in self.checked[path]
                    else Qt.CheckState.Unchecked
                )
            else:
                item.setText(f"{kind}\n{preview}  •  {text(self.language, 'always_removed')}")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.finding_list.addItem(item)
        self.finding_list.blockSignals(False)
        self.no_findings.setVisible(not findings)
        self._refresh_overlays()

    def _save_checks(self) -> None:
        if self._current_index < 0 or self._current_index >= len(self.paths):
            return
        path = self.paths[self._current_index]
        selected: set[str] = set()
        for row in range(self.finding_list.count()):
            item = self.finding_list.item(row)
            if item is None or item.checkState() is not Qt.CheckState.Checked:
                continue
            finding = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(finding, dict) and finding.get("rect"):
                selected.add(str(finding["id"]))
        self.checked[path] = selected

    def _finding_changed(self, _item: QListWidgetItem) -> None:
        self._save_checks()
        self._refresh_overlays()

    def _current_page(self) -> int:
        if self._current_index < 0:
            return 0
        return self.pages[self.paths[self._current_index]]

    def _page_count(self) -> int:
        if self._current_index < 0:
            return 1
        return max(1, int(self.inspections[self._current_index].get("page_count", 1)))

    def _change_page(self, delta: int) -> None:
        if self._current_index < 0:
            return
        path = self.paths[self._current_index]
        target = max(0, min(self._page_count() - 1, self.pages[path] + delta))
        if target != self.pages[path]:
            self.pages[path] = target
            self._update_page_controls()
            self._request_preview()
            self._refresh_overlays()

    def _update_page_controls(self) -> None:
        page = self._current_page()
        count = self._page_count()
        self.page_label.setText(text(self.language, "page", current=page + 1, total=count))
        self.previous.setEnabled(page > 0)
        self.next.setEnabled(page + 1 < count)

    def _request_preview(self) -> None:
        if self._current_index < 0:
            return
        self.preview_status.setText(text(self.language, "preview_wait"))
        self.preview_requested.emit(
            self.paths[self._current_index],
            self._current_page(),
        )

    def _refresh_overlays(self) -> None:
        if self._current_index < 0:
            return
        path = self.paths[self._current_index]
        page = self._current_page()
        automatic = [
            finding["rect"]
            for finding in self.inspections[self._current_index].get("findings", [])
            if finding.get("rect")
            and str(finding["id"]) in self.checked[path]
            and int(finding.get("page_index") or 0) == page
        ]
        manual = self.manual[path].get(page, [])
        self.canvas.set_overlays(automatic, manual)

    def _manual_added(self, rect: dict[str, float]) -> None:
        if self._current_index < 0:
            return
        path = self.paths[self._current_index]
        page = self._current_page()
        self.manual[path].setdefault(page, []).append(rect)
        self._refresh_overlays()

    def _undo_manual(self) -> None:
        if self._current_index < 0:
            return
        path = self.paths[self._current_index]
        regions = self.manual[path].get(self._current_page(), [])
        if regions:
            regions.pop()
            self._refresh_overlays()

    def _browse_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            text(self.language, "output_folder"),
            self.output_edit.text(),
        )
        if folder:
            self.output_edit.setText(folder)

    def _emit_clean(self) -> None:
        self._save_checks()
        output_text = self.output_edit.text().strip()
        if not output_text:
            QMessageBox.warning(
                self,
                text(self.language, "error_title"),
                text(self.language, "invalid_output"),
            )
            return
        output_dir = Path(output_text).expanduser()
        dpi = int(self.dpi_combo.currentText().split()[0])
        jobs: list[dict[str, Any]] = []
        for path, inspection in zip(self.paths, self.inspections, strict=True):
            regions: list[dict[str, Any]] = []
            for finding in inspection.get("findings", []):
                if finding.get("rect") and str(finding["id"]) in self.checked[path]:
                    regions.append(
                        {
                            "page_index": int(finding.get("page_index") or 0),
                            "rect": finding["rect"],
                            "source_finding_id": str(finding["id"]),
                            "reason": str(finding.get("kind", "detected")),
                        }
                    )
            for page, rectangles in self.manual[path].items():
                for rect in rectangles:
                    regions.append(
                        {
                            "page_index": page,
                            "rect": rect,
                            "source_finding_id": None,
                            "reason": "manual",
                        }
                    )
            source = Path(path)
            jobs.append(
                {
                    "input_path": path,
                    "output_path": str(
                        output_dir / f"{source.stem}.cleaned{source.suffix.lower()}"
                    ),
                    "selected_finding_ids": [],
                    "manual_redactions": regions,
                    "dpi": dpi,
                    # Findings were already reviewed. Re-running OCR would be slow and
                    # would generate new finding identifiers; verification still runs.
                    "run_ocr": False,
                }
            )
        self.clean_requested.emit({"output_dir": str(output_dir), "jobs": jobs})


class ProgressPage(QWidget):
    cancel_requested = Signal()

    def __init__(self, language: str) -> None:
        super().__init__()
        self.language = language
        root = QVBoxLayout(self)
        root.setContentsMargins(64, 56, 64, 56)
        root.setSpacing(28)
        self.title = QLabel()
        self.description = QLabel()
        root.addLayout(_header(self.title, self.description))
        root.addStretch()
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)
        self.file_name = QLabel()
        self.file_name.setObjectName("fileName")
        self.stage = QLabel()
        self.stage.setObjectName("muted")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.file_name)
        layout.addWidget(self.stage)
        layout.addWidget(self.progress)
        root.addWidget(card)
        root.addStretch()
        self.cancel = QPushButton()
        self.cancel.setObjectName("ghostButton")
        self.cancel.clicked.connect(self.cancel_requested)
        root.addWidget(self.cancel, alignment=Qt.AlignmentFlag.AlignRight)
        self.retranslate(language)

    def set_status(self, file_name: str, stage: str, progress: int) -> None:
        self.file_name.setText(file_name)
        self.stage.setText(text(self.language, f"stage_{stage}"))
        self.progress.setValue(progress)

    def retranslate(self, language: str) -> None:
        self.language = language
        self.title.setText(text(language, "progress_title"))
        self.description.setText(text(language, "progress_desc"))
        self.cancel.setText(text(language, "cancel"))


class ResultPage(QWidget):
    open_folder_requested = Signal()
    new_job_requested = Signal()

    def __init__(self, language: str) -> None:
        super().__init__()
        self.language = language
        root = QVBoxLayout(self)
        root.setContentsMargins(52, 40, 52, 40)
        root.setSpacing(18)
        self.title = QLabel()
        self.description = QLabel()
        root.addLayout(_header(self.title, self.description))
        self.report_note = QLabel()
        self.report_note.setObjectName("privacyBadge")
        root.addWidget(self.report_note, alignment=Qt.AlignmentFlag.AlignLeft)
        columns = QHBoxLayout()
        output_card = QFrame()
        output_card.setObjectName("card")
        output_layout = QVBoxLayout(output_card)
        self.outputs = QListWidget()
        output_layout.addWidget(self.outputs)
        columns.addWidget(output_card, 1)
        verify_card = QFrame()
        verify_card.setObjectName("card")
        verify_layout = QVBoxLayout(verify_card)
        self.verify_title = QLabel()
        self.verify_title.setObjectName("sectionTitle")
        self.checks = QListWidget()
        verify_layout.addWidget(self.verify_title)
        verify_layout.addWidget(self.checks)
        columns.addWidget(verify_card, 1)
        root.addLayout(columns, 1)
        actions = QHBoxLayout()
        self.new_job = QPushButton()
        self.new_job.setObjectName("secondaryButton")
        self.new_job.clicked.connect(self.new_job_requested)
        self.open_folder = QPushButton()
        self.open_folder.setObjectName("primaryButton")
        self.open_folder.clicked.connect(self.open_folder_requested)
        actions.addWidget(self.new_job)
        actions.addStretch()
        actions.addWidget(self.open_folder)
        root.addLayout(actions)
        self.retranslate(language)

    def set_reports(self, reports: list[dict[str, Any]]) -> None:
        self.outputs.clear()
        self.checks.clear()
        warnings = False
        for report in reports:
            output_details = report.get("output", {})
            output_extension = (
                str(output_details.get("extension", "")) if isinstance(output_details, dict) else ""
            )
            output = Path(
                str(report.get("_private_output_path") or f"cleaned-output{output_extension}")
            )
            state = str(report.get("state", "completed"))
            warnings = warnings or state == "completed_with_warnings"
            self.outputs.addItem(
                f"{output.name}\nSHA-256: {report['verification']['output_sha256']}"
            )
            for check in report.get("verification", {}).get("checks", []):
                status = str(check.get("status", "not_run"))
                icon = "✓" if status == "passed" else "⚠" if status == "warning" else "✕"
                self.checks.addItem(f"{icon}  {check.get('name', '')}")
        self.description.setText(
            text(self.language, "result_warning" if warnings else "result_passed")
        )

    def retranslate(self, language: str) -> None:
        self.language = language
        self.title.setText(text(language, "result_title"))
        self.description.setText(text(language, "result_passed"))
        self.report_note.setText(text(language, "report_ready"))
        self.verify_title.setText(text(language, "verification_checks"))
        self.new_job.setText(text(language, "new_job"))
        self.open_folder.setText(text(language, "open_folder"))
