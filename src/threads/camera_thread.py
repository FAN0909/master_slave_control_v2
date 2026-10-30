"""D435 相机工作对象：枚举、连接、断开与读取彩色帧。"""

import logging
from PySide6.QtCore import QObject, QTimer, Signal, Slot
from src.devices.drivers_factory import create_camera
from src.log import Logger


class CameraThread(QObject):
    sig_devices_refreshed = Signal(list)
    sig_connection_changed = Signal(bool)
    sig_color_frame = Signal(object)

    def __init__(self):
        super().__init__()
        self.device = None
        self.is_connect = False
        self.read_timer = QTimer(self)
        self.read_timer.timeout.connect(self.read_color_frame)

    def start_timer_work(self, interval_ms: int) -> bool:
        if interval_ms <= 0 or not self.is_connect:
            return False
        self.read_timer.start(interval_ms)
        return True

    def stop_timer_work(self) -> None:
        if self.read_timer.isActive():
            self.read_timer.stop()

    @Slot()
    def read_color_frame(self) -> None:
        frame = self.Get_color_frame()
        if frame is not None:
            self.sig_color_frame.emit(frame)
        elif not self.is_connect:
            self.stop_timer_work()
            self.sig_connection_changed.emit(False)

    @Slot(str, dict, int)
    def connect_device(self, model: str, options: dict, interval_ms: int) -> None:
        if self.Connect(model, options):
            Logger.instance().info(f"相机已连接：{options['serial_number']}")
            self.start_timer_work(interval_ms)
        self.sig_connection_changed.emit(self.is_connect)

    @Slot()
    def disconnect_device(self) -> None:
        if self.Disconnect():
            Logger.instance().info("相机已断开")
        self.sig_connection_changed.emit(self.is_connect)


    def Connect(self, model: str, options: dict) -> bool:
        if self.device is not None:
            try:
                if not self.device.Disconnect():
                    Logger.instance().error("已有相机断开失败，无法连接新设备")
                    return False
            except Exception as error:
                Logger.instance().error(f"已有相机断开失败，无法连接新设备：{error}")
                return False
            self.device = None

        try:
            self.device = self._create_device(model, **options)
            if self.device.Connect():
                self.is_connect = True
                return True
        except Exception as error:
            self.is_connect = False
            Logger.instance().error(f"相机连接失败：{error}")

        # 连接失败时释放驱动可能已经占用的资源。
        if self.device is not None:
            try:
                if self.device.Disconnect():
                    self.device = None
            except Exception:
                logging.exception("相机连接失败后的清理失败：%s", model)
        self.is_connect = False
        return False

    @Slot()
    def Disconnect(self) -> bool:
        if self.device is None:
            self.stop_timer_work()
            return False

        try:
            if not self.device.Disconnect():
                Logger.instance().error("相机断开失败")
                return False
        except Exception as error:
            Logger.instance().error(f"相机断开失败：{error}")
            return False

        self.stop_timer_work()
        self.device = None
        self.is_connect = False
        return True


    def _create_device(self, model: str, **options):
        return create_camera(model, **options)

    @Slot(str, dict)
    def refresh_devices(self, model: str, options: dict) -> None:
        self.sig_devices_refreshed.emit(self.list_devices(model, options))

 
    def list_devices(self, model: str, options: dict) -> list:
        # 枚举不需要建立相机连接。
        try:
            device = self._create_device(model, **options)
            devices = device.list_devices()
            return devices
        except Exception as error:
            Logger.instance().error(f"刷新相机列表失败：{error}")
            return []

    def Get_color_frame(self):
        if self.device is None or not self.device.is_connected:
            self.is_connect = False
            return None

        try:
            frame = self.device.Get_color_frame()
        except Exception as error:
            Logger.instance().error(f"相机读取彩色帧失败：{error}")
            self.is_connect = bool(self.device.is_connected)
            return None
        return frame
