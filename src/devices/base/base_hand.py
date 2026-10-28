import logging
import math
from abc import ABC, abstractmethod
from numbers import Real


class BaseHand(ABC):
    """灵巧手接口；数值单位和通道数量由具体驱动说明。"""

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
    def Set_joint_positions(self, positions: list) -> bool:
        """Set the joint positions."""
        raise NotImplementedError

    @abstractmethod
    def Set_speed(self, speed: list[float]) -> bool:
        """设置驱动定义的各通道速度；通道数量与取值范围由具体驱动说明。"""
        raise NotImplementedError

    @abstractmethod
    def Get_joint_positions(self) -> list:
        """返回设备原生关节位置，单位由驱动说明；失败返回 []。"""
        raise NotImplementedError

    @abstractmethod
    def MAX_JOINTS(self) -> int:
        """Return the number of controllable hand joints."""
        raise NotImplementedError

    @abstractmethod
    def Set_force(self, force: list) -> bool:
        """Set per-joint force values for configured hand actions."""
        raise NotImplementedError
