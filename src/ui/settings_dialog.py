import json
import math
from pathlib import Path
from PySide6.QtCore import QIODevice, QSaveFile, QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QDialog, QHeaderView, QInputDialog, QMessageBox, QTableWidgetItem

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
