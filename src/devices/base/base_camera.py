from __future__ import annotations

from typing import TYPE_CHECKING
from abc import abstractmethod

from .base_device import BaseDevice

if TYPE_CHECKING:
    import numpy as np


class BaseCamera(BaseDevice):
    """彩色相机接口：连接、断开、设备枚举和非阻塞读取 BGR8 帧。"""

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
