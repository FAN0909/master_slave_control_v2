from abc import abstractmethod

from .base_device import BaseDevice


class BaseRobotArm(BaseDevice):
    """Abstract base class for robot arm devices.

    This interface defines the common operations required by all robot arm
    implementations, including connection management, enable/disable control,
    state reading, and motion execution.
    """

    @abstractmethod
    def Enable(self) -> bool:
        """Enable the robot arm."""
        raise NotImplementedError

    @abstractmethod
    def Disable(self) -> bool:
        """Disable the robot arm."""
        raise NotImplementedError

    MAX_JOINT_COUNT: int = 0
    TCP_DIM: int = 0

    @abstractmethod
    def Get_joint_positions(self) -> list:
        """返回关节角度（度），长度为 MAX_JOINT_COUNT；失败返回 []。"""
        raise NotImplementedError

    @abstractmethod
    def Get_tcp_positions(self) -> list:
        """返回 [X, Y, Z, Rx, Ry, Rz]（毫米、度）；失败返回 []。"""
        raise NotImplementedError

    @abstractmethod
    def Move_j(
        self,
        target_positions: list,
        speed: float,
        acceleration: float,
        deceleration: float
    ) -> bool:
        """Move the robot arm in joint space."""
        raise NotImplementedError

    @abstractmethod
    def Move_l(
        self,
        target_positions: list,
        speed: float,
        acceleration: float,
        deceleration: float
    ) -> bool:
        """Move the robot arm in Cartesian space."""
        raise NotImplementedError

    supports_servoj = False

    def Open_servoJ(self) -> bool:
        """可选 ServoJ 能力，调用前检查 supports_servoj。"""
        return self._fail("设备不支持 ServoJ")

    def Close_servoJ(self) -> bool:
        return self._fail("设备不支持 ServoJ")

    def Set_servoJ_pos(self, target_positions: list) -> bool:
        """发送关节角度（度）；不支持或发送失败返回 False。"""
        return self._fail("设备不支持 ServoJ")
