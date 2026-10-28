"""D435 相机工作对象：枚举、连接、断开与读取彩色帧。"""

import logging

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from src.devices.drivers_factory import create_camera


class CameraThread(QObject):
    sig_devices = Signal(list)
    sig_color_frame = Signal(object)
    sig_connect_result = Signal(bool, str)
    sig_disconnect_result = Signal(bool, str)
    sig_command_result = Signal(str, bool, str)
    sig_error = Signal(str)

    def __init__(self):
        super().__init__()
        self.device = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.Read)
        self.logger = logging.getLogger(type(self).__module__)

    def _error(self, message: str):
        self.logger.error(message)
        self.sig_error.emit(message)

    @Slot(str, dict)
    def Connect(self, model: str, options: dict) -> bool:
        if self.device is not None:
            self.sig_connect_result.emit(False, "请先断开当前设备")
            return False
        try:
            device = self._create_device(model, **options)
            self.device = device
            if device.Connect():
                self.sig_connect_result.emit(True, f"[{device.name}] 已连接")
                return True
            message = getattr(device, "last_error", "") or f"[{device.name}] 连接失败"
        except Exception as error:
            message = f"连接失败：{error}"
        if self.device is not None:
            try:
                if self.device.Disconnect():
                    self.device = None
                else:
                    message += f"；清理失败：{getattr(self.device, 'last_error', '')}"
            except Exception as error:
                message += f"；清理失败：{error}"
        self._error(message)
        self.sig_connect_result.emit(False, message)
        return False

    @Slot()
    def Disconnect(self) -> bool:
        self.StopPolling()
        if self.device is None:
            self.sig_disconnect_result.emit(False, "设备未创建")
            return False
        try:
            success = self.device.Disconnect()
            message = getattr(self.device, "last_error", "") or f"[{self.device.name}] 断开失败"
        except Exception as error:
            success = False
            message = f"断开失败：{error}"
        if success:
            name = self.device.name
            self.device = None
            self.sig_disconnect_result.emit(True, f"[{name}] 已断开")
            return True
        self._error(message)
        self.sig_disconnect_result.emit(False, message)
        return False

    @Slot(int)
    def StartPolling(self, interval_ms: int = 20) -> bool:
        if self.device is None or not self.device.is_connected:
            self._error("设备未连接，无法开始读取")
            return False
        if interval_ms <= 0:
            self._error("读取周期必须为正数")
            return False
        self.timer.start(interval_ms)
        return True

    @Slot()
    def StopPolling(self):
        self.timer.stop()

    @Slot()
    def Shutdown(self):
        self.StopPolling()
        if self.device is not None:
            self.Disconnect()

    def _command(self, name: str, *args) -> bool:
        if self.device is None or not self.device.is_connected:
            message = "设备未连接"
            self._error(message)
            self.sig_command_result.emit(name, False, message)
            return False
        try:
            success = bool(getattr(self.device, name)(*args))
            message = "指令已发送" if success else (getattr(self.device, "last_error", "") or "指令失败")
        except Exception as error:
            success = False
            message = f"{name} 失败：{error}"
        if not success:
            self._error(message)
        self.sig_command_result.emit(name, success, message)
        return success


    def _create_device(self, model: str, **options):
        return create_camera(model, **options)

    @Slot(str, dict)
    def list_devices(self, model: str, options: dict) -> list:
        # 枚举不需要建立相机连接。
        try:
            device = self.device or self._create_device(model, **options)
            devices = device.list_devices()
            if getattr(device, "last_error", ""):
                self._error(getattr(device, "last_error", ""))
        except Exception as error:
            devices = []
            self._error(f"相机枚举失败：{error}")
        self.sig_devices.emit(devices)
        return devices

    @Slot()
    def Get_color_frame(self):
        if self.device is None or not self.device.is_connected:
            return None
        try:
            frame = self.device.Get_color_frame()
            if not self.device.is_connected:
                self.StopPolling()
                self._error("相机读取失败，设备连接已断开；已停止轮询")
                return None
            if getattr(self.device, "last_error", ""):
                raise RuntimeError(getattr(self.device, "last_error", ""))
        except Exception as error:
            self.StopPolling()
            self._error(f"相机读取失败：{error}")
            return None
        if frame is not None:
            self.sig_color_frame.emit(frame)
        return frame

    @Slot()
    def Read(self):
        return self.Get_color_frame()
