from abc import abstractmethod

from .base_device import BaseDevice


class BaseHand(BaseDevice):
    """灵巧手接口；数值单位和通道数量由具体驱动说明。"""

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
