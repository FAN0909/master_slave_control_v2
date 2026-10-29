"""Gello 主手工作对象：连接、断开、读取关节角度。"""

import logging
import math

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from src.devices.drivers_factory import create_master_arm
from src.log import Logger


class MasterRobotThread(QObject):
    sig_connection_changed = Signal(bool)
    sig_joint_positions = Signal(list)

    def __init__(self):
        super().__init__()
        self.device = None
        self.is_connect = False
        self.logger = Logger.instance()
        self.read_timer = QTimer(self)
        self.read_timer.timeout.connect(self.read_joint_pos)


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
    def read_joint_pos(self) -> None:
        positions = self.Get_joint_positions()
        if positions:
            self.sig_joint_positions.emit(positions)
        elif not self.is_connect:
            self.stop_timer_work()
            self.sig_connection_changed.emit(False)

    @Slot(str, dict, int)
    def connect_device(self, model: str, options: dict, interval_ms: int) -> None:
        if self.Connect(model, options):
            self.logger.info(f"主手已连接：{model}，端口 {options.get('port', '')}")
            self.start_timer_work(interval_ms)
        else:
            self.logger.error(f"主手连接失败：{model}，端口 {options.get('port', '')}")
        self.sig_connection_changed.emit(self.is_connect)

    @Slot()
    def disconnect_device(self) -> None:
        if self.device is not None:
            if self.Disconnect():
                self.logger.info("主手已断开")
            else:
                self.logger.error("主手断开失败")
        self.sig_connection_changed.emit(self.is_connect)


    def Connect(self, model: str, options: dict) -> bool:
        if self.device is not None and not self.Disconnect():
            return False

        try:
            self.device = self._create_device(model, **options)
            if self.device.Connect():
                self.is_connect = True
                return True
        except Exception:
            logging.exception("主手连接失败：%s", model)

        if self.device is not None:
            self.Disconnect()
        self.is_connect = False
        return False


    def Disconnect(self) -> bool:
        self.stop_timer_work()
        if self.device is None:
            return False

        try:
            if not self.device.Disconnect():
                logging.error("主手断开失败")
                return False
        except Exception:
            logging.exception("主手断开失败")
            return False

        self.device = None
        self.is_connect = False
        return True

    def _create_device(self, model: str, **options):
        return create_master_arm(model, **options)


    def Get_joint_positions(self) -> list:
        if self.device is None or not self.device.is_connected:
            self.is_connect = False
            return []

        try:
            positions = self.device.Get_joint_positions()
        except Exception:
            logging.exception("主手读取关节位置失败")
            self.is_connect = bool(self.device.is_connected)
            return []

        self.is_connect = bool(self.device.is_connected)
        return positions if positions is not None else []
