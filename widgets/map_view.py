from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class MapView(QWidget):
    """Map workspace shell with replaceable context bar, tools, and canvas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("mapView")
        self.setMinimumSize(520, 360)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.context_bar = MapContextBar()
        root.addWidget(self.context_bar)
        self.canvas = MapCanvas()
        self.map_canvas = self.canvas
        root.addWidget(self.canvas, 1)

    def set_layers(self, layers):
        self.canvas.set_layers(layers)

    def zoom_to_layer(self, layer_id: str) -> None:
        """Stable placeholder for a future GIS canvas implementation."""
        self.canvas.setProperty("requestedLayerId", layer_id)


class MapContextBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("mapContextBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 7, 12, 7)
        layout.setSpacing(8)

        current_label = QLabel("当前区域：")
        self.region_value = QLabel("未选择")
        self.region_value.setObjectName("mapContextValue")
        layout.addWidget(current_label)
        layout.addWidget(self.region_value)
        layout.addSpacing(24)

        layout.addWidget(QLabel("时相对比："))
        self.before_period = QLabel("—")
        self.after_period = QLabel("—")
        self.before_period.setObjectName("periodBadge")
        self.after_period.setObjectName("periodBadge")
        layout.addWidget(self.before_period)
        layout.addWidget(QLabel("────●────"))
        layout.addWidget(self.after_period)
        layout.addStretch(1)

        for text, tooltip in (("全图", "缩放至全图"), ("框选", "框选要素"), ("刷新", "刷新地图")):
            button = QToolButton()
            button.setObjectName("mapToolButton")
            button.setText(text)
            button.setToolTip(tooltip)
            layout.addWidget(button)


class MapCanvas(QWidget):
    """Placeholder canvas; a GIS canvas can replace this class later."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("mapCanvas")
        self._layers = ()

    def set_layers(self, layers):
        self._layers = tuple(layers)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#eef1f5"))
        painter.setPen(QPen(QColor("#d8dee7"), 1))
        spacing = 42
        for x in range(0, self.width(), spacing):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), spacing):
            painter.drawLine(0, y, self.width(), y)

        painter.setPen(QPen(QColor("#b9c3d0"), 3))
        for offset in (0, 90, 180):
            path = QPainterPath(QPointF(-30, self.height() * 0.28 + offset))
            path.cubicTo(
                self.width() * 0.28, self.height() * 0.08 + offset,
                self.width() * 0.62, self.height() * 0.48 + offset,
                self.width() + 40, self.height() * 0.24 + offset,
            )
            painter.drawPath(path)

        painter.setPen(QColor("#45515e"))
        font = painter.font()
        font.setPointSize(16)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect().adjusted(0, -28, 0, 0), Qt.AlignCenter, "统一地图工作空间")
        font.setPointSize(10)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor("#7b8794"))
        painter.drawText(self.rect().adjusted(0, 18, 0, 0), Qt.AlignCenter, "等待地图数据")
