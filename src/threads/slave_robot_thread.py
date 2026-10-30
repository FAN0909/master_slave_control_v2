"""NRC 从手工作对象：驱动命令和状态读取，不承担遥操作计算。"""

import logging
import math

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from src.devices.drivers_factory import create_slave_arm
from src.log import Logger


class SlaveRobotThread(QObject):
    sig_connection_changed = Signal(bool)
    sig_power_changed = Signal(bool)
    sig_joint_positions = Signal(list)
    sig_tcp_positions = Signal(list)

    def __init__(self):
        super().__init__()
        self.device = None
        self.is_connect = False
        self.is_enable = False
        self.read_timer = QTimer(self)
        self.read_timer.timeout.connect(self.read_positions)

    def start_timer_work(self, interval_ms: int) -> bool:
        if interval_ms <= 0 or not self.is_connect:
            return False
        if self.read_timer.isActive():
            self.read_timer.setInterval(interval_ms)
        else:
            self.read_timer.start(interval_ms)
        return True

    def stop_timer_work(self) -> None:
        if self.read_timer.isActive():
            self.read_timer.stop()

    @Slot()
    def read_positions(self) -> None:
        joint_positions = self.Get_joint_positions()
        if not self.is_connect:
            self.stop_timer_work()
            self.sig_connection_changed.emit(False)
            return
        if joint_positions:
            self.sig_joint_positions.emit(joint_positions)

        tcp_positions = self.Get_tcp_positions()
        if not self.is_connect:
            self.stop_timer_work()
            self.sig_connection_changed.emit(False)
            return
        if tcp_positions:
            self.sig_tcp_positions.emit(tcp_positions)

    @Slot(str, dict, int)
    def connect_device(self, model: str, options: dict, interval_ms: int) -> None:
        if self.Connect(model, options):
            Logger.instance().info(f"从手已连接：{model}，IP {options.get('ip_address', '')}")
            self.start_timer_work(interval_ms)
        self.sig_connection_changed.emit(self.is_connect)

    @Slot()
    def disconnect_device(self) -> None:
        if self.device is not None:
            if self.Disconnect():
                Logger.instance().info("从手已断开")
            else:
                Logger.instance().error("从手断开失败")
        self.sig_connection_changed.emit(self.is_connect)

    @Slot()
    def power_on(self) -> None:
        if self.Enable():
            Logger.instance().info("从手已上电")
        else:
            Logger.instance().error("从手上电失败")
        self.sig_power_changed.emit(self.is_enable)

    @Slot()
    def power_off(self) -> None:
        if self.Disable():
            Logger.instance().info("从手已下电")
        else:
            Logger.instance().error("从手下电失败")
        self.sig_power_changed.emit(self.is_enable)

    @Slot(str, dict)
    def Connect(self, model: str, options: dict) -> bool:
        if self.device is not None and not self.Disconnect():
            Logger.instance().error("从手连接失败：现有设备断开失败")
            return False

        try:
            self.device = self._create_device(model, **options)
            if self.device.Connect():
                self.is_connect = True
                return True
        except Exception as error:
            Logger.instance().error(f"从手连接失败：{error}")
        else:
            Logger.instance().error(f"从手连接失败：{model}，IP {options.get('ip_address', '')}")

        if self.device is not None:
            self.Disconnect()
        self.is_connect = False
        return False

    @Slot()
    def Disconnect(self) -> bool:
        self.stop_timer_work()
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
        self.is_enable = False
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

        self.is_connect = bool(self.device.is_connected)
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

        self.is_connect = bool(self.device.is_connected)
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


    def Move_j(self, target_positions: list, speed: float,
               acceleration: float, deceleration: float) -> bool:
        if self.device is None or not self.device.is_connected or not self.device.is_enabled:
            return False

        try:
            return bool(self.device.Move_j(target_positions, speed, acceleration, deceleration))
        except Exception:
            logging.exception("从手 Move_j 失败")
            return False

    @Slot(str, list, float, float)
    def move_home(self, home_joints: list,
                  speed: float =50, acceleration: float =100) -> None:
        if (not self.is_connect or not self.is_enable or self.device is None):
            Logger.instance().error("从手未连接、未上电或型号已改变，无法执行 Home")
            return
        if self.Move_j(home_joints, speed, acceleration, acceleration):
            Logger.instance().info(f"从手已发送 Home 关节运动：{self.device.name}")
        else:
            Logger.instance().error(f"从手 Home 关节运动失败：{self.device.name}")


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
