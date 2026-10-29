"""应用入口：创建并显示主窗口。"""

import sys
from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtUiTools import loadUiType
from PySide6.QtWidgets import QApplication, QMainWindow

if __package__:
    from .log import Logger
    from .threads.master_robot_thread import MasterRobotThread
    from .ui.settings_dialog import SettingsDialog
else:
    # 支持在 IDE 中直接运行 src/main.py。
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src.log import Logger
    from src.threads.master_robot_thread import MasterRobotThread
    from src.ui.settings_dialog import SettingsDialog


UI_PATH = Path(__file__).resolve().parent / "ui" / "main_window.ui"
Ui_MainWindow, _ = loadUiType(str(UI_PATH))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.init_ui()

        self.init_thread()

#region====================================初始化界面==========================================
    def init_ui(self):
        #init log connect
        self.logger = Logger.instance()
        self.logger.message_logged.connect(self._append_log)
        self.ui.pushButton_clear_log.clicked.connect(self.ui.plainTextEdit_log.clear)

        #init set ui
        self.set_dialog = SettingsDialog(self)
        #init button connect clicked
        self.init_button_connect()

    def init_button_connect(self):
        self.ui.menuSet_Param.triggered.connect(self._open_settings)

    #open set ui    
    def _open_settings(self) -> None:
        self.set_dialog.show()

#endregion==================================初始化界面=============================================

#region====================================初始化线程===========================================
    def init_thread(self):
        self.init_master_thread()
        self.init_slave_thread()
        self.init_hand_thread()
        self.init_camera_thread()

    
    def init_master_thread(self):
        self.master_thread = QThread(self)
        self.master_worker = MasterRobotThread()
        self.master_worker.moveToThread(self.master_thread)
        self.master_thread.finished.connect(self.master_worker.deleteLater)
        


        self.master_thread.start()
    def init_slave_thread(self):
        pass
    def init_hand_thread(self):
        pass
    def init_camera_thread(self):
        pass

#endregion=================================初始化线程============================================
    def closeEvent(self, event):
        self.master_thread.quit()
        self.master_thread.wait()
        super().closeEvent(event)

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
