"""主手第七轴控制灵巧手开关，不连接真实设备。"""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PySide6.QtCore import QCoreApplication

from src.threads.hand_thread import HandThread
from src.threads.joint_snapshot import JointSnapshot


class HandFollowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def test_threshold_switches_once_with_hysteresis_and_stops_on_generation_change(self):
        snapshot = JointSnapshot()
        snapshot.update([0.0] * 7)
        device = SimpleNamespace(
            name="test_hand", is_connected=True,
            Set_speed=Mock(return_value=True),
            Set_force=Mock(return_value=True),
            Set_joint_positions=Mock(return_value=True),
        )
        with tempfile.TemporaryDirectory() as directory:
            follow_path = Path(directory) / "follow.json"
            hand_path = Path(directory) / "hand.json"
            follow_path.write_text(json.dumps({
                "HAND_CLOSE_DELTA_DEG": 10,
                "HAND_OPEN_DELTA_DEG": 5,
            }), encoding="utf-8")
            hand_path.write_text(json.dumps({"test_hand": {
                "joint_count": 6,
                "current_open": "open1", "current_close": "close1",
                "actions": {
                    "open1": {"positions": [20] * 6, "speed": 30, "force": 40},
                    "close1": {"positions": [300] * 6, "speed": 50, "force": 60},
                },
            }}), encoding="utf-8")
            with (patch.object(HandThread, "FOLLOW_CONFIG_PATH", follow_path),
                  patch.object(HandThread, "HAND_CONFIG_PATH", hand_path)):
                hand = HandThread(snapshot)
                hand.device = device
                hand.is_connect = True
                self.assertTrue(hand.start_follow_work(20))
                hand.follow_move()
                snapshot.update([0.0] * 6 + [9.9])
                hand.follow_move()
                device.Set_joint_positions.assert_not_called()

                snapshot.update([0.0] * 6 + [-10.0])
                hand.follow_move()
                device.Set_joint_positions.assert_called_once_with([300] * 6)
                device.Set_speed.assert_called_once_with([50] * 6)
                device.Set_force.assert_called_once_with([60] * 6)

                snapshot.update([0.0] * 6 + [-6.0])
                hand.follow_move()
                self.assertEqual(device.Set_joint_positions.call_count, 1)
                snapshot.update([0.0] * 6 + [-5.0])
                hand.follow_move()
                self.assertEqual(device.Set_joint_positions.call_count, 2)
                device.Set_joint_positions.assert_called_with([20] * 6)
                hand.follow_move()
                self.assertEqual(device.Set_joint_positions.call_count, 2)

                snapshot.clear()
                snapshot.update([0.0] * 6 + [30.0])
                hand.follow_move()
                self.assertFalse(hand.follow_timer.isActive())
                self.assertEqual(device.Set_joint_positions.call_count, 2)


if __name__ == "__main__":
    unittest.main()
