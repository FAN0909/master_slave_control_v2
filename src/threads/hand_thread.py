"""灵巧手工作对象：连接、断开、读取关节与发送原生位置、速度、力矩。"""
import logging
import math
from PySide6.QtCore import QObject, QTimer, Signal, Slot
from src.devices.drivers_factory import create_hand
from src.log import Logger

class HandThread(QObject):
    sig_connection_changed = Signal(bool)
    sig_joint_positions = Signal(list)

    def __init__(self):
        super().__init__()
        self.device = None
        self.is_connect = False
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
            Logger.instance().info(f"灵巧手已连接：{model}，{options['comm_info']}")
            self.start_timer_work(interval_ms)
        self.sig_connection_changed.emit(self.is_connect)

    @Slot()
    def disconnect_device(self) -> None:
        if self.device is not None:
            if self.Disconnect():
                Logger.instance().info("灵巧手已断开")
            else:
                Logger.instance().error("灵巧手断开失败")
        self.sig_connection_changed.emit(self.is_connect)


    def Connect(self, model: str, options: dict) -> bool:
        if self.device is not None:
            try:
                if not self.device.Disconnect():
                    Logger.instance().error("已有灵巧手断开失败，无法连接新设备")
                    return False
            except Exception as error:
                Logger.instance().error(f"已有灵巧手断开失败：{error}")
                return False
            self.device = None
            self.is_connect = False

        try:
            self.device = self._create_device(model, **options)
            if self.device.Connect():
                self.is_connect = True
                return True
        except (Exception, SystemExit) as error:
            Logger.instance().error(f"灵巧手连接失败：{error}")

        if self.device is not None:
            try:
                if self.device.Disconnect():
                    self.device = None
            except Exception:
                logging.exception("灵巧手连接失败后的清理失败：%s", model)
        self.is_connect = False
        return False


    @Slot()
    def Disconnect(self) -> bool:
        self.stop_timer_work()
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
