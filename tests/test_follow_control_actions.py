"""Follow Control 对话框负责按钮输入和操作信号。"""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from PySide6.QtWidgets import QApplication

from src.ui.follow_control_dialog import FollowControlDialog


class FollowControlActionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_follow_and_episode_buttons_run_dialog_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            dialog = FollowControlDialog()
            pipeline = Mock()
            camera_signal = Mock()
            feedback_signal = Mock()
            dialog.record_pipeline = pipeline
            dialog.controller = SimpleNamespace(
                slave_following=True, master_connected=True, slave_connected=True,
                follow_interval_ms=20, camera_connected={"side": True},
                hand_connected=False, request_camera_record_side=camera_signal,
                request_slave_record_feedback=feedback_signal,
            )
            events = []
            dialog.home_requested.connect(lambda: events.append(("home",)))
            dialog.follow_start_requested.connect(lambda ms: events.append(("follow_start", ms)))
            dialog.follow_stop_requested.connect(lambda: events.append(("follow_stop",)))

            dialog.set_slave_controls(True, True, False)
            dialog.ui.pushButton_slave_home_pos.click()
            dialog.ui.lineEdit_follow_rate.setText("20")
            dialog.ui.pushButton_start_follow.click()
            dialog.set_slave_controls(True, True, True)
            dialog.ui.pushButton_start_follow.click()

            dialog.ui.lineEdit_task.setText("pick object")
            dialog.ui.lineEdit_save_file_path.setText(directory)
            dialog.ui.pushButton_start_recod.click()
            pipeline.start.assert_called_once_with(
                Path(directory).resolve(), "pick object", 50, ("side",), False, "v3.0"
            )
            camera_signal.emit.assert_called_with(True)
            feedback_signal.emit.assert_called_with(True)
            self.assertEqual(dialog.record_state, "recording")
            dialog.ui.pushButton_stop_recod.click()
            pipeline.stop.assert_called_once_with()
            camera_signal.emit.assert_called_with(False)
            feedback_signal.emit.assert_called_with(False)
            dialog._on_record_stopped(1, {
                "missing_or_stale": 0, "misaligned": 0, "queue_full": 0,
                "prepare_ms": 10.0, "queue_peak": 1,
                "write_avg_ms": 2.0, "write_max_ms": 3.0,
                "effective_fps": 20.0, "max_frame_gap_ms": 50.0,
            })
            dialog.ui.pushButton_save_episode.click()
            pipeline.save.assert_called_once_with()
            dialog._on_record_finished("save", str(Path(directory) / "episode"), {})
            dialog.record_state = "pending"
            dialog.set_recording_state("pending", 1)
            dialog.ui.pushButton_discard_episode.click()
            pipeline.discard.assert_called_once_with()

            self.assertEqual(events, [
                ("home",), ("follow_start", 20), ("follow_stop",),
            ])

    def test_format_selection_reaches_pipeline_and_locks_during_recording(self):
        with tempfile.TemporaryDirectory() as directory:
            dialog = FollowControlDialog()
            dialog.record_pipeline = Mock()
            dialog.controller = SimpleNamespace(
                slave_following=True, master_connected=True, slave_connected=True,
                follow_interval_ms=50, camera_connected={}, hand_connected=False,
                request_slave_record_feedback=Mock(),
            )
            dialog.ui.lineEdit_task.setText("pick object")
            dialog.ui.lineEdit_save_file_path.setText(directory)
            dialog.ui.comboBox_recording_format.setCurrentIndex(1)
            dialog.ui.pushButton_start_recod.click()
            dialog.record_pipeline.start.assert_called_once_with(
                Path(directory).resolve(), "pick object", 20, (), False, "v2.1"
            )
            self.assertFalse(dialog.ui.comboBox_recording_format.isEnabled())

    def test_close_waits_for_episode_save(self):
        dialog = FollowControlDialog()
        dialog.record_pipeline = Mock()
        dialog.record_state = "pending"
        dialog.record_count = 1
        closed = []
        dialog.close_requested.connect(lambda: closed.append(True))
        self.assertFalse(dialog.prepare_close())
        dialog.record_pipeline.save.assert_called_once_with()
        dialog._on_record_finished("save", "/tmp/episode", {})
        self.assertEqual(closed, [True])
        self.assertTrue(dialog.prepare_close())

    def test_saved_episode_label_tracks_path_format_and_completed_save(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for folder, count, frames in (("lerobot_v30", 2, 120), ("lerobot_v21", 5, 305)):
                meta = root / folder / "meta"
                meta.mkdir(parents=True)
                (meta / "info.json").write_text(
                    json.dumps({"total_episodes": count, "total_frames": frames}), encoding="utf-8"
                )
            dialog = FollowControlDialog()
            dialog._set_save_path(root)
            self.assertEqual(dialog.ui.label_saved_episodes.text(), "已保存：2 条 Episode，120 帧")
            dialog.ui.comboBox_recording_format.setCurrentIndex(1)
            self.assertEqual(dialog.ui.label_saved_episodes.text(), "已保存：5 条 Episode，305 帧")
            (root / "lerobot_v21/meta/info.json").write_text(
                json.dumps({"total_episodes": 6, "total_frames": 350}), encoding="utf-8"
            )
            dialog._on_record_finished("save", str(root / "lerobot_v21"), {})
            self.assertEqual(dialog.ui.label_saved_episodes.text(), "已保存：6 条 Episode，350 帧")


if __name__ == "__main__":
    unittest.main()
