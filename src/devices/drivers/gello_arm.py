import json
import math
from pathlib import Path
from typing import Optional, Sequence

from src.devices.base.base_masterArm import BaseMasterArm
from src.log import Logger
from vendor.gello.dynamixel import DynamixelDriver


class GelloArm(BaseMasterArm):
    CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "master_arm.json"

    def __init__(
        self,
        name: str,
        servo_types: Optional[Sequence[str]] = None,
        port: str = "/dev/ttyUSB0",
        baudrate: int = 57600,
        max_retries: int = 3,
        use_fake_fallback: bool = False,
    ):
        super().__init__(name)
        self._load_config()
        self.servo_types = servo_types
        self.port = port
        self.baudrate = baudrate
        self.max_retries = max_retries
        self.use_fake_fallback = use_fake_fallback

        self.dynamixel_driver = None

    def _load_config(self):
        """从配置文件读取主手维度和舵机 ID。"""
        try:
            with self.CONFIG_PATH.open(encoding="utf-8") as file:
                config = json.load(file)["Gello"]
            joint_count = config["MAX_JOINT_COUNT"]
            tcp_dim = config["TCP_DIM"]
            if type(joint_count) is not int or joint_count <= 0:
                raise ValueError("MAX_JOINT_COUNT 必须是正整数")
            if type(tcp_dim) is not int or tcp_dim < 0:
                raise ValueError("TCP_DIM 必须是非负整数")
            joint_ids = list(config["IDS"])
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
            message = f"Gello 配置读取失败 ({self.CONFIG_PATH}): {error}"
            Logger.instance().error(message)
            raise ValueError(message) from error

    def Connect(self) -> bool:
        if self.dynamixel_driver is not None:
            self.is_connected = True
            return True

        try:
            # 断开后重新连接时读取最新配置。
            self._load_config()
            # 配置中的舵机 ID 与连接参数传给底层驱动。
            driver = DynamixelDriver(
                ids=self.ids,
                servo_types=self.servo_types,
                port=self.port,
                baudrate=self.baudrate,
                max_retries=self.max_retries,
                use_fake_fallback=self.use_fake_fallback,
            )
            self.dynamixel_driver = driver
            self.is_connected = True
            return True
        except Exception as e:
            Logger.instance().error(f"[{self.name}] connect failed: {e}")
            self.dynamixel_driver = None
            self.is_connected = False
            return False

    def Disconnect(self) -> bool:
        if self.dynamixel_driver is not None:
            try:
                self.dynamixel_driver.close()
            except Exception as error:
                Logger.instance().warning(f"[{self.name}] close failed: {error}")

        self.dynamixel_driver = None
        self.is_connected = False
        self.is_enabled = False
        Logger.instance().info(f"[{self.name}] disconnected")
        return True

    def Get_joint_positions(self) -> list:
        try:
            if not self.is_connected or self.dynamixel_driver is None:
                return []

            pos = self.dynamixel_driver.get_joints()
            if pos is None:
                raise ValueError("Dynamixel driver returned no joint positions")

            values = [float(value) for value in pos]
            if len(values) != self.MAX_JOINT_COUNT:
                raise ValueError(
                    f"expected {self.MAX_JOINT_COUNT} joints, received {len(values)}"
                )
            if not all(math.isfinite(value) for value in values):
                raise ValueError("joint positions contain non-finite values")

            joint_degrees = [math.degrees(value) for value in values]
            if not all(math.isfinite(value) for value in joint_degrees):
                raise ValueError("converted joint positions contain non-finite values")
            return joint_degrees

        except Exception as e:
            Logger.instance().error(f"[{self.name}] get_joint_positions failed: {e}")
            return []


    def Enable(self) -> bool:
        raise NotImplementedError(
            f"[{self.name}] Gello does not support Enable"
        )

    def Disable(self) -> bool:
        raise NotImplementedError(
            f"[{self.name}] Gello does not support Disable"
        )

    def Get_tcp_positions(self) -> list:
        raise NotImplementedError(
            f"[{self.name}] Gello does not provide TCP positions"
        )
