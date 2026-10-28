from abc import abstractmethod

from .base_device import BaseDevice


class BaseMasterArm(BaseDevice):
    """主手接口：连接、断开、读取关节为必选，使能与 TCP 为可选能力。"""

    supports_enable = False
    supports_tcp = False

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
