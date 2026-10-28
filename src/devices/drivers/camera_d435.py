from __future__ import annotations

from typing import TYPE_CHECKING

from src.devices.base.base_camera import BaseCamera

if TYPE_CHECKING:
    import numpy as np


class CameraD435(BaseCamera):
    """Intel RealSense D435：返回独立的 BGR8 彩色帧。"""

    def __init__(self, name: str, serial_number: str | None = None):
        super().__init__(name)
        self.serial_number = serial_number
        self.camera_manager = None

    def _manager(self):
        if self.camera_manager is None:
            from vendor.realsense.realsense_manager import RealSenseManager

            self.camera_manager = RealSenseManager()
        return self.camera_manager

    def list_devices(self) -> list[tuple[str, str]]:
        """返回 (名称, 序列号)；枚举失败返回 [] 并设置 last_error。"""
        self.last_error = ""
        try:
            return self._manager().list_devices()
        except Exception as error:
            self._fail(f"list devices failed: {error}")
            return []

    def Connect(self) -> bool:
        if self.is_connected:
            return True
        self.last_error = ""
        try:
            manager = self._manager()
            manager.connect(self.serial_number)
            if not manager.is_connected():
                raise RuntimeError("camera is not connected")
            self.is_connected = True
            return True
        except Exception as error:
            self.is_connected = False
            return self._fail(f"connect failed: {error}")

    def Disconnect(self) -> bool:
        try:
            if self.camera_manager is not None:
                self.camera_manager.disconnect()
            self.is_connected = False
            self.is_enabled = False
            self.last_error = ""
            return True
        except Exception as error:
            self.is_connected = self.camera_manager.is_connected()
            return self._fail(f"disconnect failed: {error}")

    def Get_color_frame(self) -> np.ndarray | None:
        if not self._ready():
            return None
        try:
            return self.camera_manager.get_color_frame()
        except Exception as error:
            self._fail(f"get color frame failed: {error}")
            return None
