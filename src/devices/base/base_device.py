"""设备公共约定：命令返回 bool；读取失败返回空结果，详情见 last_error。

驱动实例由所属工作线程串行调用，不保证跨线程并发访问安全。
"""

import logging
import math
from abc import ABC, abstractmethod
from numbers import Real


class BaseDevice(ABC):
    def __init__(self, name: str):
        self.name = name
        self.is_connected = False
        self.is_enabled = False
        self.last_error = ""
        self.logger = logging.getLogger(f"{type(self).__module__}.{name}")

    @abstractmethod
    def Connect(self) -> bool:
        """连接设备；已连接时直接返回 True。"""
        raise NotImplementedError

    @abstractmethod
    def Disconnect(self) -> bool:
        """释放资源；未连接时也可调用，失败时返回 False。"""
        raise NotImplementedError

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
        """校验长度、有限实数以及驱动指定的数值范围。"""
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
