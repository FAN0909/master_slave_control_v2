import json
import math
from pathlib import Path

from src.log import Logger
from src.devices.base.base_robotArm import BaseRobotArm

# NRC 的原生扩展依赖系统库；连接 NRC 时再加载，避免它阻断整个界面启动。
nrc_interface = None

class NrcArm(BaseRobotArm):

    CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "slave_arm.json"

    def __init__(
        self,
        name: str,
        ip_address: str = "192.168.2.14",
        command_port: int = 6001,
        servo_port: int = 7000,
    ):
        super().__init__(name)
        self._load_config(self.CONFIG_PATH)

        self.ip_address = ip_address
        self.command_port = command_port
        self.servo_port = servo_port

        self.servo_fd = None
        self.command_fd = None
        self.is_connected = False
        self.is_enabled = False

    def _load_config(self, path):
        """创建驱动和连接前读取配置，跟随循环不访问磁盘。"""
        try:
            with path.open(encoding="utf-8") as file:
                config = json.load(file)["NRC"]
            for key in ("JOINT_COUNT", "TCP_COUNT"):
                value = config[key]
                if type(value) is not int or value <= 0:
                    raise ValueError(f"{key} 必须是正整数")
                setattr(self, key, value)
            for key in ("JOINT_COORD", "TCP_COORD"):
                setattr(self, key, config[key])
            # 单位分别为 °/s、°/s²、°/s³。
            for key in ("SERVO_J_VMAX", "SERVO_J_AVMAX", "SERVO_J_JMAX"):
                value = config[key]
                if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                    raise ValueError(f"{key} 必须是有限的正数")
                setattr(self, key, float(value))
        except (OSError, ValueError, KeyError, TypeError) as error:
            message = f"NRC 配置读取失败 ({path}): {error}"
            Logger.instance().error(message)
            raise ValueError(message) from error

    #connect command_port and servo_port
    def Connect(self) -> bool:
        global nrc_interface
        try:
            if nrc_interface is None:
                from vendor.nrc import nrc_interface as sdk
                nrc_interface = sdk

            #连接前先加载配置文件  以后修改配置文件后重新连接即可生效
            self._load_config(self.CONFIG_PATH)
            Logger.instance().info(f"[{self.name}] connecting to {self.ip_address}:{self.command_port} and {self.servo_port}...")
            self.command_fd = nrc_interface.connect_robot(self.ip_address, str(self.command_port))
            if self.command_fd == -1:
                self.command_fd = None
                self.last_error = f"NRC 连接失败：命令端口 {self.command_port} 无法连接"
                Logger.instance().error(f"[{self.name}] {self.last_error}")
                self.is_connected = False
                return False
            self.servo_fd = nrc_interface.connect_robot(self.ip_address, str(self.servo_port))
            if self.servo_fd == -1:
                self.servo_fd = None
                self.Disconnect()
                self.last_error = f"NRC 连接失败：伺服端口 {self.servo_port} 无法连接"
                Logger.instance().error(f"[{self.name}] {self.last_error}")
                self.is_connected = False
                return False

            Logger.instance().info(f"[{self.name}] connected: {self.command_fd}")
            Logger.instance().info(f"[{self.name}] connected: {self.servo_fd}")
            self.is_connected = True
            return True
        except Exception as e:
            self.Disconnect()
            error = f"NRC 连接失败：{e}"
            Logger.instance().error(f"[{self.name}] {error}")
            self.is_connected = False
            return False

    def Disconnect(self) -> bool:
        success = True
        for fd_name in ("command_fd", "servo_fd"):
            fd = getattr(self, fd_name)
            if fd is None or fd == -1:
                setattr(self, fd_name, None)
                continue
            try:
                nrc_interface.disconnect_robot(fd)
                setattr(self, fd_name, None)
            except Exception as error:
                Logger.instance().error(f"[{self.name}] disconnect {fd_name} failed: {error}")
                success = False
        self.is_connected = False
        if success:
            Logger.instance().info(f"[{self.name}] disconnected")
        return success

    def Enable(self) -> bool:
        nrc_interface.set_servo_state(self.command_fd,1)
        res = nrc_interface.set_servo_poweron(self.command_fd)
        if res == 0:
            Logger.instance().info(f"[{self.name}] enable successful")
            self.is_enabled = True
        else:
            Logger.instance().error(f"[{self.name}] enable failed: {res}")
            self.is_enabled = False
        return self.is_enabled


    def Disable(self) -> bool:
        res = nrc_interface.set_servo_poweroff(self.command_fd)
        if res == 0:
            Logger.instance().info(f"[{self.name}] disable successful")
            self.is_enabled = False
        else:
            Logger.instance().error(f"[{self.name}] disable failed: {res}")
            self.is_enabled = True
        return not self.is_enabled

    def Get_joint_positions(self) -> list:
        try:
                output = nrc_interface.VectorDouble()
                output.resize(self.JOINT_COUNT)

                result = nrc_interface.get_current_position(
                    self.command_fd,
                    self.JOINT_COORD,
                    output
                )

                if result != 0:
                    Logger.instance().error(f"[{self.name}] get_current_position failed: {result}")
                    return []

                return [float(value) for value in output]

        except Exception as e:
                Logger.instance().error(f"[{self.name}] get_current_position error: {e}")
                return []

    def Get_tcp_positions(self) -> list:
        try:
                output = nrc_interface.VectorDouble()
                output.resize(self.TCP_COUNT)

                result = nrc_interface.get_current_position(
                    self.command_fd,
                    self.TCP_COORD,
                    output
                )

                if result != 0:
                    Logger.instance().error(f"[{self.name}] get_current_position failed: {result}")
                    return []

                return [float(value) for value in output][:self.TCP_COUNT]

        except Exception as e:
                Logger.instance().error(f"[{self.name}] get_current_position error: {e}")
                return []

    def Move_j(
        self,
        joint_positions: list,
        speed: float,
        acceleration: float,
        deceleration: float
    ) -> bool:

        # 1. 检查关节数量
        if len(joint_positions) < self.JOINT_COUNT-1:
            return False

        # 2. 创建 MoveJ 指令
        cmd = nrc_interface.MoveCmd()

        # 3. 设置运动参数
        cmd.acc = acceleration
        cmd.dec = deceleration
        cmd.velocity = speed
        cmd.coord = self.JOINT_COORD

        # 4. 设置目标位置
        cmd.targetPosValue.resize(self.JOINT_COUNT)

        for i, position in enumerate(joint_positions):
            cmd.targetPosValue[i] = position

        # 5. 发送指令
        result = nrc_interface.robot_movej(
            self.command_fd,
            cmd
        )

        # 6. 返回执行结果
        return result == 0

    def Move_l(
        self,
        tcp_positions: list,
        speed: float,
        acceleration: float,
        deceleration: float
    ) -> bool:

        if not self.is_connected:
            return False

        # TCP 点位应该包含 6 个值： 纳博特要写7个 第七个写0就行
        # X, Y, Z, Rx, Ry, Rz
        if len(tcp_positions) < self.TCP_COUNT-1:
            return False

        cmd = nrc_interface.MoveCmd()

        # 设置运动参数
        cmd.velocity = float(speed)
        cmd.acc = float(acceleration)
        cmd.dec = float(deceleration)

        # 设置坐标系
        cmd.coord = self.TCP_COORD

        # 设置目标位置
        cmd.targetPosValue.resize(self.TCP_COUNT)

        for i, position in enumerate(tcp_positions):
            cmd.targetPosValue[i] = float(position)

        # 其余位置补 0 
        for i in range(len(tcp_positions), self.TCP_COUNT):
            cmd.targetPosValue[i] = 0.0

        # 调用 SDK
        result = nrc_interface.robot_movel(
            self.command_fd,
            cmd,
        )

        return result == 0

        #endregion

    #servo control 7000 port
    def Open_servoJ(self) -> bool:

        if self.servo_fd is None or self.servo_fd == -1:
            Logger.instance().error(f"[{self.name}] open_servoJ failed: invalid servo_fd")
            return False

        try:

            # servoJ 约束
            vMax  = nrc_interface.VectorDouble([self.SERVO_J_VMAX]  * self.JOINT_COUNT)
            avMax = nrc_interface.VectorDouble([self.SERVO_J_AVMAX] * self.JOINT_COUNT)
            jMax  = nrc_interface.VectorDouble([self.SERVO_J_JMAX]  * self.JOINT_COUNT)

            result = nrc_interface.open_servoJ(
                self.servo_fd, vMax, avMax, jMax
            )

            if result == 0:
                Logger.instance().info(f"[{self.name}] servo J opened successfully")
                return True
            else:
                Logger.instance().error(f"[{self.name}] failed to open servo J: {result}")
                return False

        except Exception as e:
            Logger.instance().error(f"[{self.name}] open_servoJ error: {e}")
            return False

    def Close_servoJ(self) -> bool:

        if self.servo_fd is None or self.servo_fd == -1:
            Logger.instance().error(f"[{self.name}] close_servoJ failed: invalid servo_fd")
            return False

        try:

            result = nrc_interface.stop_servoJ(self.servo_fd)
            if result == 0:

                return True
            else:
                return False
        except Exception as e:
            Logger.instance().error(f"[{self.name}] close_servoJ error: {e}")
            return False

    #目标关节角（度），长度必须 ≥ 7；是目标绝对位置，不是增量
    def Set_servoJ_pos(self, target_positions: list) -> bool:
        if self.servo_fd is None or self.servo_fd == -1:
            Logger.instance().error(f"[{self.name}] set_servoJ_pos failed: invalid servo_fd")
            return False

        if len(target_positions) < self.JOINT_COUNT:
            Logger.instance().error(f"[{self.name}] 目标关节数量不匹配")
            return False

        try:
            pos = nrc_interface.VectorDouble()
            pos.resize(self.JOINT_COUNT)
            for i, v in enumerate(target_positions):
                pos[i] = float(v)

            result = nrc_interface.set_servoJ_pos(self.servo_fd, pos)
            return result == 0

        except Exception as e:
            Logger.instance().error(f"[{self.name}] set_servoJ_pos error: {e}")
            return False

        #endregion
