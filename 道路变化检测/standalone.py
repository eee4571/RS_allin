from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from plugin import create_plugin


def build_window():
    plugin = create_plugin()
    widget = plugin.create_widget()
    widget.setWindowTitle(f"{plugin.name} {plugin.version}")
    widget.resize(380, 760)
    return plugin, widget


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    plugin, widget = build_window()
    app.aboutToQuit.connect(plugin.shutdown)
    widget.show()
    exit_code = app.exec()
    plugin.shutdown()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

