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
        self.slave_model = None
        self.hand_model = None

    def init_ui(self):
        self.ui.buttonBox.rejected.connect(self.reject)
        self.ui.pushButton_save_slave_param.clicked.connect(self.save_slave_config)
        table = self.ui.tableWidget_hand_actions
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.ui.pushButton_add_hand_actions.clicked.connect(self.add_hand_action)
        self.ui.pushButton_delete_hand_actions.clicked.connect(self.delete_hand_action)
        self.ui.pushButton_save_hand_actions.clicked.connect(self.save_hand_actions)
        self.ui.pushButton_hand_test.clicked.connect(self.test_hand_action)
        table.cellChanged.connect(self._hand_action_cell_changed)

#region==================================主手/从手/hand数据更新槽函数=========================
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
#endregion==================================主手/从手/hand数据更新槽函数=========================


#region===================================slave配置文件的读写=======================================
    def update_slave_config(self, model: str|None) -> bool:
        self.slave_model = model
        if self.slave_model is None:
            return False
        
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

    def save_slave_config(self, _checked: bool = False) -> bool:
        if not self.slave_model:
            Logger.instance().error("尚未连接从手，无法确定要保存的型号")
            return False

        try:
            with self.CONFIG_PATH.open("r", encoding="utf-8") as config_file:
                config = json.load(config_file)
            model_config = config[self.slave_model]

            home_joints = [
                float(getattr(self.ui, f"lineEdit_slave_home_joint{index}").text())
                for index in range(7)
            ]
            if not all(math.isfinite(value) for value in home_joints):
                raise ValueError("Home Pos 必须填写有效数字")

            motion_limits = {
                "SERVO_J_VMAX": float(self.ui.lineEdit_slave_arm_vel.text()),
                "SERVO_J_AVMAX": float(self.ui.lineEdit_slave_arm_acc.text()),
                "SERVO_J_JMAX": float(self.ui.lineEdit_slave_arm_jerk.text()),
            }
            if not all(math.isfinite(value) for value in motion_limits.values()):
                raise ValueError("Motion Limits 必须填写有效数字")

            model_config["HOME_JOINTS"] = home_joints
            model_config.update(motion_limits)

            output = json.dumps(config, ensure_ascii=False, indent=2).encode("utf-8")
            save_file = QSaveFile(str(self.CONFIG_PATH))
            if not save_file.open(QIODevice.WriteOnly):
                raise OSError(save_file.errorString())
            if save_file.write(output) != len(output) or not save_file.commit():
                save_file.cancelWriting()
                raise OSError(save_file.errorString())
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            Logger.instance().error(f"保存从手型号 {self.slave_model} 的配置失败：{error}")
            return False

        Logger.instance().info(f"已保存从手型号 {self.slave_model} 的配置")
        return True

#endregion===================================slave配置文件的读写=======================================

#region===================================hand配置文件的读写========================================
    def update_hand_config(self, model: str| None) -> bool:
        self.hand_model = model

        table = self.ui.tableWidget_hand_actions
        close_combo = self.ui.comboBox_hand_current_close
        open_combo = self.ui.comboBox_hand_current_open
        test_combo = self.ui.comboBox_hand_actions_test

        if not model:
            self.ui.label_hand_model_value.setText("未选择")
            table.setRowCount(0)
            for combo in (close_combo, open_combo, test_combo):
                combo.clear()
            for index in range(6):
                getattr(self.ui, f"lineEdit_hand_joint{index}").clear()
            return False

        try:
            with self.HAND_CONFIG_PATH.open("r", encoding="utf-8") as config_file:
                model_config = json.load(config_file)[model]

            joint_names = model_config["joint_names"]
            joint_count = model_config["joint_count"]
            if  len(joint_names) != joint_count:
                raise ValueError("手部配置文件的关节数和关节名称数量不一致")

            actions = model_config["actions"]
            if not isinstance(actions, dict):
                raise ValueError("actions 必须是动作字典")
            rows = []
            for name, action in actions.items():
                positions = action["positions"]
                if len(positions) != joint_count:
                    raise ValueError(f"动作 {name} 的关节目标值数量必须为 {joint_count}")
                rows.append([name, action.get("description", ""),
                             *positions, action["speed"], action["force"]])

            current_close = model_config["current_close"]
            current_open = model_config["current_open"]
            if current_close not in actions or current_open not in actions:
                raise ValueError("当前开合动作在 actions 中不存在")
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            Logger.instance().error(f"读取灵巧手型号 {model} 的配置失败：{error}")
            self.update_hand_config(None)
            return False

        self.ui.label_hand_model_value.setText(model)
        blocker = QSignalBlocker(table)
        table.setColumnCount(joint_count + 4)
        table.setHorizontalHeaderLabels(
            ["动作", "描述", *joint_names, "speed", "force"]
        )
        table.setRowCount(len(rows))
        for row_index, values in enumerate(rows):
            for column_index, value in enumerate(values):
                table.setItem(row_index, column_index, QTableWidgetItem(str(value)))
        del blocker

        action_names = list(actions)
        for combo in (close_combo, open_combo, test_combo):
            combo.clear()
            combo.addItems(action_names)
        close_combo.setCurrentText(current_close)
        open_combo.setCurrentText(current_open)
        return True

    #如果用户修改动作名称  则自动更新下面那三个下拉框中的动作名称
    def _hand_action_cell_changed(self, _row: int, column: int) -> None:
        if column == 0:
            self._sync_hand_action_combos()

    def _sync_hand_action_combos(self) -> None:
        table = self.ui.tableWidget_hand_actions
        names = [table.item(row, 0).text().strip()
                 for row in range(table.rowCount()) if table.item(row, 0)]
        names = [name for name in names if name]
        for combo in (self.ui.comboBox_hand_current_close,
                      self.ui.comboBox_hand_current_open,
                      self.ui.comboBox_hand_actions_test):
            selected = combo.currentText()
            blocker = QSignalBlocker(combo)
            combo.clear()
            combo.addItems(names)
            if selected in names:
                combo.setCurrentText(selected)
            del blocker

    def add_hand_action(self, _checked: bool = False) -> None:
        if not self.hand_model:
            QMessageBox.warning(self, "新增动作", "请先连接灵巧手")
            return
        name, accepted = QInputDialog.getText(self, "新增动作", "动作名称：")
        if not accepted:
            return
        name = name.strip()
        table = self.ui.tableWidget_hand_actions
        existing = {table.item(row, 0).text().strip()
                    for row in range(table.rowCount()) if table.item(row, 0)}
        if not name or name in existing:
            QMessageBox.warning(self, "新增动作", "动作名称不能为空或与已有动作重复")
            return
        try:
            with self.HAND_CONFIG_PATH.open("r", encoding="utf-8") as config_file:
                config = json.load(config_file)[self.hand_model]
            joint_count = config["joint_count"]
            try:
                positions = [
                    round(float(getattr(self.ui, f"lineEdit_hand_joint{index}").text()))
                    for index in range(joint_count)
                ]
                limits = config["position_range"]
                if not all(limits["min"] <= value <= limits["max"] for value in positions):
                    raise ValueError("当前关节位置超出范围")
            except (AttributeError, OverflowError, ValueError, TypeError):
                positions = [config["position_range"]["min"]] * joint_count
            values = [name, "", *positions, config["default_speed"], config["default_force"]]
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            Logger.instance().error(f"新增灵巧手动作失败：{error}")
            return

        row = table.rowCount()
        table.insertRow(row)
        blocker = QSignalBlocker(table)
        for column, value in enumerate(values):
            table.setItem(row, column, QTableWidgetItem(str(value)))
        del blocker
        table.selectRow(row)
        self._sync_hand_action_combos()

    def delete_hand_action(self, _checked: bool = False) -> None:
        if not self.hand_model:
            return
        table = self.ui.tableWidget_hand_actions
        row = table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "删除动作", "请先选中一行动作")
            return
        table.removeRow(row)
        self._sync_hand_action_combos()

    def _read_hand_actions_from_table(self) -> dict:
        table = self.ui.tableWidget_hand_actions
        if table.rowCount() == 0:
            raise ValueError("至少需要保留一个动作")
        with self.HAND_CONFIG_PATH.open("r", encoding="utf-8") as config_file:
            model_config = json.load(config_file)[self.hand_model]
        joint_count = model_config["joint_count"]
        position_range = model_config["position_range"]
        actions = {}
        for row in range(table.rowCount()):
            def cell(column):
                item = table.item(row, column)
                return item.text().strip() if item else ""

            name = cell(0)
            if not name or name in actions:
                raise ValueError(f"第 {row + 1} 行动作名称为空或重复")
            try:
                values = [int(cell(column)) for column in range(2, joint_count + 4)]
            except ValueError as error:
                raise ValueError(f"动作 {name} 的关节值、速度和力度必须是整数") from error
            positions = values[:joint_count]
            speed, force = values[joint_count:]
            if not all(position_range["min"] <= value <= position_range["max"]
                       for value in positions):
                raise ValueError(f"动作 {name} 的关节值超出范围")
            if not 0 <= speed <= 255 or not 0 <= force <= 255:
                raise ValueError(f"动作 {name} 的速度和力度必须在 0~255 之间")
            action = dict(model_config["actions"].get(name, {}))
            action.update(description=cell(1), positions=positions,
                          speed=speed, force=force)
            actions[name] = action
        return actions

    def save_hand_actions(self, _checked: bool = False) -> bool:
        if not self.hand_model:
            QMessageBox.warning(self, "保存动作", "请先连接灵巧手")
            return False
        try:
            actions = self._read_hand_actions_from_table()
            current_close = self.ui.comboBox_hand_current_close.currentText()
            current_open = self.ui.comboBox_hand_current_open.currentText()
            if current_close not in actions or current_open not in actions:
                raise ValueError("请选择有效的当前开合动作")
            with self.HAND_CONFIG_PATH.open("r", encoding="utf-8") as config_file:
                config = json.load(config_file)
            config[self.hand_model]["actions"] = actions
            config[self.hand_model]["current_close"] = current_close
            config[self.hand_model]["current_open"] = current_open
            output = json.dumps(config, ensure_ascii=False, indent=2).encode("utf-8")
            save_file = QSaveFile(str(self.HAND_CONFIG_PATH))
            if not save_file.open(QIODevice.WriteOnly):
                raise OSError(save_file.errorString())
            if save_file.write(output) != len(output) or not save_file.commit():
                save_file.cancelWriting()
                raise OSError(save_file.errorString())
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            Logger.instance().error(f"保存灵巧手动作失败：{error}")
            QMessageBox.warning(self, "保存动作失败", str(error))
            return False
        Logger.instance().info(f"已保存灵巧手型号 {self.hand_model} 的动作配置")
        return True

    def test_hand_action(self, _checked: bool = False) -> None:
        if not self.hand_model:
            QMessageBox.warning(self, "测试动作", "请先连接灵巧手")
            return
        name = self.ui.comboBox_hand_actions_test.currentText()
        try:
            actions = self._read_hand_actions_from_table()
            action = actions[name]
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            QMessageBox.warning(self, "测试动作失败", str(error))
            return
        self.sig_test_hand_action.emit(
            self.hand_model, name, action["positions"], action["speed"], action["force"]
        )


#endregion================================hand配置文件的读写======================================
