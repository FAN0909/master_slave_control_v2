"""NRC 从手工作对象：驱动命令和状态读取，不承担遥操作计算。"""

import logging
import math

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from src.devices.drivers_factory import create_slave_arm


class SlaveRobotThread(QObject):


    def __init__(self):
        super().__init__()
        self.device = None
        self.is_connect = False
        self.is_enable = False

    @Slot(str, dict)
    def Connect(self, model: str, options: dict) -> bool:
        if self.device is not None and not self.Disconnect():
            return False

        try:
            self.device = self._create_device(model, **options)
            if self.device.Connect():
                self.is_connect = True
                return True
        except Exception:
            logging.exception("从手连接失败：%s", model)

        return False

    @Slot()
    def Disconnect(self) -> bool:
        if self.device is None:
            return False

        try:
            if not self.device.Disconnect():
                logging.error("从手断开失败")
                return False
        except Exception:
            logging.exception("从手断开失败")
            return False

        self.device = None
        self.is_connect = False
        return True

    def _create_device(self, model: str, **options):
        return create_slave_arm(model, **options)

    @Slot()
    def Get_joint_positions(self) -> list:
        if self.device is None or not self.device.is_connected:
            self.is_connect = False
            return []

        try:
            positions = self.device.Get_joint_positions()
        except Exception:
            logging.exception("从手读取关节位置失败")
            positions = []

        return positions if positions is not None else []

    @Slot()
    def Get_tcp_positions(self) -> list:
        if self.device is None or not self.device.is_connected:
            self.is_connect = False
            return []

        try:
            positions = self.device.Get_tcp_positions()
        except Exception:
            logging.exception("从手读取 TCP 位置失败")
            positions = []

        return positions if positions is not None else []


    @Slot()
    def Enable(self) -> bool:
        if self.device is None or not self.device.is_connected:
            self.is_connect = False
            self.is_enable = False
            return False

        try:
            if self.device.Enable():
                self.is_enable = True
                return True
        except Exception:
            logging.exception("从手使能失败")
        return False

    @Slot()
    def Disable(self) -> bool:
        if self.device is None or not self.device.is_connected:
            self.is_connect = False
            self.is_enable = False
            return False

        try:
            if self.device.Disable():
                self.is_enable = False
                return True
        except Exception:
            logging.exception("从手去使能失败")
        return False

    @Slot(list, float, float, float)
    def Move_j(self, target_positions: list, speed: float,
               acceleration: float, deceleration: float) -> bool:
        if self.device is None or not self.device.is_connected or not self.device.is_enabled:
            return False

        try:
            return bool(self.device.Move_j(target_positions, speed, acceleration, deceleration))
        except Exception:
            logging.exception("从手 Move_j 失败")
            return False

    @Slot(list, float, float, float)
    def Move_l(self, target_positions: list, speed: float,
               acceleration: float, deceleration: float) -> bool:
        if self.device is None or not self.device.is_connected or not self.device.is_enabled:
            return False

        try:
            return bool(self.device.Move_l(target_positions, speed, acceleration, deceleration))
        except Exception:
            logging.exception("从手 Move_l 失败")
            return False

    @Slot()
    def Open_servoJ(self) -> bool:
        if self.device is None or not self.device.is_connected or not self.device.is_enabled:
            return False

        try:
            return bool(self.device.Open_servoJ())
        except Exception:
            logging.exception("从手 Open_servoJ 失败")
            return False

    @Slot()
    def Close_servoJ(self) -> bool:
        if self.device is None or not self.device.is_connected:
            return False

        try:
            return bool(self.device.Close_servoJ())
        except Exception:
            logging.exception("从手 Close_servoJ 失败")
            return False

    #目标关节角（度），长度必须 ≥ 7；是目标绝对位置，不是增量
    @Slot(list)
    def Set_servoJ_pos(self, target_positions: list) -> bool:
        if self.device is None or not self.device.is_connected or not self.device.is_enabled:
            return False

        try:
            return bool(self.device.Set_servoJ_pos(target_positions))
        except Exception:
            logging.exception("从手 Set_servoJ_pos 失败")
            return False
