"""D435 相机工作对象：枚举、连接、断开与读取彩色帧。"""

import logging
from PySide6.QtCore import QObject, QTimer, Signal, Slot
from src.devices.drivers_factory import create_camera
from src.log import Logger


class CameraThread(QObject):
    sig_devices_refreshed = Signal(list)

    def __init__(self):
        super().__init__()
        self.device = None
        self.is_connect = False


    def Connect(self, model: str, options: dict) -> bool:
        if self.device is not None:
            try:
                if not self.device.Disconnect():
                    logging.error("已有相机断开失败，无法连接新设备")
                    return False
            except Exception:
                logging.exception("已有相机断开失败，无法连接新设备")
                return False
            self.device = None

        try:
            self.device = self._create_device(model, **options)
            if self.device.Connect():
                self.is_connect = True
                return True
        except Exception:
            self.is_connect = False
            logging.exception("相机连接失败：%s", model)

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
            return False

        try:
            if not self.device.Disconnect():
                logging.error("相机断开失败")
                return False
        except Exception:
            logging.exception("相机断开失败")
            return False

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
        except Exception:
            logging.exception("相机读取彩色帧失败")
            self.is_connect = False
            return None
        return frame
