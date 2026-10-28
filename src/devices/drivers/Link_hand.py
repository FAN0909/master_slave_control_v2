from src.devices.base.base_hand import BaseHand


class LinkHand(BaseHand):
    """LinkerHand：位置、速度、力矩限制均为 SDK 的 0～255 原生值。

    positions/force 长度为 MAX_JOINTS；speed 按 SDK 的速度通道传入列表。
    O6/L6 为 6 通道，L7 为 7 通道，其余型号至少 5 通道。
    命令返回 True 表示通过校验且已提交 SDK，不表示设备已经运动到位。
    """

    JOINT_COUNTS = {"O6": 6, "L6": 6, "L7": 7, "L10": 10,
                    "L20": 20, "G20": 20, "L21": 25, "L25": 25}

    def __init__(self, name: str, hand_type="left", hand_joint="O6", modbus="None",
                 can="can0", comm_type=None, comm_info=None):
        super().__init__(name)
        self.hand_type = {"Right Hand": "right", "Left Hand": "left"}.get(hand_type, hand_type)
        if self.hand_type not in ("left", "right"):
            raise ValueError(f"不支持的手侧：{hand_type}")
        self.hand_joint = hand_joint.upper()
        if self.hand_joint not in self.JOINT_COUNTS:
            raise ValueError(f"不支持的灵巧手型号：{hand_joint}")
        if comm_type is not None:
            communication = comm_type.strip().lower()
            if not comm_info:
                raise ValueError("通信端口不能为空")
            if communication in ("modbus", "modebus"):
                modbus, can = comm_info, "None"
            elif communication == "can":
                modbus, can = "None", comm_info
            else:
                raise ValueError(f"不支持的灵巧手通信方式：{comm_type}")
        self.modbus = modbus
        self.can = can
        self.hand_api = None

    def MAX_JOINTS(self) -> int:
        return self.JOINT_COUNTS[self.hand_joint]

    def Connect(self) -> bool:
        if self.is_connected:
            return True
        if self.hand_api is not None and not self.Disconnect():
            return False
        self.last_error = ""
        try:
            from vendor.linkerhand_python_sdk.LinkerHand.linker_hand_api import LinkerHandApi

            self.hand_api = LinkerHandApi(hand_type=self.hand_type, hand_joint=self.hand_joint,
                                          modbus=self.modbus, can=self.can)
            self.is_connected = True
            return True
        except (Exception, SystemExit) as error:
            # 厂商 SDK 连接失败可能调用 sys.exit；不得导致整个 GUI 退出。
            self.is_connected = False
            return self._fail(f"connect failed: {error}")

    def Disconnect(self) -> bool:
        try:
            if self.hand_api is not None:
                backend = self.hand_api.hand
                # SDK close_can() 引用了未定义变量，直接关闭实际传输。
                if hasattr(backend, "close_can_interface"):
                    backend.close_can_interface()
                else:
                    backend.close()
                self.hand_api = None
            self.is_connected = False
            self.is_enabled = False
            self.last_error = ""
            return True
        except Exception as error:
            self.is_connected = False
            self.is_enabled = False
            return self._fail(f"disconnect failed: {error}")

    def _send(self, method: str, values, count: int) -> bool:
        if not self._ready():
            return False
        try:
            values = self._values(values, count, minimum=0, maximum=255)
            result = getattr(self.hand_api, method)([int(value) for value in values])
            if result is False:
                return self._fail(f"{method} 被 SDK 拒绝")
            return True
        except Exception as error:
            return self._fail(f"{method} failed: {error}")

    def Set_joint_positions(self, positions: list) -> bool:
        return self._send("finger_move", positions, self.MAX_JOINTS())

    def Get_joint_positions(self) -> list:
        if not self._ready():
            return []
        try:
            return self._values(self.hand_api.get_state(), self.MAX_JOINTS(), minimum=0, maximum=255)
        except Exception as error:
            self._fail(f"get joint positions failed: {error}")
            return []

    def Set_speed(self, speed: list[float]) -> bool:
        try:
            values = list(speed)
            count = 6 if self.hand_joint in ("O6", "L6") else 7 if self.hand_joint == "L7" else len(values)
            if len(values) < 5:
                return self._fail("速度至少需要 5 个通道")
            return self._send("set_speed", values, count)
        except (TypeError, ValueError) as error:
            return self._fail(f"invalid speed: {error}")

    def Set_force(self, force: list) -> bool:
        return self._send("set_torque", force, self.MAX_JOINTS())
