from abc import ABC, abstractmethod


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

    @abstractmethod
    def Connect(self) -> bool:
        """Connect to the robot arm and return the socket connection."""
        raise NotImplementedError

    @abstractmethod
    def Disconnect(self) -> bool:
        """Disconnect from the robot arm."""
        raise NotImplementedError

    @abstractmethod
    def Enable(self) -> bool:
        """Enable the robot arm."""
        raise NotImplementedError

    @abstractmethod
    def Disable(self) -> bool:
        """Disable the robot arm."""
        raise NotImplementedError

    @abstractmethod
    def Get_joint_positions(self) -> list:
        """Read the current joint positions."""
        raise NotImplementedError

    @abstractmethod
    def Get_tcp_positions(self) -> list:
        """Read the current TCP positions."""
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

    @abstractmethod
    def Open_servoJ(self) -> bool:
        """Open the servo control."""
        raise NotImplementedError

    @abstractmethod
    def Close_servoJ(self) -> bool:
        """Close the servo control."""
        raise NotImplementedError
    
    @abstractmethod
    def Set_servoJ_pos(self,target_positions: list,) -> bool:
        """Set the servo control to a specific position."""
        raise NotImplementedError
