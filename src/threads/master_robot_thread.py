"""Gello 主手工作对象：连接、断开、读取关节角度。"""

import logging
import math

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from src.devices.drivers_factory import create_master_arm


class MasterRobotThread(QObject):


    def __init__(self):
        super().__init__()
        self.device = None



    def Connect(self, model: str, options: dict) -> bool:
        pass


  
    def Disconnect(self) -> bool:
        pass


    def _create_device(self, model: str, **options):
        return create_master_arm(model, **options)

  
    def Get_joint_positions(self) -> list:
        pass


