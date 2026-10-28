from abc import ABC, abstractmethod


class BaseHand(ABC):
    """Abstract base class for Hand devices.

    This interface defines the common operations required by all Hand
    implementations, including connection management,
    """

    def __init__(self, name: str):
        self.name = name
        self.is_connected = False

    @abstractmethod
    def Connect(self) -> bool:
        """Connect to the robot arm and return the socket connection."""
        raise NotImplementedError

    @abstractmethod
    def Disconnect(self) -> bool:
        """Disconnect from the robot arm."""
        raise NotImplementedError

    @abstractmethod
    def Set_joint_positions(self, positions: list) -> bool:
        """Set the joint positions."""
        raise NotImplementedError

    @abstractmethod
    def Set_speed(self, speed: list[float]) -> bool:
        """Set the speed of the hand."""
        raise NotImplementedError

    @abstractmethod
    def Get_joint_positions(self) -> list:
        """get joints pos."""
        raise NotImplementedError

    @abstractmethod
    def Set_force(self, force: list) -> bool:
        """Set per-joint force values for configured hand actions."""
        raise NotImplementedError
