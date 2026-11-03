"""灵巧手工作对象：连接、断开、读取关节与发送原生位置、速度、力矩。"""
import json
import logging
import math
from pathlib import Path
from PySide6.QtCore import QObject, QTimer, Signal, Slot
from src.devices.drivers_factory import create_hand
from src.log import Logger
from src.threads.joint_snapshot import JointSnapshot

class HandThread(QObject):
    FOLLOW_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "follow_params.json"
    HAND_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "hand_control.json"

    sig_connection_changed = Signal(bool)
    sig_joint_positions = Signal(list)

    def __init__(self, joint_snapshot: JointSnapshot | None = None):
        super().__init__()
        self.device = None
        self.is_connect = False
        self.joint_snapshot = joint_snapshot
        self._follow_generation: int | None = None
        self._master_seventh_start: float | None = None
        self._hand_actions: dict | None = None
        self._hand_state = "open"
        self.read_timer = QTimer(self)
        self.read_timer.timeout.connect(self.read_joint_pos)
        self.follow_timer = QTimer(self)
        self.follow_timer.timeout.connect(self.follow_move)

    @Slot(int)
    def start_follow_work(self, interval_ms: int) -> bool:
        if (not 0 < interval_ms <= 2_147_483_647 or not self.is_connect
                or self.device is None or self.joint_snapshot is None):
            return False
        sample = self.joint_snapshot.read()
        if (sample is None or len(sample.positions) < 7
                or not math.isfinite(sample.positions[6])):
            Logger.instance().error("没有有效的主手第七轴位置，无法开始灵巧手跟随")
            return False
        try:
            with self.FOLLOW_CONFIG_PATH.open(encoding="utf-8") as file:
                follow_config = json.load(file)
            close_delta = follow_config["HAND_CLOSE_DELTA_DEG"]
            open_delta = follow_config["HAND_OPEN_DELTA_DEG"]
            if (type(close_delta) not in (int, float) or not math.isfinite(close_delta)
                    or close_delta <= 0 or type(open_delta) not in (int, float)
                    or not math.isfinite(open_delta) or not 0 <= open_delta < close_delta):
                raise ValueError("灵巧手阈值必须满足 0 <= 开阈值 < 关阈值")
            with self.HAND_CONFIG_PATH.open(encoding="utf-8") as file:
                hand_config = json.load(file)[self.device.name]
            actions = {}
            for state, key in (("open", "current_open"), ("close", "current_close")):
                action = hand_config["actions"][hand_config[key]]
                positions = action["positions"]
                speed, force = action["speed"], action["force"]
                actions[state] = (positions, speed, force)
        except (OSError, ValueError, KeyError, TypeError) as error:
            Logger.instance().error(f"灵巧手跟随配置读取失败：{error}")
            return False
        self.stop_follow_work()
        self._close_delta = float(close_delta)
        self._open_delta = float(open_delta)
        self._hand_actions = actions
        self._master_seventh_start = sample.positions[6]
        self._follow_generation = sample.generation
        self._hand_state = "open"
        self.follow_timer.start(interval_ms)
        return True

    @Slot()
    def stop_follow_work(self) -> None:
        self.follow_timer.stop()
        self._follow_generation = None
        self._master_seventh_start = None
        self._hand_actions = None
        self._hand_state = "open"

    @Slot()
    def follow_move(self) -> None:
        if not self.follow_timer.isActive():
            return
        if self.device is None or not self.device.is_connected:
            self.stop_follow_work()
            return
        sample = self.joint_snapshot.read()
        if sample is None or sample.generation != self._follow_generation:
            self.stop_follow_work()
            return
        if len(sample.positions) < 7 or not math.isfinite(sample.positions[6]):
            return
        delta = abs(sample.positions[6] - self._master_seventh_start)
        new_state = self._hand_state
        if self._hand_state == "open" and delta >= self._close_delta:
            new_state = "close"
        elif self._hand_state == "close" and delta <= self._open_delta:
            new_state = "open"
        if new_state == self._hand_state:
            return
        positions, speed, force = self._hand_actions[new_state]
        if (not self.Set_speed([speed] * len(positions))
                or not self.Set_force([force] * len(positions))
                or not self.Set_joint_positions(positions)):
            Logger.instance().error(f"灵巧手跟随动作 {new_state} 发送失败")
            self.stop_follow_work()
            return
        self._hand_state = new_state

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
            self.stop_follow_work()
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
        self.stop_follow_work()
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

    @Slot(str, str, list, int, int)
    def test_action(self, model: str, name: str, positions: list,
                    speed: int, force: int) -> None:
        if (not self.is_connect or self.device is None
                or not self.device.is_connected or self.device.name != model):
            Logger.instance().error(f"无法测试动作 {name}：灵巧手未连接或型号已改变")
            return
        if not self.Set_speed([speed] * len(positions)):
            Logger.instance().error(f"测试动作 {name} 失败：设置速度失败")
            return
        if not self.Set_force([force] * len(positions)):
            Logger.instance().error(f"测试动作 {name} 失败：设置力度失败")
            return
        if not self.Set_joint_positions(positions):
            Logger.instance().error(f"测试动作 {name} 失败：发送关节位置失败")
            return
        Logger.instance().info(f"已发送灵巧手测试动作：{name}")
