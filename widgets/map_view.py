from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class MapView(QWidget):
    """Neutral shared map workspace placeholder for future GIS integration."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("mapView")
        self.setMinimumSize(520, 360)
        self._layers = ()

    def set_layers(self, layers):
        self._layers = layers
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#f3f6f7"))
        painter.setPen(QPen(QColor("#dce4e7"), 1))
        spacing = 42
        for x in range(0, self.width(), spacing):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), spacing):
            painter.drawLine(0, y, self.width(), y)

        painter.setPen(QPen(QColor("#c5d0d4"), 3))
        for offset in (0, 90, 180):
            path = QPainterPath(QPointF(-30, self.height() * 0.28 + offset))
            path.cubicTo(
                self.width() * 0.28, self.height() * 0.08 + offset,
                self.width() * 0.62, self.height() * 0.48 + offset,
                self.width() + 40, self.height() * 0.24 + offset,
            )
            painter.drawPath(path)

        painter.setPen(QColor("#24343b"))
        font = painter.font()
        font.setPointSize(16)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect().adjusted(0, -28, 0, 0), Qt.AlignCenter, "统一地图工作空间")
        font.setPointSize(10)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor("#6b7d85"))
        painter.drawText(self.rect().adjusted(0, 18, 0, 0), Qt.AlignCenter, "影像 · 道路 · 建筑物 · 变化成果")

        painter.setPen(Qt.NoPen)
        palette = ("#22a06b", "#3b82f6", "#d97706", "#8b5cf6", "#0891b2")
        for index, layer in enumerate(self._layers[-5:]):
            color = QColor(palette[sum(ord(char) for char in layer.layer_type) % len(palette)])
            painter.setBrush(color)
            painter.drawRoundedRect(18, 18 + index * 29, 10, 10, 3, 3)
            painter.setPen(QColor("#40545d"))
            painter.drawText(36, 28 + index * 29, layer.name)
            painter.setPen(Qt.NoPen)
