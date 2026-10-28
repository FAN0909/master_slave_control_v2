"""工作对象测试：模拟驱动，不连接机器人或相机。"""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from PySide6.QtCore import QCoreApplication

from src.threads.camera_thread import CameraThread
from src.threads.hand_thread import HandThread
from src.threads.master_robot_thread import MasterRobotThread
from src.threads.slave_robot_thread import SlaveRobotThread


def fake_device(**extra):
    device = SimpleNamespace(
        name="fake", is_connected=False, is_enabled=False,
        is_servoj_open=False, last_error="", MAX_JOINT_COUNT=7,
        TCP_DIM=6, Connect=None, Disconnect=None,
        Get_joint_positions=Mock(return_value=[0.0] * 7),
        Get_tcp_positions=Mock(return_value=[0.0] * 6),
        Get_color_frame=Mock(return_value=None),
        list_devices=Mock(return_value=[("camera", "123")]),
        MAX_JOINTS=Mock(return_value=6),
        Set_joint_positions=Mock(return_value=True),
        Set_speed=Mock(return_value=True), Set_force=Mock(return_value=True),
        Move_j=Mock(return_value=True), Move_l=Mock(return_value=True),
        Set_servoJ_pos=Mock(return_value=True),
    )

    def connect():
        device.is_connected = True
        return True

    def disconnect():
        device.is_connected = False
        return True

    def enable():
        device.is_enabled = True
        return True

    def disable():
        device.is_enabled = False
        return True

    def open_servoj():
        device.is_servoj_open = True
        return True

    def close_servoj():
        device.is_servoj_open = False
        return True

    device.Connect = Mock(side_effect=connect)
    device.Disconnect = Mock(side_effect=disconnect)
    device.Enable = Mock(side_effect=enable)
    device.Disable = Mock(side_effect=disable)
    device.Open_servoJ = Mock(side_effect=open_servoj)
    device.Close_servoJ = Mock(side_effect=close_servoj)
    device.__dict__.update(extra)
    return device


class DeviceThreadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def _connected(self, worker, device):
        worker._create_device = Mock(return_value=device)
        self.assertTrue(worker.Connect("model", {}))
        self.assertIs(worker.device, device)
        return worker

    def test_master_only_polls_its_own_driver(self):
        device = fake_device()
        worker = self._connected(MasterRobotThread(), device)
        readings = []
        worker.sig_joint_positions.connect(readings.append)
        self.assertTrue(worker.StartPolling(20))
        self.assertEqual(worker.Get_joint_positions(), [0.0] * 7)
        self.assertEqual(readings[-1], [0.0] * 7)
        device.Get_joint_positions.return_value = []
        self.assertEqual(worker.Get_joint_positions(), [])
        self.assertFalse(worker.timer.isActive())
        self.assertTrue(worker.Disconnect())

    def test_slave_commands_require_power_and_servoj(self):
        device = fake_device()
        worker = self._connected(SlaveRobotThread(), device)
        self.assertEqual(worker.Get_joint_positions(), [0.0] * 7)
        self.assertEqual(worker.Get_tcp_positions(), [0.0] * 6)
        self.assertFalse(worker.Move_j([0.0] * 7, 10, 10, 10))
        device.Move_j.assert_not_called()
        self.assertTrue(worker.Enable())
        self.assertTrue(worker.Move_j([0.0] * 7, 10, 10, 10))
        self.assertFalse(worker.Set_servoJ_pos([0.0] * 7))
        device.Set_servoJ_pos.assert_not_called()
        self.assertTrue(worker.Open_servoJ())
        self.assertTrue(worker.Set_servoJ_pos([0.0] * 7))
        self.assertTrue(worker.Disable())
        device.Close_servoJ.assert_called_once()
        self.assertFalse(device.is_enabled)
        self.assertTrue(worker.Disconnect())

    def test_slave_invalid_read_emits_empty_results(self):
        device = fake_device()
        worker = self._connected(SlaveRobotThread(), device)
        joints, tcp = [], []
        worker.sig_joint_positions.connect(joints.append)
        worker.sig_tcp_positions.connect(tcp.append)
        device.Get_tcp_positions.return_value = []
        self.assertEqual(worker.Read(), ([], []))
        self.assertEqual(joints[-1], [])
        self.assertEqual(tcp[-1], [])

    def test_hand_exposes_only_driver_commands(self):
        device = fake_device()
        worker = self._connected(HandThread(), device)
        device.Get_joint_positions.return_value = [0.0] * 6
        self.assertEqual(worker.Get_joint_positions(), [0.0] * 6)
        self.assertTrue(worker.Set_force([120] * 6))
        self.assertTrue(worker.Set_speed([80] * 6))
        self.assertTrue(worker.Set_joint_positions([100] * 6))
        device.Set_force.assert_called_once_with([120] * 6)
        device.Set_speed.assert_called_once_with([80] * 6)
        device.Set_joint_positions.assert_called_once_with([100] * 6)
        worker.Disconnect()
        self.assertFalse(worker.Set_joint_positions([0] * 6))

    def test_camera_can_enumerate_before_connecting(self):
        device = fake_device()
        worker = CameraThread()
        worker._create_device = Mock(return_value=device)
        self.assertEqual(worker.list_devices("D435", {}), [("camera", "123")])
        device.Connect.assert_not_called()
        self.assertIsNone(worker.device)
        self.assertTrue(worker.Connect("D435", {}))
        frame = object()
        device.Get_color_frame.return_value = frame
        captured = []
        worker.sig_color_frame.connect(captured.append)
        self.assertIs(worker.Get_color_frame(), frame)
        self.assertIs(captured[-1], frame)
        self.assertTrue(worker.Disconnect())

    def test_failed_connect_keeps_resource_if_cleanup_fails(self):
        device = fake_device()
        device.Connect = Mock(return_value=False)
        device.Disconnect = Mock(side_effect=[False, True])
        device.last_error = "连接失败"
        worker = CameraThread()
        worker._create_device = Mock(return_value=device)
        self.assertFalse(worker.Connect("D435", {}))
        self.assertIs(worker.device, device)
        self.assertFalse(worker.Connect("D435", {}))
        self.assertTrue(worker.Disconnect())
        self.assertIsNone(worker.device)


if __name__ == "__main__":
    unittest.main()
