import logging
import math
from abc import ABC, abstractmethod
from numbers import Real


class BaseMasterArm(ABC):
    """主手接口：连接、断开、读取关节为必选，使能与 TCP 为可选能力。"""

    supports_enable = False
    supports_tcp = False

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

    def Enable(self) -> bool:
        """可选能力；不支持时返回 False。"""
        return self._fail("设备不支持使能")

    def Disable(self) -> bool:
        return self._fail("设备不支持去使能")

    MAX_JOINT_COUNT: int = 0
    TCP_DIM: int = 0

    @abstractmethod
    def Get_joint_positions(self) -> list:
        """返回关节角度（度），长度为 MAX_JOINT_COUNT；失败返回 []。"""
        raise NotImplementedError

    def Get_tcp_positions(self) -> list:
        """可选 TCP 能力；不支持时返回 []，调用前检查 supports_tcp。"""
        self._fail("设备不提供 TCP 位姿")
        return []
