import json
import math
from pathlib import Path
from PySide6.QtCore import QIODevice, QSaveFile, QSignalBlocker, Qt, Signal, Slot
from PySide6.QtWidgets import QAbstractItemView, QDialog, QHeaderView, QInputDialog, QMessageBox, QTableWidgetItem

from ..log import Logger
from .settings_window import Ui_SettingsDialog


class SettingsDialog(QDialog):
    sig_test_hand_action = Signal(str, str, list, int, int)

    CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "slave_arm.json"
    HAND_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "hand_control.json"

    def __init__(self, parent=None):
        """创建界面并保存当前型号、动作列表和表格快照等编辑状态。"""
        super().__init__(parent)
        self.ui = Ui_SettingsDialog()
        self.ui.setupUi(self)
        self.init_ui()

    def init_ui(self):
        self.ui.buttonBox.rejected.connect(self.reject)

    @Slot(list)
    def update_master_joint_positions(self, positions: list) -> None:
        if len(positions) != 7:
            return
        for index, position in enumerate(positions):
            getattr(self.ui, f"lineEdit_master_joint{index}").setText(
                f"{position:.2f}"
            )

    @Slot(list)
    def update_slave_joint_positions(self, positions: list) -> None:
        if len(positions) != 7:
            return
        for index, position in enumerate(positions):
            getattr(self.ui, f"lineEdit_slave_joint{index}").setText(
                f"{position:.2f}"
            )

    @Slot(list)
    def update_slave_tcp_positions(self, positions: list) -> None:
        if len(positions) < 6:
            return
        for axis, position in zip("xyzabc", positions):
            getattr(self.ui, f"lineEdit_slave_{axis}").setText(f"{position:.2f}")

    @Slot(list)
    def update_hand_joint_positions(self, positions: list) -> None:
        if len(positions) != 6:
            return
        for index, position in enumerate(positions):
            getattr(self.ui, f"lineEdit_hand_joint{index}").setText(f"{position:g}")

#读取slave配置文件
    def update_slave_config(self, model: str) -> bool:
        try:
            with self.CONFIG_PATH.open("r", encoding="utf-8") as config_file:
                model_config = json.load(config_file)[model]
            home_joints = model_config["HOME_JOINTS"]
            if len(home_joints) != 7:
                raise ValueError("HOME_JOINTS 必须包含 7 个关节值")

            for index, position in enumerate(home_joints):
                getattr(self.ui, f"lineEdit_slave_home_joint{index}").setText(
                    f"{position:g}"
                )
            for key, widget_name in (
                ("SERVO_J_VMAX", "lineEdit_slave_arm_vel"),
                ("SERVO_J_AVMAX", "lineEdit_slave_arm_acc"),
                ("SERVO_J_JMAX", "lineEdit_slave_arm_jerk"),
            ):
                getattr(self.ui, widget_name).setText(f"{model_config[key]:g}")
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            Logger.instance().error(f"读取从手型号 {model} 的配置失败：{error}")
            return False
        return True
