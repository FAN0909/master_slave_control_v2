"""应用入口：创建并显示主窗口。"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMainWindow

if __package__:
    from .log import Logger
    from .ui.ui_MainWindow import Ui_MainWindow
else:
    # 支持在 IDE 中直接运行 src/main.py。
    from log import Logger
    from ui.ui_MainWindow import Ui_MainWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.logger = Logger.instance()
        self.logger.message_logged.connect(self._append_log)
        self.ui.pushButton_clear_log.clicked.connect(self.ui.plainTextEdit_log.clear)

    def _append_log(self, _level: str, text: str) -> None:
        log_view = self.ui.plainTextEdit_log
        log_view.appendPlainText(text)
        if self.ui.checkBox_log_autoscroll.isChecked():
            log_view.verticalScrollBar().setValue(log_view.verticalScrollBar().maximum())





def load_stylesheet(app: QApplication) -> None:
    """Load the application stylesheet and resolve its local image references."""
    style_dir = Path(__file__).resolve().parent / "res" / "style"
    stylesheet_path = style_dir / "main_window.qss"
    stylesheet = stylesheet_path.read_text(encoding="utf-8")
    stylesheet = stylesheet.replace("__STYLE_DIR__", style_dir.as_posix())
    app.setStyleSheet(stylesheet)


def main() -> int:
    app = QApplication(sys.argv)
    load_stylesheet(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
