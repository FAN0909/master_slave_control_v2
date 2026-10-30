"""关节增量跟随的快照与目标计算，不连接真实机器人。"""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PySide6.QtCore import QCoreApplication

from src.threads.joint_snapshot import JointSnapshot
from src.threads.master_robot_thread import MasterRobotThread
from src.threads.slave_robot_thread import SlaveRobotThread


class FollowSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def test_master_writes_latest_positions_and_timestamp(self):
        snapshot = JointSnapshot()
        master = MasterRobotThread(snapshot)
        master.device = SimpleNamespace(
            is_connected=True,
            Get_joint_positions=Mock(side_effect=[[1.0] * 7, [2.0] * 7]),
        )
        master.is_connect = True
        with patch("src.threads.joint_snapshot.monotonic_ns", side_effect=[100, 200]):
            master.read_joint_pos()
            first = snapshot.read()
            master.read_joint_pos()
        assert first is not None
        self.assertEqual(first.timestamp_ns, 100)
        self.assertEqual(snapshot.read().positions, (2.0,) * 7)
        self.assertEqual(snapshot.read().timestamp_ns, 200)
        snapshot.clear()
        self.assertIsNone(snapshot.read())

    def test_incremental_follow_holds_latest_snapshot_without_timeout(self):
        snapshot = JointSnapshot()
        with patch("src.threads.joint_snapshot.monotonic_ns", return_value=1):
            snapshot.update([10.0] * 7)
        device = SimpleNamespace(
            JOINT_COUNT=7, SERVO_J_VMAX=80.0,
            FOLLOW_JOINT_MAP=(1, 0, 2, 3, 4, 5, 6),
            FOLLOW_JOINT_DIRECTION=(-1, 1, 1, 1, 1, 1, 1),
            FOLLOW_JOINT_GAIN=(0.5, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
            is_connected=True, is_enabled=True,
            Get_joint_positions=Mock(return_value=[30.0] * 7),
            Open_servoJ=Mock(return_value=True),
            Set_servoJ_pos=Mock(return_value=True),
            Close_servoJ=Mock(return_value=True),
        )
        slave = SlaveRobotThread(snapshot)
        slave.device = device
        slave.is_connect = True
        slave.is_enable = True
        slave.start_timer_work(100)
        self.assertTrue(slave.start_follow_work(20))
        self.assertEqual(device.Set_servoJ_pos.call_args.args[0], [30.0] * 7)
        self.assertFalse(slave.read_timer.isActive())

        snapshot.update([20.0, 14.0, 20.0, 20.0, 20.0, 20.0, 20.0])
        slave.follow_move()
        first_target = device.Set_servoJ_pos.call_args.args[0]
        self.assertAlmostEqual(first_target[0], 28.4)
        self.assertAlmostEqual(first_target[1], 31.6)
        slave.follow_move()  # 同一快照仍可逐周期追上目标，不按时间戳停止。
        second_target = device.Set_servoJ_pos.call_args.args[0]
        self.assertAlmostEqual(second_target[0], 28.0)
        self.assertAlmostEqual(second_target[1], 33.2)
        self.assertTrue(slave.is_following)

        slave.stop_follow_work()
        device.Close_servoJ.assert_called_once()
        self.assertTrue(slave.read_timer.isActive())
        self.assertEqual(slave.read_timer.interval(), 100)

    def test_master_reconnect_does_not_reuse_old_follow_baseline(self):
        snapshot = JointSnapshot()
        snapshot.update([0.0] * 7)
        device = SimpleNamespace(
            JOINT_COUNT=7, SERVO_J_VMAX=80.0,
            FOLLOW_JOINT_MAP=tuple(range(7)),
            FOLLOW_JOINT_DIRECTION=(1,) * 7,
            FOLLOW_JOINT_GAIN=(1.0,) * 7,
            is_connected=True, is_enabled=True,
            Get_joint_positions=Mock(return_value=[0.0] * 7),
            Open_servoJ=Mock(return_value=True),
            Set_servoJ_pos=Mock(return_value=True),
            Close_servoJ=Mock(return_value=True),
        )
        slave = SlaveRobotThread(snapshot)
        slave.device = device
        slave.is_connect = True
        self.assertTrue(slave.start_follow_work(20))
        snapshot.clear()
        snapshot.update([90.0] * 7)
        slave.follow_move()
        device.Set_servoJ_pos.assert_called_once_with([0.0] * 7)
        slave.stop_follow_work()


if __name__ == "__main__":
    unittest.main()
