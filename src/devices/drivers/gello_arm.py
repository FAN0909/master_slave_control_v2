import json
import math
import subprocess
from pathlib import Path

from src.devices.base.base_masterArm import BaseMasterArm
from typing import Optional, Sequence

class GelloArm(BaseMasterArm):
    """被动主手，仅提供关节读数；将厂商 SDK 弧度转换为度。"""

    CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "master_arm.json"

    def __init__(
        self,
        name: str,
        ids: Optional[Sequence[int]] = None,
        servo_types: Optional[Sequence[str]] = None,
        port: str = "/dev/ttyUSB0",
        baudrate: int = 57600,
        max_retries: int = 3,
        use_fake_fallback: bool = False,
        config_path=None,
    ):
        super().__init__(name)
        self.config_path = Path(config_path) if config_path is not None else self.CONFIG_PATH
        self._load_config(ids)
        self.servo_types = servo_types
        self.port = port
        self.baudrate = baudrate
        self.max_retries = max_retries
        self.use_fake_fallback = use_fake_fallback

        self.dynamixel_driver = None
        self.is_connected = False
        self.is_enabled = False

    def _load_config(self, ids=None):
        """读取主手维度和默认舵机 ID，允许显式传入 ID。"""
        try:
            with self.config_path.open(encoding="utf-8") as file:
                config = json.load(file)["Gello"]
            joint_count = config["MAX_JOINT_COUNT"]
            tcp_dim = config["TCP_DIM"]
            if type(joint_count) is not int or joint_count <= 0:
                raise ValueError("MAX_JOINT_COUNT 必须是正整数")
            if type(tcp_dim) is not int or tcp_dim < 0:
                raise ValueError("TCP_DIM 必须是非负整数")
            joint_ids = list(config["IDS"] if ids is None else ids)
            if len(joint_ids) != joint_count:
                raise ValueError("IDS 数量必须与 MAX_JOINT_COUNT 一致")
            if any(type(value) is not int or not 0 <= value <= 252 for value in joint_ids):
                raise ValueError("IDS 必须是 0 到 252 之间的整数")
            if len(set(joint_ids)) != len(joint_ids):
                raise ValueError("IDS 不得重复")
            self.MAX_JOINT_COUNT = joint_count
            self.TCP_DIM = tcp_dim
            self.ids = joint_ids
        except (OSError, ValueError, KeyError, TypeError) as error:
            message = f"Gello 配置读取失败 ({self.config_path}): {error}"
            self._fail(message)
            raise ValueError(message) from error

    def Connect(self) -> bool:
        if self.is_connected:
            return True
        if self.dynamixel_driver is not None and not self.Disconnect():
            return False
        self.last_error = ""
        try:
            # The bundled driver kills processes that own its serial port.
            # Refuse the connection here before entering that SDK code.
            if not Path(self.port).exists():
                return self._fail(f"serial port does not exist: {self.port}")
            owner = subprocess.run(
                ["lsof", "-t", self.port], capture_output=True, text=True, check=False
            )
            if owner.stdout.strip():
                return self._fail(
                    f"serial port {self.port} is in use by PID(s): "
                    f"{', '.join(owner.stdout.split())}"
                )
            if owner.returncode not in (0, 1):
                return self._fail(f"cannot check serial port {self.port}: {owner.stderr.strip()}")
            # 这里的调用方式和底层库签名一致，参数名与 __init__ 一一对应
            from vendor.gello.dynamixel import DynamixelDriver

            self.dynamixel_driver = DynamixelDriver(
                ids=self.ids,
                servo_types=self.servo_types,
                port=self.port,
                baudrate=self.baudrate,
                max_retries=self.max_retries,
                use_fake_fallback=self.use_fake_fallback,
            )
            self.is_connected = True
            return True
        except Exception as error:
            self.is_connected = False
            return self._fail(f"connect failed: {error}")

    def Disconnect(self) -> bool:
        try:
            if self.dynamixel_driver is not None:
                self.dynamixel_driver.close()
            self.dynamixel_driver = None
            self.is_connected = False
            self.is_enabled = False
            self.last_error = ""
            return True
        except Exception as error:
            self.is_connected = False
            self.is_enabled = False
            return self._fail(f"disconnect failed: {error}")

    def Get_joint_positions(self) -> list:
        """将 SDK 弧度转换为度；读取失败或维度错误返回 []。"""
        if not self._ready():
            return []
        try:
            values = self._values(self.dynamixel_driver.get_joints(), self.MAX_JOINT_COUNT)
            return self._values([math.degrees(value) for value in values], self.MAX_JOINT_COUNT)
        except Exception as error:
            self._fail(f"get joint positions failed: {error}")
            return []
