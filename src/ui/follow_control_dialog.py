import json
from pathlib import Path

from PySide6.QtCore import QSettings, Signal, Slot
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from ..log import Logger
from ..recording.lerobot_recorder import LeRobotRecorder
from ..recording.lerobot_v21_recorder import LeRobotV21Recorder
from ..recording.pipeline import RecordingPipeline
from .follow_control_window import Ui_FollowControlDialog


class FollowControlDialog(QDialog):
    home_requested = Signal()
    follow_start_requested = Signal(int)
    follow_stop_requested = Signal()
    close_requested = Signal()

    SAVE_PATH_KEY = "save_path"
    DEFAULT_SAVE_PATH = Path(__file__).resolve().parents[2] / "record_data"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_FollowControlDialog()
        self.ui.setupUi(self)
        self.ui.comboBox_recording_format.setItemData(0, "v3.0")
        self.ui.comboBox_recording_format.setItemData(1, "v2.1")
        self.settings = QSettings("master_slave_control_v2", "follow_control")
        self.DEFAULT_SAVE_PATH.mkdir(parents=True, exist_ok=True)
        self.save_path = self.DEFAULT_SAVE_PATH
        saved_path = self.settings.value(self.SAVE_PATH_KEY, "", type=str)
        if saved_path:
            path = Path(saved_path).expanduser()
            if path.is_dir():
                self.save_path = path.resolve()
        self.ui.lineEdit_save_file_path.setText(str(self.save_path))
        self.ui.pushButton_browse_save_path.clicked.connect(self._browse_save_path)
        self.ui.lineEdit_save_file_path.editingFinished.connect(self._save_typed_path)
        self.ui.comboBox_recording_format.currentIndexChanged.connect(
            self._refresh_saved_episode_count
        )
        self.ui.buttonBox.rejected.connect(self.reject)
        self._following = False
        self.controller = None
        self.record_pipeline = None
        self.record_state = "idle"
        self.record_count = 0
        self.record_cameras = ()
        self.record_hand = False
        self._closing_after_record = False
        self.ui.pushButton_slave_home_pos.clicked.connect(self._request_home)
        self.ui.pushButton_start_follow.clicked.connect(self._toggle_follow)
        self.ui.pushButton_start_recod.clicked.connect(self._start_recording)
        self.ui.pushButton_stop_recod.clicked.connect(self._stop_recording)
        self.ui.pushButton_save_episode.clicked.connect(self._save_episode)
        self.ui.pushButton_discard_episode.clicked.connect(self._discard_episode)
        self.set_slave_controls(False, False, False)
        self.set_recording_state("idle", 0)
        self._refresh_saved_episode_count()

    def _refresh_saved_episode_count(self) -> None:
        """读取当前格式数据集的元数据；缺失的数据集按 0 条显示。"""
        dataset_dirs = {
            "v2.1": LeRobotV21Recorder.DATASET_DIR,
            "v3.0": LeRobotRecorder.DATASET_DIR,
        }
        dataset_dir = dataset_dirs.get(self.ui.comboBox_recording_format.currentData())
        if dataset_dir is None:
            self.ui.label_saved_episodes.setText("已保存：—")
            return
        info_path = self.save_path / dataset_dir / "meta" / "info.json"
        if not info_path.exists():
            if (self.save_path / dataset_dir).exists():
                self.ui.label_saved_episodes.setText("已保存：读取失败")
                return
            episodes = frames = 0
        else:
            try:
                with info_path.open(encoding="utf-8") as info_file:
                    info = json.load(info_file)
                episodes, frames = info["total_episodes"], info["total_frames"]
                if any(type(value) is not int or value < 0 for value in (episodes, frames)):
                    raise ValueError("数据集计数无效")
            except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
                self.ui.label_saved_episodes.setText("已保存：读取失败")
                return
        self.ui.label_saved_episodes.setText(
            f"已保存：{episodes} 条 Episode，{frames} 帧"
        )

    def configure_recording(self, mailbox, controller) -> None:
        """绑定设备协调者，并让采集流程由对话框管理。"""
        self.controller = controller
        self.record_pipeline = RecordingPipeline(mailbox, self)
        self.record_pipeline.ready.connect(self._on_record_ready)
        self.record_pipeline.stopped.connect(self._on_record_stopped)
        self.record_pipeline.finished.connect(self._on_record_finished)
        self.record_pipeline.failed.connect(self._on_record_failed)
        self.record_pipeline.operation_failed.connect(self._on_record_operation_failed)

    def set_slave_controls(self, connected: bool, enabled: bool, following: bool) -> None:
        self._following = following
        self.ui.pushButton_slave_home_pos.setEnabled(connected and enabled)
        self.ui.pushButton_start_follow.setText("Stop Follow" if following else "Start Follow")
        self.ui.pushButton_start_follow.setEnabled(connected)

    def set_follow_request_pending(self) -> None:
        self.ui.pushButton_start_follow.setEnabled(False)

    def set_recording_state(self, state: str, count: int) -> None:
        pending = state == "pending"
        self.ui.pushButton_start_recod.setEnabled(state == "idle")
        self.ui.pushButton_stop_recod.setEnabled(state == "recording")
        self.ui.pushButton_save_episode.setEnabled(pending and count > 0)
        self.ui.pushButton_discard_episode.setEnabled(pending)
        for control in (self.ui.lineEdit_task, self.ui.lineEdit_save_file_path,
                        self.ui.pushButton_browse_save_path, self.ui.comboBox_recording_format):
            control.setEnabled(state == "idle")

    def _toggle_follow(self) -> None:
        if self._following:
            self.set_follow_request_pending()
            self.follow_stop_requested.emit()
            return
        try:
            interval_ms = int(self.ui.lineEdit_follow_rate.text().strip())
            if not 0 < interval_ms <= 2_147_483_647:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "跟随周期无效", "跟随周期必须是正整数（毫秒）")
            return
        self.follow_start_requested.emit(interval_ms)

    def _request_home(self) -> None:
        self.home_requested.emit()

    def _start_recording(self) -> None:
        if self.record_state != "idle" or self.record_pipeline is None:
            return
        task = self.ui.lineEdit_task.text().strip()
        if not task:
            QMessageBox.warning(self, "任务描述为空", "请先填写任务描述")
            return
        entered_path = self.ui.lineEdit_save_file_path.text().strip()
        if entered_path != str(self.save_path):
            self._save_typed_path()
            if self.ui.lineEdit_save_file_path.text() != entered_path:
                return
        controller = self.controller
        if not controller.slave_following or not controller.master_connected or not controller.slave_connected:
            Logger.instance().error("请先连接主从手并启动跟随")
            return
        recording_format = self.ui.comboBox_recording_format.currentData()
        if recording_format not in ("v2.1", "v3.0"):
            Logger.instance().error("请选择支持的采集格式")
            return
        try:
            interval_ms = controller.follow_interval_ms
            if interval_ms <= 0 or 1000 % interval_ms:
                raise ValueError("当前跟随周期必须能整除 1000 毫秒")
            self.record_cameras = tuple(
                camera for camera, connected in controller.camera_connected.items() if connected
            )
            self.record_hand = controller.hand_connected
            self.record_pipeline.start(
                self.save_path, task, 1000 // interval_ms,
                self.record_cameras, self.record_hand, recording_format,
            )
        except (OSError, RuntimeError, ValueError) as error:
            Logger.instance().error(f"开始采集失败：{error}")
            return
        self.record_count = 0
        for camera in self.record_cameras:
            getattr(controller, f"request_camera_record_{camera}").emit(True)
        controller.request_slave_record_feedback.emit(True)
        self.record_state = "recording"
        self.set_recording_state(self.record_state, self.record_count)
        Logger.instance().info(f"正在准备 LeRobot {recording_format} 采集：{task}")

    @Slot()
    def _on_record_ready(self) -> None:
        if self.record_state == "recording":
            Logger.instance().info("LeRobot 数据集初始化完成，开始按设定周期采集")

    def _stop_recording(self) -> None:
        if self.record_state != "recording":
            return
        self.record_pipeline.stop()
        for camera in self.record_cameras:
            getattr(self.controller, f"request_camera_record_{camera}").emit(False)
        self.controller.request_slave_record_feedback.emit(False)
        self.record_state = "stopping"
        self.set_recording_state(self.record_state, self.record_count)
        Logger.instance().info("正在停止采集并处理写入队列")

    def stop_recording(self) -> None:
        """跟随被外部停止时结束当前采集。"""
        self._stop_recording()

    @Slot(int, object)
    def _on_record_stopped(self, count: int, stats: dict) -> None:
        self.record_count = count
        self.record_state = "pending"
        self.set_recording_state(self.record_state, self.record_count)
        Logger.instance().info(
            f"采集已停止：{count} 帧，过期/缺失 {stats['missing_or_stale']} 次，"
            f"时间差过大 {stats['misaligned']} 次，队列满 {stats['queue_full']} 次"
        )
        Logger.instance().info(
            f"采集性能：初始化 {stats['prepare_ms']:.0f} ms，"
            f"队列峰值 {stats['queue_peak']}/{self.record_pipeline.QUEUE_SIZE}，"
            f"单帧写入平均/最长 {stats['write_avg_ms']:.1f}/{stats['write_max_ms']:.1f} ms，"
            f"实际帧率 {stats['effective_fps']:.1f} fps，"
            f"最大帧间隔 {stats['max_frame_gap_ms']:.1f} ms"
        )
        if self._closing_after_record:
            self._save_episode() if count else self._discard_episode()

    def _save_episode(self) -> None:
        if self.record_state != "pending" or self.record_count == 0:
            return
        try:
            self.record_pipeline.save()
        except Exception as error:
            Logger.instance().error(f"保存 episode 失败：{error}")
            return
        self.record_state = "saving"
        self.set_recording_state(self.record_state, self.record_count)

    def _discard_episode(self) -> None:
        if self.record_state != "pending":
            return
        try:
            self.record_pipeline.discard()
        except Exception as error:
            Logger.instance().error(f"丢弃 episode 失败：{error}")
            return
        self.record_state = "discarding"
        self.set_recording_state(self.record_state, self.record_count)

    @Slot(str, str, object)
    def _on_record_finished(self, decision: str, path: str, stats: dict) -> None:
        Logger.instance().info(
            f"LeRobot {self.ui.comboBox_recording_format.currentData()} episode 已保存：{path}"
            if decision == "save" else "episode 已丢弃"
        )
        self.record_state = "idle"
        self.record_cameras = ()
        self.set_recording_state(self.record_state, self.record_count)
        self._refresh_saved_episode_count()
        if self._closing_after_record:
            self._closing_after_record = False
            self.close_requested.emit()

    @Slot(str)
    def _on_record_failed(self, message: str) -> None:
        Logger.instance().error(message)
        for camera in self.record_cameras:
            getattr(self.controller, f"request_camera_record_{camera}").emit(False)
        self.controller.request_slave_record_feedback.emit(False)
        self.record_state = "idle"
        self._closing_after_record = False
        self.set_recording_state(self.record_state, self.record_count)

    @Slot(str)
    def _on_record_operation_failed(self, message: str) -> None:
        Logger.instance().error(message)
        self.record_state = "pending"
        self._closing_after_record = False
        self.set_recording_state(self.record_state, self.record_count)

    def prepare_close(self) -> bool:
        """主窗口关闭前完成当前 episode；返回是否可以立刻关闭。"""
        if self.record_state == "idle":
            return True
        self._closing_after_record = True
        if self.record_state == "recording":
            self._stop_recording()
        elif self.record_state == "pending":
            self._save_episode() if self.record_count else self._discard_episode()
        return False

    def _browse_save_path(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "选择保存目录", str(self.save_path))
        if selected:
            self._set_save_path(Path(selected))

    def _save_typed_path(self) -> None:
        entered = self.ui.lineEdit_save_file_path.text().strip()
        if not entered:
            self.settings.remove(self.SAVE_PATH_KEY)
            self.save_path = self.DEFAULT_SAVE_PATH
            self.ui.lineEdit_save_file_path.setText(str(self.save_path))
            self._refresh_saved_episode_count()
            return
        path = Path(entered).expanduser()
        if not path.is_dir():
            QMessageBox.warning(self, "保存路径无效", "请选择已存在的目录")
            self.ui.lineEdit_save_file_path.setText(str(self.save_path))
            return
        self._set_save_path(path)

    def _set_save_path(self, path: Path) -> None:
        self.save_path = path.resolve()
        self.ui.lineEdit_save_file_path.setText(str(self.save_path))
        self.settings.setValue(self.SAVE_PATH_KEY, str(self.save_path))
        self._refresh_saved_episode_count()
