import json
import math
from pathlib import Path

from src.devices.base.base_robotArm import BaseRobotArm

# 延迟加载原生扩展，使未使用 NRC 的项目也能导入设备模块。
nrc_interface = None


class NrcArm(BaseRobotArm):
    """NRC 从臂：关节角度为度，TCP 平移为毫米、旋转为度。"""

    CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "slave_arm.json"
    supports_servoj = True

    def __init__(self, name: str, ip_address: str = "192.168.2.14",
                 command_port: int = 6001, servo_port: int = 7000, config_path=None):
        super().__init__(name)
        self.config_path = Path(config_path) if config_path is not None else self.CONFIG_PATH
        self._load_config(self.config_path)
        self.ip_address = ip_address
        self.command_port = command_port
        self.servo_port = servo_port
        self.command_fd = None
        self.servo_fd = None
        self.is_servoj_open = False

    def _load_config(self, path):
        try:
            with path.open(encoding="utf-8") as file:
                config = json.load(file)["NRC"]
            for key in ("MAX_JOINT_COUNT", "TCP_DIM"):
                value = config[key]
                if type(value) is not int or value <= 0:
                    raise ValueError(f"{key} 必须是正整数")
                setattr(self, key, value)
            if self.TCP_DIM != 6 or self.MAX_JOINT_COUNT < self.TCP_DIM:
                raise ValueError("NRC 要求 TCP_DIM 为 6，MAX_JOINT_COUNT 不小于 6")
            for key in ("JOINT_COORD", "TCP_COORD"):
                value = config[key]
                if type(value) is not int:
                    raise ValueError(f"{key} 必须是整数")
                setattr(self, key, value)
            for key in ("SERVO_J_VMAX", "SERVO_J_AVMAX", "SERVO_J_JMAX"):
                value = config[key]
                if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                    raise ValueError(f"{key} 必须是有限正数")
                setattr(self, key, float(value))
        except (OSError, ValueError, KeyError, TypeError) as error:
            message = f"NRC 配置读取失败 ({path}): {error}"
            self._fail(message)
            raise ValueError(message) from error

    def Connect(self) -> bool:
        global nrc_interface
        if self.is_connected:
            return True
        # 上次释放失败时保留句柄，必须先成功释放才能重新连接。
        if not self.Disconnect():
            return False
        self.last_error = ""
        try:
            if nrc_interface is None:
                from vendor.nrc import nrc_interface as sdk
                nrc_interface = sdk
            self._load_config(self.config_path)
            for field, port in (("command_fd", self.command_port), ("servo_fd", self.servo_port)):
                fd = nrc_interface.connect_robot(self.ip_address, str(port))
                if fd is None or fd < 0:
                    raise RuntimeError(f"端口 {port} 连接失败")
                setattr(self, field, fd)
            self.is_connected = True
            return True
        except Exception as error:
            message = f"连接失败：{error}"
            if not self.Disconnect():
                message += f"；资源释放失败：{self.last_error}"
            return self._fail(message)

    def Disconnect(self) -> bool:
        errors = []
        if self.is_servoj_open and not self.Close_servoJ():
            errors.append(self.last_error)
        for field in ("servo_fd", "command_fd"):
            fd = getattr(self, field)
            if fd is None:
                continue
            try:
                result = nrc_interface.disconnect_robot(fd)
                if result is not None and result != 0:
                    raise RuntimeError(f"SDK 返回 {result}")
                setattr(self, field, None)
            except Exception as error:
                errors.append(f"释放 {field} 失败：{error}")
        self.is_connected = False
        self.is_enabled = False
        if self.servo_fd is None:
            self.is_servoj_open = False
        if errors:
            return self._fail("；".join(errors))
        self.last_error = ""
        return True

    def _command(self, operation, *args) -> bool:
        try:
            result = operation(*args)
            if result != 0:
                operation_name = getattr(operation, "__name__", type(operation).__name__)
                return self._fail(f"{operation_name} 失败：{result}")
            self.last_error = ""
            return True
        except Exception as error:
            return self._fail(str(error))

    def Enable(self) -> bool:
        if not self._ready():
            return False
        if not self._command(nrc_interface.set_servo_state, self.command_fd, 1):
            return False
        if not self._command(nrc_interface.set_servo_poweron, self.command_fd):
            return False
        self.is_enabled = True
        return True

    def Disable(self) -> bool:
        if not self._ready():
            return False
        if not self._command(nrc_interface.set_servo_poweroff, self.command_fd):
            return False
        self.is_enabled = False
        self.is_servoj_open = False
        return True

    def _read_positions(self, coord: int, count: int) -> list:
        if not self._ready():
            return []
        try:
            output = nrc_interface.VectorDouble()
            output.resize(self.MAX_JOINT_COUNT)
            result = nrc_interface.get_current_position(self.command_fd, coord, output)
            if result != 0:
                raise RuntimeError(f"读取位置失败：{result}")
            return self._values(list(output)[:count], count)
        except Exception as error:
            self._fail(str(error))
            return []

    def Get_joint_positions(self) -> list:
        return self._read_positions(self.JOINT_COORD, self.MAX_JOINT_COUNT)

    def Get_tcp_positions(self) -> list:
        return self._read_positions(self.TCP_COORD, self.TCP_DIM)

    def _move(self, target_positions, speed, acceleration, deceleration, *, linear) -> bool:
        if not self._ready():
            return False
        try:
            count = self.TCP_DIM if linear else self.MAX_JOINT_COUNT
            positions = self._values(target_positions, count)
            motion = self._values([speed, acceleration, deceleration], 3)
            if any(value <= 0 for value in motion):
                raise ValueError("速度、加速度和减速度必须为正数")
            cmd = nrc_interface.MoveCmd()
            cmd.velocity, cmd.acc, cmd.dec = motion
            cmd.coord = self.TCP_COORD if linear else self.JOINT_COORD
            cmd.targetPosValue.resize(self.MAX_JOINT_COUNT)
            for i in range(self.MAX_JOINT_COUNT):
                cmd.targetPosValue[i] = positions[i] if i < count else 0.0
            operation = nrc_interface.robot_movel if linear else nrc_interface.robot_movej
            return self._command(operation, self.command_fd, cmd)
        except Exception as error:
            return self._fail(str(error))

    def Move_j(self, target_positions: list, speed: float,
               acceleration: float, deceleration: float) -> bool:
        return self._move(target_positions, speed, acceleration, deceleration, linear=False)

    def Move_l(self, target_positions: list, speed: float,
               acceleration: float, deceleration: float) -> bool:
        return self._move(target_positions, speed, acceleration, deceleration, linear=True)

    def Open_servoJ(self) -> bool:
        if not self._ready():
            return False
        if self.is_servoj_open:
            return True
        try:
            limits = [nrc_interface.VectorDouble([limit] * self.MAX_JOINT_COUNT)
                      for limit in (self.SERVO_J_VMAX, self.SERVO_J_AVMAX, self.SERVO_J_JMAX)]
            if not self._command(nrc_interface.open_servoJ, self.servo_fd, *limits):
                return False
            self.is_servoj_open = True
            return True
        except Exception as error:
            return self._fail(str(error))

    def Close_servoJ(self) -> bool:
        if not self.is_servoj_open:
            self.last_error = ""
            return True
        if self.servo_fd is None:
            return self._fail("伺服端口未连接")
        if not self._command(nrc_interface.stop_servoJ, self.servo_fd):
            return False
        self.is_servoj_open = False
        return True

    def Set_servoJ_pos(self, target_positions: list) -> bool:
        if not self._ready():
            return False
        if not self.is_servoj_open:
            return self._fail("ServoJ 尚未打开")
        try:
            values = self._values(target_positions, self.MAX_JOINT_COUNT)
            return self._command(nrc_interface.set_servoJ_pos, self.servo_fd,
                                 nrc_interface.VectorDouble(values))
        except Exception as error:
            return self._fail(str(error))
