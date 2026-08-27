from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from core.command_bus import CommandBus
from core.event_bus import EventBus
from core.layer_manager import LayerManager
from core.module_registry import ModuleRegistry
from core.project_context import ProjectContext
from main_window import MainWindow


def create_application(argv=None):
    app = QApplication.instance() or QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("遥感智能解译综合平台")
    app.setOrganizationName("Integrated RS")
    app.setStyle("Fusion")
    # Explicit loading also makes Chinese text reliable in offscreen/test sessions.
    font_path = Path("C:/Windows/Fonts/msyh.ttc")
    if font_path.exists():
        font_id = QFontDatabase.addApplicationFont(str(font_path))
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            app.setFont(QFont(families[0], 10))
    style_path = Path(__file__).parent / "styles" / "light.qss"
    if style_path.exists():
        app.setStyleSheet(style_path.read_text(encoding="utf-8"))

    event_bus = EventBus()
    context = ProjectContext()
    registry = ModuleRegistry(event_bus, context)
    discovery_errors = registry.discover()
    layer_manager = LayerManager(event_bus)
    command_bus = CommandBus(registry, event_bus)
    window = MainWindow(registry, command_bus, event_bus, layer_manager, context)
    for error in discovery_errors:
        window.log_panel.append(f"插件加载失败：{error}", "ERROR")
    return app, window


def main():
    app, window = create_application()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
