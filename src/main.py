"""应用入口：创建并显示主窗口。"""

import sys

from PySide6.QtWidgets import QApplication, QMainWindow

if __package__:
    from .ui.ui_MainWindow import Ui_MainWindow
else:
    # 支持在 IDE 中直接运行 src/main.py。
    from ui.ui_MainWindow import Ui_MainWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
