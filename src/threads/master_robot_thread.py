"""Gello 主手工作对象：连接、断开、读取关节角度。"""

import logging
import math

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from src.devices.drivers_factory import create_master_arm
from src.log import Logger


class MasterRobotThread(QObject):
    sig_connection_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self.device = None
        self.is_connect = False
        self.logger = Logger.instance()

    @Slot(str, dict)
    def connect_device(self, model: str, options: dict) -> None:
        if self.Connect(model, options):
            self.logger.info(f"主手已连接：{model}，端口 {options.get('port', '')}")
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
