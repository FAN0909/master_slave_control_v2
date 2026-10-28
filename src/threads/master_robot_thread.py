"""Gello 主手工作对象：连接、断开、读取关节角度。"""

import math

from PySide6.QtCore import Signal, Slot

from src.devices.drivers_factory import create_master_arm
from src.threads.base_device_thread import BaseDeviceThread


class MasterRobotThread(BaseDeviceThread):
    sig_joint_positions = Signal(list)

    def _create_device(self, model: str, **options):
        return create_master_arm(model, **options)

    @Slot()
    def Get_joint_positions(self) -> list:
        if self.device is None or not self.device.is_connected:
            self.sig_joint_positions.emit([])
            return []
        try:
            joints = self.device.Get_joint_positions()
            if len(joints) != self.device.MAX_JOINT_COUNT or not all(
                math.isfinite(value) for value in joints
            ):
                raise ValueError(self.device.last_error or "主手关节数据无效")
        except Exception as error:
            self.StopPolling()
            self._error(f"主手读取失败：{error}")
            joints = []
        self.sig_joint_positions.emit(joints)
        return joints

    @Slot()
    def Read(self):
        return self.Get_joint_positions()
