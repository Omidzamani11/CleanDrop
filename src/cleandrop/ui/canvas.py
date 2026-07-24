from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPoint, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QPen, QPixmap
from PySide6.QtWidgets import QWidget


class RedactionCanvas(QWidget):
    rectangle_added = Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(620, 440)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._pixmap = QPixmap()
        self._auto_rects: list[dict[str, Any]] = []
        self._manual_rects: list[dict[str, Any]] = []
        self._start: QPoint | None = None
        self._current: QPoint | None = None
        self._zoom = 1.0

    def set_image(self, path: str) -> None:
        self._pixmap = QPixmap(path)
        if not self._pixmap.isNull():
            self.setMinimumSize(
                max(620, round(self._pixmap.width() * self._zoom)),
                max(440, round(self._pixmap.height() * self._zoom)),
            )
        self.update()

    def set_overlays(
        self,
        automatic: list[dict[str, Any]],
        manual: list[dict[str, Any]],
    ) -> None:
        self._auto_rects = automatic
        self._manual_rects = manual
        self.update()

    def zoom_in(self) -> None:
        self._set_zoom(min(2.5, self._zoom + 0.2))

    def zoom_out(self) -> None:
        self._set_zoom(max(0.5, self._zoom - 0.2))

    def _set_zoom(self, value: float) -> None:
        self._zoom = value
        if not self._pixmap.isNull():
            self.setMinimumSize(
                max(620, round(self._pixmap.width() * value)),
                max(440, round(self._pixmap.height() * value)),
            )
        self.updateGeometry()
        self.update()

    def _image_rect(self) -> QRectF:
        if self._pixmap.isNull():
            return QRectF()
        available = self.rect()
        ratio = min(
            available.width() / self._pixmap.width(),
            available.height() / self._pixmap.height(),
        )
        width = self._pixmap.width() * ratio
        height = self._pixmap.height() * ratio
        return QRectF(
            (available.width() - width) / 2,
            (available.height() - height) / 2,
            width,
            height,
        )

    def _to_widget_rect(self, rect: dict[str, Any]) -> QRectF:
        image = self._image_rect()
        return QRectF(
            image.x() + float(rect["x"]) * image.width(),
            image.y() + float(rect["y"]) * image.height(),
            float(rect["width"]) * image.width(),
            float(rect["height"]) * image.height(),
        )

    def paintEvent(self, _event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#111a29"))
        image_rect = self._image_rect()
        if not self._pixmap.isNull():
            painter.drawPixmap(image_rect.toRect(), self._pixmap)
        painter.setBrush(QColor(20, 184, 166, 55))
        painter.setPen(QPen(QColor("#2dd4bf"), 2))
        for rect in self._auto_rects:
            painter.drawRect(self._to_widget_rect(rect))
        painter.setBrush(QColor(239, 68, 68, 70))
        painter.setPen(QPen(QColor("#fb7185"), 2))
        for rect in self._manual_rects:
            painter.drawRect(self._to_widget_rect(rect))
        if self._start is not None and self._current is not None:
            painter.setBrush(QColor(239, 68, 68, 65))
            painter.setPen(QPen(QColor("#fb7185"), 2, Qt.PenStyle.DashLine))
            painter.drawRect(QRect(self._start, self._current).normalized())
        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() is Qt.MouseButton.LeftButton and self._image_rect().contains(
            event.position()
        ):
            self._start = event.position().toPoint()
            self._current = self._start
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._start is not None:
            point = event.position()
            image = self._image_rect()
            x = max(image.left(), min(image.right(), point.x()))
            y = max(image.top(), min(image.bottom(), point.y()))
            self._current = QPoint(round(x), round(y))
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._start is None or self._current is None:
            return
        drawn = QRect(self._start, self._current).normalized()
        image = self._image_rect()
        self._start = None
        self._current = None
        if drawn.width() < 6 or drawn.height() < 6:
            self.update()
            return
        left = max(image.left(), float(drawn.left()))
        top = max(image.top(), float(drawn.top()))
        right = min(image.right(), float(drawn.right()))
        bottom = min(image.bottom(), float(drawn.bottom()))
        normalized = {
            "x": (left - image.left()) / image.width(),
            "y": (top - image.top()) / image.height(),
            "width": (right - left) / image.width(),
            "height": (bottom - top) / image.height(),
        }
        if normalized["width"] > 0 and normalized["height"] > 0:
            self.rectangle_added.emit(normalized)
        self.update()
