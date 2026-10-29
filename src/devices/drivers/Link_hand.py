import math

from src.devices.base.base_hand import BaseHand
from src.log import Logger
from vendor.linkerhand_python_sdk.LinkerHand.linker_hand_api import LinkerHandApi


class LinkHand(BaseHand):
    SPEED_LENGTHS = {
        "O6": (6,), "L6": (6,), "L7": (7,), "L10": (5, 10),
        "L20": (5,), "G20": (5,), "L21": (5, 25), "L25": (5, 25),
    }
    FORCE_LENGTHS = {
        "O6": (6,), "L6": (6,), "L7": (7,), "L10": (5, 10),
        "G20": (5,), "L21": (5,), "L25": (5,),
    }

    def __init__(self, name: str, hand_type="left", hand_joint="O6", modbus="None",
                 can="can0", comm_type=None, comm_info=None):
        super().__init__(name)
        self.hand_type = {
            "Right Hand": "right",
            "Left Hand": "left",
        }.get(hand_type, hand_type)
        self.hand_joint = hand_joint
        if comm_type is not None:
            communication = comm_type.strip().lower()
            if communication in ("modbus", "modebus"):
                modbus, can = comm_info, "None"
            elif communication == "can":
                modbus, can = "None", comm_info
            else:
                raise ValueError(f"不支持的灵巧手通信方式：{comm_type}")
        self.modbus = modbus
        self.can = can
        self.is_connected = False
        self.hand_api = None  # Placeholder for the actual hand API instance

    @property
    def MAX_JOINTS(self) -> int:
        mapping = {
            "O6": 6, "L6": 6, "L7": 7, "L10": 10,
            "L20": 20, "G20": 20, "L21": 25, "L25": 25
        }
        return mapping.get(self.hand_joint.upper(), 0)

    def Connect(self) -> bool:
        # Implement the connection logic for LinkHandO6
        # For example, establish a serial connection or network connection
        try:
            if self.hand_api is None:
                self.hand_api = LinkerHandApi(hand_type=self.hand_type, hand_joint=self.hand_joint, modbus=self.modbus, can=self.can)

            self.is_connected = True
            return True
        except Exception as e:
            Logger.instance().error(f"[{self.name}] connect failed: {e}")
            self.is_connected = False
            return False

    def Disconnect(self) -> bool:
        try:
            if self.hand_api is not None:
                backend = self.hand_api.hand
                # SDK close_can() references an undefined `modbus` variable.
                # Close the actual transport, including its CAN receive thread.
                if hasattr(backend, "close_can_interface"):
                    backend.close_can_interface()
                else:
                    backend.close()
                self.hand_api = None
            self.is_connected = False
            Logger.instance().info(f"[{self.name}] disconnected")
            return True
        except Exception as e:
            Logger.instance().error(f"[{self.name}] disconnect failed: {e}")
            return False

    def Set_joint_positions(self, positions: list) -> bool:
        # Implement the logic to set joint positions for LinkHandO6
        try:
            if self.hand_api is None:
                Logger.instance().error(f"[{self.name}] hand API not connected")
                return False

            max_joints = self.MAX_JOINTS
            if max_joints <= 0:
                Logger.instance().error(f"[{self.name}] unsupported joint type: {self.hand_joint}")
                return False

            pos = [int(p) for p in positions]
            if len(pos) != max_joints:
                Logger.instance().error(
                    f"[{self.name}] joint count mismatch: expected {max_joints}, got {len(pos)}"
                )
                return False

            self.hand_api.finger_move(pos)
            return True
        except Exception as e:
            Logger.instance().error(f"[{self.name}] set joint positions failed: {e}")
            return False

    def Get_joint_positions(self) -> list:
        """读取灵巧手当前关节位置；读取失败时返回空列表。"""
        if not self.is_connected or self.hand_api is None:
            Logger.instance().error(f"[{self.name}] hand API not connected")
            return []

        try:
            positions = self.hand_api.get_state()
            if positions is None:
                raise ValueError("SDK returned no joint positions")
            joint_positions = [float(value) for value in positions]
            if len(joint_positions) != self.MAX_JOINTS or not all(
                math.isfinite(value) for value in joint_positions
            ):
                raise ValueError(f"invalid joint positions: {joint_positions}")
            return joint_positions
        except Exception as error:
            Logger.instance().error(f"[{self.name}] get joint positions failed: {error}")
            return []

    @staticmethod
    def _valid_channel_values(values: list, lengths: tuple[int, ...]) -> bool:
        return (
            isinstance(values, list)
            and len(values) in lengths
            and all(
                type(value) in (int, float)
                and math.isfinite(value)
                and 0 <= value <= 255
                and value == int(value)
                for value in values
            )
        )

    def Set_speed(self, speed: list) -> bool:
        if not self.is_connected or self.hand_api is None:
            Logger.instance().error(f"[{self.name}] hand API not connected")
            return False
        joint_type = self.hand_joint.upper()
        lengths = self.SPEED_LENGTHS.get(joint_type, ())
        if joint_type == "L10" and self.modbus != "None":
            lengths = (10,)
        if not self._valid_channel_values(speed, lengths):
            Logger.instance().error(f"[{self.name}] invalid speed values for {joint_type}: {speed}")
            return False

        try:
            return self.hand_api.set_speed([int(value) for value in speed]) is not False
        except Exception as e:
            Logger.instance().error(f"[{self.name}] set speed failed: {e}")
            return False

    def Set_force(self, force: list) -> bool:
        if not self.is_connected or self.hand_api is None:
            Logger.instance().error(f"[{self.name}] hand API not connected")
            return False
        joint_type = self.hand_joint.upper()
        lengths = self.FORCE_LENGTHS.get(joint_type, ())
        if not lengths:
            Logger.instance().error(f"[{self.name}] force control is not supported for {joint_type}")
            return False
        if joint_type == "L10" and self.modbus != "None":
            lengths = (10,)
        if not self._valid_channel_values(force, lengths):
            Logger.instance().error(f"[{self.name}] invalid force values for {joint_type}: {force}")
            return False

        try:
            return self.hand_api.set_torque([int(value) for value in force]) is not False
        except Exception as error:
            Logger.instance().error(f"[{self.name}] set force failed: {error}")
            return False
