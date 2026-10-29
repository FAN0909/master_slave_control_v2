"""应用入口：创建并显示主窗口。"""

import sys
from pathlib import Path

from PySide6.QtCore import QThread, Signal, Slot
from PySide6.QtUiTools import loadUiType
from PySide6.QtWidgets import QApplication, QMainWindow
from serial.tools import list_ports

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
    request_master_connect = Signal(str, dict)
    request_master_disconnect = Signal()

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        #初始化变量
        self.master_connected = False


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

        #master相关按钮
        self.ui.pushButton_refresh_master_port.clicked.connect(self._refresh_master_ports)
        self.ui.pushButton_connect_master_arm.clicked.connect(self._toggle_master_connection)

    #打开设置界面
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
        self.request_master_connect.connect(self.master_worker.connect_device)
        self.request_master_disconnect.connect(self.master_worker.disconnect_device)
        self.master_worker.sig_connection_changed.connect(self._on_master_connection_changed)
        self.master_thread.finished.connect(self.master_worker.disconnect_device)
        self.master_thread.finished.connect(self.master_worker.deleteLater)
        self.master_thread.start()

    def init_slave_thread(self):
        pass

    def init_hand_thread(self):
        pass

    def init_camera_thread(self):
        pass

#endregion=================================初始化线程============================================

#region====================================master相关==========================================
    @Slot()
    def _refresh_master_ports(self):
        combo = self.ui.comboBox_master_port
        selected_port = combo.currentData()
        try:
            ports = sorted(
                (
                    port for port in list_ports.comports()
                    if port.vid is not None and port.pid is not None
                ),
                key=lambda port: port.device,
            )
        except Exception as error:
            self.logger.error(f"刷新主手串口失败：{error}")
            ports = []

        combo.clear()
        for port in ports:
            combo.addItem(port.device, port.device)
        if ports:
            index = combo.findData(selected_port)
            combo.setCurrentIndex(index if index >= 0 else 0)
        else:
            combo.addItem("无可用 USB 串口", None)
        self.ui.pushButton_connect_master_arm.setEnabled(bool(ports))

    @Slot()
    def _toggle_master_connection(self):
        button = self.ui.pushButton_connect_master_arm
        if self.master_connected:
            button.setEnabled(False)
            self.ui.comboBox_master_port.setEnabled(False)
            self.ui.pushButton_refresh_master_port.setEnabled(False)
            self.ui.label_master_status.setText("● Disconnecting...")
            self.request_master_disconnect.emit()
            return

        port = self.ui.comboBox_master_port.currentData()
        if not port:
            return
        button.setEnabled(False)
        self.ui.comboBox_master_port.setEnabled(False)
        self.ui.pushButton_refresh_master_port.setEnabled(False)
        self.ui.label_master_status.setText("● Connecting...")
        self.request_master_connect.emit("Gello", {"port": port})

    @Slot(bool)
    def _on_master_connection_changed(self, connected: bool):
        self.master_connected = connected
        self.ui.label_master_status.setText(
            "● Connected" if connected else "● Disconnected"
        )
        self.ui.pushButton_connect_master_arm.setText(
            "Disconnect" if connected else "Connect"
        )
        self.ui.comboBox_master_port.setEnabled(not connected)
        self.ui.pushButton_refresh_master_port.setEnabled(not connected)
        self.ui.pushButton_connect_master_arm.setEnabled(
            connected or self.ui.comboBox_master_port.currentData() is not None
        )

#endregion=================================master相关===========================================

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
