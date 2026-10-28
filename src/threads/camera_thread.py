"""D435 相机工作对象：枚举、连接、断开与读取彩色帧。"""

from PySide6.QtCore import Signal, Slot

from src.devices.drivers_factory import create_camera
from src.threads.base_device_thread import BaseDeviceThread


class CameraThread(BaseDeviceThread):
    sig_devices = Signal(list)
    sig_color_frame = Signal(object)

    def _create_device(self, model: str, **options):
        return create_camera(model, **options)

    @Slot(str, dict)
    def list_devices(self, model: str, options: dict) -> list:
        # 枚举不需要建立相机连接。
        try:
            device = self.device or self._create_device(model, **options)
            devices = device.list_devices()
            if device.last_error:
                self._error(device.last_error)
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
            if self.device.last_error:
                raise RuntimeError(self.device.last_error)
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
