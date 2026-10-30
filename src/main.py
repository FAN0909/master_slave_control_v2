"""应用入口：创建并显示主窗口。"""

import sys
from functools import partial
from ipaddress import IPv4Address
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtUiTools import loadUiType
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow
from serial.tools import list_ports

if __package__:
    from .log import Logger
    from .threads.camera_thread import CameraThread
    from .threads.hand_thread import HandThread
    from .threads.master_robot_thread import MasterRobotThread
    from .threads.slave_robot_thread import SlaveRobotThread
    from .ui.settings_dialog import SettingsDialog
else:
    # 支持在 IDE 中直接运行 src/main.py。
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src.log import Logger
    from src.threads.camera_thread import CameraThread
    from src.threads.hand_thread import HandThread
    from src.threads.master_robot_thread import MasterRobotThread
    from src.threads.slave_robot_thread import SlaveRobotThread
    from src.ui.settings_dialog import SettingsDialog


UI_PATH = Path(__file__).resolve().parent / "ui" / "main_window.ui"
Ui_MainWindow, _ = loadUiType(str(UI_PATH))


class MainWindow(QMainWindow):
    request_master_connect = Signal(str, dict, int)
    request_master_disconnect = Signal()
    request_slave_connect = Signal(str, dict, int)
    request_slave_disconnect = Signal()
    request_slave_power_on = Signal()
    request_slave_power_off = Signal()
    request_hand_connect = Signal(str, dict, int)
    request_hand_disconnect = Signal()
    request_camera_refresh = Signal(str, dict)
    request_camera_connect_side = Signal(str, dict, int)
    request_camera_connect_front = Signal(str, dict, int)
    request_camera_connect_hand = Signal(str, dict, int)
    request_camera_disconnect_side = Signal()
    request_camera_disconnect_front = Signal()
    request_camera_disconnect_hand = Signal()

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        #初始化变量
        self.master_connected = False
        self.slave_connected = False
        self.slave_enabled = False
        #记录当前连接的设备型号
        self.slave_model = None
        self.hand_model = None
        self.hand_connected = False
        self.camera_connected = {camera: False for camera in ("side", "front", "hand")}


        self.init_ui()
        self.init_thread()

#region====================================初始化界面==========================================
    def init_ui(self):
        #init log connect
        self.logger = Logger.instance()
        self.logger.message_logged.connect(self._append_log)
        self.ui.pushButton_clear_log.clicked.connect(self.ui.plainTextEdit_log.clear)

        for label in (
            self.ui.label_master_status,
            self.ui.label_slave_status,
            self.ui.label_hand_status,
            self.ui.label_camera_status_1,
            self.ui.label_camera_status_2,
            self.ui.label_camera_status_3,
        ):
            self._set_connection_status(label, "● Disconnected", "disconnected")

        #init set ui
        self.set_dialog = SettingsDialog(self)
        #init button connect clicked
        self.init_button_connect()

    def init_button_connect(self):
        self.ui.menuSet_Param.triggered.connect(self._open_settings)

        #master相关按钮
        self.ui.pushButton_refresh_master_port.clicked.connect(self._refresh_master_ports)
        self.ui.pushButton_connect_master_arm.clicked.connect(self._toggle_master_connection)

        # slave 相关按钮
        self.ui.Btn_robot_connect.clicked.connect(self._toggle_slave_connection)
        self.ui.pushButton_robot_PowerOn.clicked.connect(self._toggle_slave_power)
        self.ui.pushButton_robot_PowerOn.setEnabled(False)

        # hand 相关按钮
        self.ui.pushButton_refresh_hand_connect_info.clicked.connect(
            self._refresh_hand_comm_info
        )
        self.ui.pushButton_connect_hand.clicked.connect(self._toggle_hand_connection)

        # camera 相关按钮
        self.ui.pushButton_camera_refresh.clicked.connect(self._refresh_camera_devices)
        self.camera_controls = {
            "side": (self.ui.comboBox_camera_device_side,
                     self.ui.pushButton_connect_side_camera, self.ui.label_camera_status_1),
            "front": (self.ui.comboBox_camera_device_front,
                      self.ui.pushButton_connect__front_camera, self.ui.label_camera_status_2),
            "hand": (self.ui.comboBox_camera_device_hand,
                     self.ui.pushButton_connect_camera_hand, self.ui.label_camera_status_3),
        }
        self.camera_previews = {
            "side": self.ui.label_camera_preview_1,
            "front": self.ui.label_camera_preview_2,
            "hand": self.ui.label_camera_preview_3,
        }
        for camera, (_, button, _) in self.camera_controls.items():
            button.clicked.connect(partial(self._toggle_camera_connection, camera))

    #打开设置界面
    def _open_settings(self) -> None:
        self.set_dialog.show()

    #设置连接状态标签
    def _set_connection_status(self, label: QLabel, text: str, state: str) -> None:
        label.setText(text)
        label.setProperty("uiRole", "connectionStatus")
        label.setProperty("connectionState", state)
        label.style().unpolish(label)
        label.style().polish(label)
        label.update()

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
        self.master_worker.sig_joint_positions.connect(
            self.set_dialog.update_master_joint_positions
        )
        self.master_thread.finished.connect(self.master_worker.disconnect_device)
        self.master_thread.finished.connect(self.master_worker.deleteLater)
        self.master_thread.start()

    def init_slave_thread(self):
        self.slave_thread = QThread(self)
        self.slave_worker = SlaveRobotThread()
        self.slave_worker.moveToThread(self.slave_thread)
        self.request_slave_connect.connect(self.slave_worker.connect_device)
        self.request_slave_disconnect.connect(self.slave_worker.disconnect_device)
        self.request_slave_power_on.connect(self.slave_worker.power_on)
        self.request_slave_power_off.connect(self.slave_worker.power_off)
        self.slave_worker.sig_connection_changed.connect(self._on_slave_connection_changed)
        self.slave_worker.sig_power_changed.connect(self._on_slave_power_changed)
        self.slave_worker.sig_joint_positions.connect(
            self.set_dialog.update_slave_joint_positions
        )
        self.slave_worker.sig_tcp_positions.connect(
            self.set_dialog.update_slave_tcp_positions
        )
        self.slave_thread.finished.connect(self.slave_worker.disconnect_device)
        self.slave_thread.finished.connect(self.slave_worker.deleteLater)
        self.slave_thread.start()

    def init_hand_thread(self):
        self.hand_thread = QThread(self)
        self.hand_worker = HandThread()
        self.hand_worker.moveToThread(self.hand_thread)
        self.request_hand_connect.connect(self.hand_worker.connect_device)
        self.request_hand_disconnect.connect(self.hand_worker.disconnect_device)
        self.hand_worker.sig_connection_changed.connect(self._on_hand_connection_changed)
        self.hand_worker.sig_joint_positions.connect(
            self.set_dialog.update_hand_joint_positions
        )
        self.hand_thread.finished.connect(self.hand_worker.disconnect_device)
        self.hand_thread.finished.connect(self.hand_worker.deleteLater)
        self.hand_thread.start()

    def init_camera_thread(self):
        self.camera_threads = {}
        self.camera_workers = {}
        for camera in ("side", "front", "hand"):
            thread = QThread(self)
            worker = CameraThread()
            worker.moveToThread(thread)
            thread.finished.connect(worker.Disconnect)
            thread.finished.connect(worker.deleteLater)
            thread.start()
            self.camera_threads[camera] = thread
            self.camera_workers[camera] = worker
            getattr(self, f"request_camera_connect_{camera}").connect(worker.connect_device)
            getattr(self, f"request_camera_disconnect_{camera}").connect(worker.disconnect_device)
            worker.sig_connection_changed.connect(
                partial(self._on_camera_connection_changed, camera)
            )
            worker.sig_color_frame.connect(partial(self._on_camera_frame, camera))
        # 相机设备列表是全局的，查询一次后会同步更新 side、front、hand 三个下拉框。
        self.request_camera_refresh.connect(self.camera_workers["side"].refresh_devices)
        self.camera_workers["side"].sig_devices_refreshed.connect(
            self._on_camera_devices_refreshed
        )

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
            self._set_connection_status(
                self.ui.label_master_status, "● Disconnecting...", "disconnecting"
            )
            self.request_master_disconnect.emit()
            return

        port = self.ui.comboBox_master_port.currentData()
        if not port:
            return
        try:
            interval_ms = int(self.ui.lineEdit_master_read_pos_rate.text().strip())
            if not 0 < interval_ms <= 2_147_483_647:
                raise ValueError
        except ValueError:
            self.logger.error("主手读取周期必须是正整数（毫秒）")
            return
        button.setEnabled(False)
        self.ui.comboBox_master_port.setEnabled(False)
        self.ui.pushButton_refresh_master_port.setEnabled(False)
        self._set_connection_status(
            self.ui.label_master_status, "● Connecting...", "connecting"
        )
        self.request_master_connect.emit("Gello", {"port": port}, interval_ms)

    @Slot(bool)
    def _on_master_connection_changed(self, connected: bool):
        self.master_connected = connected
        self._set_connection_status(
            self.ui.label_master_status,
            "● Connected" if connected else "● Disconnected",
            "connected" if connected else "disconnected",
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

#region====================================slave相关=============================================
    @Slot()
    def _toggle_slave_connection(self):
        button = self.ui.Btn_robot_connect
        button.setEnabled(False)
        self.ui.comboBox_robot_type.setEnabled(False)
        self.ui.lineEdit_slave_arm_ip.setEnabled(False)

        if self.slave_connected:
            self._set_connection_status(
                self.ui.label_slave_status, "● Disconnecting...", "disconnecting"
            )
            self.request_slave_disconnect.emit()
            return

        model = self.ui.comboBox_robot_type.currentText()
        ip = self.ui.lineEdit_slave_arm_ip.text().strip()
        try:
            IPv4Address(ip)
        except ValueError:
            self.logger.error("从手 IP 地址无效")
            self._on_slave_connection_changed(False)
            return
        try:
            interval_ms = int(self.ui.lineEdit_slave_read_pos_rate.text().strip())
            if not 0 < interval_ms <= 2_147_483_647:
                raise ValueError
        except ValueError:
            self.logger.error("从手读取周期必须是正整数（毫秒）")
            self._on_slave_connection_changed(False)
            return

        self._set_connection_status(
            self.ui.label_slave_status, "● Connecting...", "connecting"
        )
        self.slave_model = model
        self.request_slave_connect.emit(model, {"ip_address": ip}, interval_ms)

    @Slot(bool)
    def _on_slave_connection_changed(self, connected: bool):
        self.slave_connected = connected
        if connected and self.slave_model:
            self.set_dialog.update_slave_config(self.slave_model)
        if not connected:
            self.set_dialog.update_slave_config(None) #断开连接后更新设置界面
            self.slave_enabled = False
            self.ui.pushButton_robot_PowerOn.setText("PowerOn")
        self.ui.pushButton_robot_PowerOn.setEnabled(connected)
        self._set_connection_status(
            self.ui.label_slave_status,
            "● Connected" if connected else "● Disconnected",
            "connected" if connected else "disconnected",
        )
        self.ui.Btn_robot_connect.setText("Disconnect" if connected else "Connect")
        self.ui.Btn_robot_connect.setEnabled(True)
        self.ui.comboBox_robot_type.setEnabled(not connected)
        self.ui.lineEdit_slave_arm_ip.setEnabled(not connected)

    @Slot()
    def _toggle_slave_power(self):
        if not self.slave_connected:
            return
        self.ui.pushButton_robot_PowerOn.setEnabled(False)
        if self.slave_enabled:
            self.request_slave_power_off.emit()
        else:
            self.request_slave_power_on.emit()

    @Slot(bool)
    def _on_slave_power_changed(self, enabled: bool):
        self.slave_enabled = enabled
        self.ui.pushButton_robot_PowerOn.setText("PowerOff" if enabled else "PowerOn")
        self.ui.pushButton_robot_PowerOn.setEnabled(self.slave_connected)

#endregion====================================slave相关=============================================

#region====================================hand相关================================================
    @Slot()
    def _refresh_hand_comm_info(self):
        combo = self.ui.comboBox_hand_comm_info
        selected_info = combo.currentData()
        comm_type = self.ui.comboBox_hand_comm_type.currentText()
        try:
            if comm_type == "Modbus":
                empty_text = "无可用 USB 串口"
                interfaces = sorted(
                    port.device
                    for port in list_ports.comports()
                    if port.vid is not None and port.pid is not None
                )
            elif comm_type == "Can":
                empty_text = "无可用 CAN 接口"
                interfaces = sorted(
                    interface.name
                    for interface in Path("/sys/class/net").iterdir()
                    if (interface / "type").read_text().strip() == "280"
                )
            else:
                self.logger.error(f"不支持的灵巧手通信方式：{comm_type}")
                return
        except (OSError, ValueError) as error:
            self.logger.error(f"刷新灵巧手通信接口失败：{error}")
            interfaces = []

        combo.clear()
        for interface in interfaces:
            combo.addItem(interface, interface)
        if interfaces:
            index = combo.findData(selected_info)
            combo.setCurrentIndex(index if index >= 0 else 0)
        else:
            combo.addItem(empty_text, None)
        combo.setProperty("commType", comm_type)

    @Slot()
    def _toggle_hand_connection(self):
        if self.hand_connected:
            self.ui.pushButton_connect_hand.setEnabled(False)
            self._set_connection_status(
                self.ui.label_hand_status, "● Disconnecting...", "disconnecting"
            )
            self.request_hand_disconnect.emit()
            return

        comm_type = self.ui.comboBox_hand_comm_type.currentText()
        comm_info = self.ui.comboBox_hand_comm_info.currentData()
        if self.ui.comboBox_hand_comm_info.property("commType") != comm_type:
            self.logger.error("请先刷新当前通信方式的接口列表")
            return
        if comm_info is None:
            self.logger.error("请选择灵巧手通信接口")
            return
        try:
            interval_ms = int(self.ui.lineEdit_hand_read_pos_rate.text().strip())
            if not 0 < interval_ms <= 2_147_483_647:
                raise ValueError
        except ValueError:
            self.logger.error("灵巧手读取周期必须是正整数（毫秒）")
            return

        model = self.ui.comboBox_hand_model.currentText()
        options = {
            "hand_type": self.ui.comboBox_hand_type.currentText(),
            "hand_joint": model.removeprefix("Linker"),
            "comm_type": comm_type,
            "comm_info": comm_info,
        }
        self.ui.pushButton_connect_hand.setEnabled(False)
        self._set_connection_status(
            self.ui.label_hand_status, "● Connecting...", "connecting"
        )
        self.hand_model = model
        self.request_hand_connect.emit(model, options, interval_ms)

    @Slot(bool)
    def _on_hand_connection_changed(self, connected: bool):
        self.hand_connected = connected
        self._set_connection_status(
            self.ui.label_hand_status,
            "● Connected" if connected else "● Disconnected",
            "connected" if connected else "disconnected",
        )
        self.ui.pushButton_connect_hand.setText(
            "Disconnect" if connected else "Connect"
        )
        self.ui.pushButton_connect_hand.setEnabled(True)
        if connected and self.hand_model:
            self.set_dialog.update_hand_config(self.hand_model)
        if not connected:
            self.set_dialog.update_hand_config(None)


#endregion====================================hand相关================================================

#region=====================================camera相关=================================================
    @Slot()
    def _refresh_camera_devices(self):
        self.ui.pushButton_camera_refresh.setEnabled(False)
        model = self.ui.comboBox_camera_model.currentText().removeprefix("RealSense")
        self.request_camera_refresh.emit(model, {})

    @Slot(list)
    def _on_camera_devices_refreshed(self, devices: list):
        for camera, (combo, _, _) in self.camera_controls.items():
            if not combo.isEnabled():
                continue
            selected_serial = combo.currentData()
            combo.clear()
            for name, serial in devices:
                combo.addItem(f"{name} ({serial})", serial)
            if devices:
                index = combo.findData(selected_serial)
                combo.setCurrentIndex(index if index >= 0 else 0)
            else:
                combo.addItem("无可用相机", None)
        self.ui.pushButton_camera_refresh.setEnabled(True)

    def _toggle_camera_connection(self, camera: str, _checked: bool = False) -> None:
        combo, button, label = self.camera_controls[camera]
        if self.camera_connected[camera]:
            button.setEnabled(False)
            self._set_connection_status(label, "● Disconnecting...", "disconnecting")
            getattr(self, f"request_camera_disconnect_{camera}").emit()
            return

        serial = combo.currentData()
        if serial is None:
            self.logger.error("请先刷新并选择相机设备")
            return
        try:
            interval_ms = int(self.ui.lineEdit_camera_frame_interval.text().strip())
            if not 0 < interval_ms <= 2_147_483_647:
                raise ValueError
        except ValueError:
            self.logger.error("相机读取周期必须是正整数（毫秒）")
            return
        model = self.ui.comboBox_camera_model.currentText().removeprefix("RealSense")
        button.setEnabled(False)
        combo.setEnabled(False)
        self._set_connection_status(label, "● Connecting...", "connecting")
        getattr(self, f"request_camera_connect_{camera}").emit(
            model, {"serial_number": serial}, interval_ms
        )

    def _on_camera_connection_changed(self, camera: str, connected: bool) -> None:
        self.camera_connected[camera] = connected
        combo, button, label = self.camera_controls[camera]
        self._set_connection_status(
            label,
            "● Connected" if connected else "● Disconnected",
            "connected" if connected else "disconnected",
        )
        button.setText("Disconnect" if connected else "Connect")
        button.setEnabled(True)
        combo.setEnabled(not connected)
        if not connected:
            self.camera_previews[camera].clear()

    def _on_camera_frame(self, camera: str, frame) -> None:
        if not self.camera_connected[camera]:
            return
        label = self.camera_previews[camera]
        height, width = frame.shape[:2]
        image = QImage(frame.data, width, height, frame.strides[0], QImage.Format_BGR888)
        label.setPixmap(
            QPixmap.fromImage(image).scaled(
                label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        )



#endregion=====================================camera相关=================================================

    def closeEvent(self, event):
        self.master_thread.quit()
        self.slave_thread.quit()
        self.hand_thread.quit()
        for thread in self.camera_threads.values():
            thread.quit()
        self.master_thread.wait()
        self.slave_thread.wait()
        self.hand_thread.wait()
        for thread in self.camera_threads.values():
            thread.wait()
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
