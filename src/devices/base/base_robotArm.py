import logging
import math
from abc import ABC, abstractmethod
from numbers import Real


class BaseRobotArm(ABC):
    """Abstract base class for robot arm devices.

    This interface defines the common operations required by all robot arm
    implementations, including connection management, enable/disable control,
    state reading, and motion execution.
    """

    def __init__(self, name: str):
        self.name = name
        self.is_connected = False
        self.is_enabled = False
        self.last_error = ""
        self.logger = logging.getLogger(f"{type(self).__module__}.{name}")

    def _fail(self, message: str) -> bool:
        self.last_error = str(message)
        self.logger.error("[%s] %s", self.name, self.last_error)
        return False

    def _ready(self) -> bool:
        if not self.is_connected:
            return self._fail("设备未连接")
        self.last_error = ""
        return True

    @staticmethod
    def _values(values, count: int, *, minimum=None, maximum=None) -> list[float]:
        result = list(values)
        if count <= 0 or len(result) != count:
            raise ValueError(f"需要 {count} 个数值，实际为 {len(result)} 个")
        for value in result:
            if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
                raise ValueError("数据必须为有限实数")
            if minimum is not None and value < minimum:
                raise ValueError(f"数据不得小于 {minimum}")
            if maximum is not None and value > maximum:
                raise ValueError(f"数据不得大于 {maximum}")
        return [float(value) for value in result]

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
