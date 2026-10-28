"""NRC 从手工作对象：驱动命令和状态读取，不承担遥操作计算。"""

import math

from PySide6.QtCore import Signal, Slot

from src.devices.drivers_factory import create_slave_arm
from src.threads.base_device_thread import BaseDeviceThread


class SlaveRobotThread(BaseDeviceThread):
    sig_joint_positions = Signal(list)
    sig_tcp_positions = Signal(list)

    def _create_device(self, model: str, **options):
        return create_slave_arm(model, **options)

    def _read_one(self, method: str, count: int, signal) -> list:
        if self.device is None or not self.device.is_connected:
            signal.emit([])
            return []
        try:
            values = getattr(self.device, method)()
            if len(values) != count or not all(math.isfinite(value) for value in values):
                raise ValueError(self.device.last_error or f"{method} 数据无效")
        except Exception as error:
            self.StopPolling()
            self._error(f"从手读取失败：{error}")
            values = []
        signal.emit(values)
        return values

    @Slot()
    def Get_joint_positions(self) -> list:
        count = self.device.MAX_JOINT_COUNT if self.device is not None else 0
        return self._read_one("Get_joint_positions", count, self.sig_joint_positions)

    @Slot()
    def Get_tcp_positions(self) -> list:
        count = self.device.TCP_DIM if self.device is not None else 0
        return self._read_one("Get_tcp_positions", count, self.sig_tcp_positions)

    @Slot()
    def Read(self):
        if self.device is None or not self.device.is_connected:
            self.sig_joint_positions.emit([])
            self.sig_tcp_positions.emit([])
            return [], []
        try:
            joints = self.device.Get_joint_positions()
            tcp = self.device.Get_tcp_positions()
            if len(joints) != self.device.MAX_JOINT_COUNT or not all(
                math.isfinite(value) for value in joints
            ):
                raise ValueError(self.device.last_error or "从手关节数据无效")
            if len(tcp) != self.device.TCP_DIM or not all(
                math.isfinite(value) for value in tcp
            ):
                raise ValueError(self.device.last_error or "从手 TCP 数据无效")
        except Exception as error:
            self.StopPolling()
            self._error(f"从手读取失败：{error}")
            joints, tcp = [], []
        self.sig_joint_positions.emit(joints)
        self.sig_tcp_positions.emit(tcp)
        return joints, tcp

    def _motion_ready(self, command: str) -> bool:
        if self.device is not None and self.device.is_connected and self.device.is_enabled:
            return True
        message = "从手未连接或未上电"
        self._error(message)
        self.sig_command_result.emit(command, False, message)
        return False

    @Slot()
    def Enable(self) -> bool:
        return self._command("Enable")

    @Slot()
    def Disable(self) -> bool:
        if not self._motion_ready("Disable"):
            return False
        if self.device.is_servoj_open and not self.Close_servoJ():
            self.sig_command_result.emit("Disable", False, "关闭 ServoJ 失败")
            return False
        return self._command("Disable")

    @Slot(list, float, float, float)
    def Move_j(self, target_positions: list, speed: float,
               acceleration: float, deceleration: float) -> bool:
        if not self._motion_ready("Move_j"):
            return False
        if self.device.is_servoj_open and not self.Close_servoJ():
            self.sig_command_result.emit("Move_j", False, "关闭 ServoJ 失败")
            return False
        return self._command("Move_j", target_positions, speed, acceleration, deceleration)

    @Slot(list, float, float, float)
    def Move_l(self, target_positions: list, speed: float,
               acceleration: float, deceleration: float) -> bool:
        if not self._motion_ready("Move_l"):
            return False
        if self.device.is_servoj_open and not self.Close_servoJ():
            self.sig_command_result.emit("Move_l", False, "关闭 ServoJ 失败")
            return False
        return self._command("Move_l", target_positions, speed, acceleration, deceleration)

    @Slot()
    def Open_servoJ(self) -> bool:
        if not self._motion_ready("Open_servoJ"):
            return False
        return self._command("Open_servoJ")

    @Slot()
    def Close_servoJ(self) -> bool:
        return self._command("Close_servoJ")

    @Slot(list)
    def Set_servoJ_pos(self, target_positions: list) -> bool:
        if not self._motion_ready("Set_servoJ_pos"):
            return False
        if not self.device.is_servoj_open:
            message = "ServoJ 尚未打开"
            self._error(message)
            self.sig_command_result.emit("Set_servoJ_pos", False, message)
            return False
        return self._command("Set_servoJ_pos", target_positions)
