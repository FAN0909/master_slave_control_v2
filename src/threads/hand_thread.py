"""灵巧手工作对象：连接、断开、读取关节与发送原生位置、速度、力矩。"""
import logging
import math
from PySide6.QtCore import QObject, QTimer, Signal, Slot
from src.devices.drivers_factory import create_hand

class HandThread(QObject):

    def __init__(self):
        super().__init__()
        self.device = None
        self.is_connect = False


    def Connect(self, model: str, options: dict) -> bool:
        if self.device is not None:
            try:
                if not self.device.Disconnect():
                    logging.error("已有灵巧手断开失败，无法连接新设备")
                    return False
            except Exception:
                logging.exception("已有灵巧手断开失败，无法连接新设备")
                return False
            self.device = None
            self.is_connect = False

        try:
            self.device = self._create_device(model, **options)
            if self.device.Connect():
                self.is_connect = True
                return True
        except Exception:
            logging.exception("灵巧手连接失败：%s", model)

        if self.device is not None:
            try:
                if self.device.Disconnect():
                    self.device = None
            except Exception:
                logging.exception("灵巧手连接失败后的清理失败：%s", model)
        self.is_connect = False
        return False


    def Disconnect(self) -> bool:
        if self.device is None:
            return False

        try:
            if not self.device.Disconnect():
                logging.error("灵巧手断开失败")
                return False
        except Exception:
            logging.exception("灵巧手断开失败")
            return False

        self.device = None
        self.is_connect = False
        return True

    def _create_device(self, model: str, **options):
        return create_hand(model, **options)


    def Get_joint_positions(self) -> list:
        if self.device is None or not self.device.is_connected:
            self.is_connect = False
            return []

        try:
            positions = self.device.Get_joint_positions()
        except Exception:
            logging.exception("灵巧手读取关节位置失败")
            self.is_connect = bool(self.device.is_connected)
            return []

        self.is_connect = bool(self.device.is_connected)
        return positions if positions is not None else []


    def _set_values(self, method: str, values: list) -> bool:
        if self.device is None or not self.device.is_connected:
            self.is_connect = False
            return False

        try:
            success = bool(getattr(self.device, method)(values))
        except Exception:
            logging.exception("灵巧手执行 %s 失败", method)
            success = False

        self.is_connect = bool(self.device.is_connected)
        return success

    def Set_joint_positions(self, positions: list) -> bool:
        return self._set_values("Set_joint_positions", positions)

    def Set_speed(self, speed: list) -> bool:
        return self._set_values("Set_speed", speed)

    def Set_force(self, force: list) -> bool:
        return self._set_values("Set_force", force)
