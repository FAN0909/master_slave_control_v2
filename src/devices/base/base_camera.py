from abc import ABC, abstractmethod
import logging
import numpy as np
class BaseCamera(ABC):
    """Abstract base class for Camera devices.

    This interface defines the common operations required by all Camera
    implementations, including connection management,
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

    @abstractmethod
    def Connect(self) -> bool:
        """Connect to the camera."""
        pass

    @abstractmethod
    def Disconnect(self) -> bool:
        """Disconnect from the camera."""
        pass

    @abstractmethod
    def Get_color_frame(self) -> np.ndarray | None:
        """获取一帧 BGR8 彩色图像，形状为 (高, 宽, 3)。

        尚未连接或当前没有新帧时返回 None。
        """
        raise NotImplementedError

    @abstractmethod
    def list_devices(self) -> list[tuple[str, str]]:
        """Return available devices as (display name, device ID) pairs."""
        raise NotImplementedError
