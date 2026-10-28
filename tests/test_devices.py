"""不加载真实厂商 SDK、不连接硬件的驱动接口回归测试。"""

import inspect
import logging
import math
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.devices.base.base_device import BaseDevice
from src.devices.base.base_hand import BaseHand
from src.devices.base.base_masterArm import BaseMasterArm
from src.devices.base.base_robotArm import BaseRobotArm
from src.devices.drivers.camera_d435 import CameraD435
from src.devices.drivers.gello_arm import GelloArm
from src.devices.drivers.Link_hand import LinkHand
from src.devices.drivers.nrc_arm import NrcArm


class Vector(list):
    def resize(self, size):
        self[:] = (self + [0.0] * size)[:size]


def fake_nrc():
    return SimpleNamespace(
        connect_robot=Mock(side_effect=[10, 11]),
        disconnect_robot=Mock(return_value=0),
        VectorDouble=Vector,
        MoveCmd=lambda: SimpleNamespace(targetPosValue=Vector()),
        get_current_position=Mock(return_value=0),
        robot_movej=Mock(return_value=0), robot_movel=Mock(return_value=0),
        set_servo_state=Mock(return_value=0), set_servo_poweron=Mock(return_value=0),
        set_servo_poweroff=Mock(return_value=0), open_servoJ=Mock(return_value=0),
        stop_servoJ=Mock(return_value=0), set_servoJ_pos=Mock(return_value=0),
    )


class ContractTests(unittest.TestCase):
    def test_abstract_bases_cannot_be_instantiated(self):
        for cls in (BaseDevice, BaseHand, BaseMasterArm, BaseRobotArm):
            with self.subTest(cls=cls.__name__), self.assertRaises(TypeError):
                cls("abstract")

    def test_parameter_names_match_base(self):
        for base, driver, names in (
            (BaseRobotArm, NrcArm, ("Move_j", "Move_l", "Set_servoJ_pos")),
            (BaseHand, LinkHand, ("Set_speed", "Set_force", "Set_joint_positions")),
        ):
            for name in names:
                with self.subTest(method=name):
                    self.assertEqual(list(inspect.signature(getattr(base, name)).parameters),
                                     list(inspect.signature(getattr(driver, name)).parameters))

    def test_passive_master_only_needs_connection_and_joint_reading(self):
        class PassiveMaster(BaseMasterArm):
            def Connect(self):
                return True

            def Disconnect(self):
                return True

            def Get_joint_positions(self):
                return []

        arm = PassiveMaster("passive")
        self.assertFalse(arm.supports_enable)
        self.assertFalse(arm.supports_tcp)
        self.assertFalse(arm.Enable())
        self.assertEqual(arm.Get_tcp_positions(), [])
        self.assertTrue(arm.last_error)


class NrcTests(unittest.TestCase):
    def setUp(self):
        self.sdk = fake_nrc()
        self.patcher = patch("src.devices.drivers.nrc_arm.nrc_interface", self.sdk)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.arm = NrcArm("nrc")

    def test_connection_is_idempotent_and_disconnect_clears_state(self):
        self.assertTrue(self.arm.Connect())
        self.assertTrue(self.arm.Connect())
        self.assertEqual(self.sdk.connect_robot.call_count, 2)
        self.assertTrue(self.arm.Enable())
        self.assertTrue(self.arm.Open_servoJ())
        self.assertTrue(self.arm.Disconnect())
        self.assertTrue(self.arm.Disconnect())
        self.assertEqual(self.sdk.disconnect_robot.call_count, 2)
        self.assertIsNone(self.arm.command_fd)
        self.assertIsNone(self.arm.servo_fd)
        self.assertFalse(self.arm.is_enabled)
        self.assertFalse(self.arm.is_servoj_open)

    def test_partial_connection_failure_releases_open_socket(self):
        for failure in (-1, OSError("servo port failed")):
            with self.subTest(failure=failure):
                self.sdk.connect_robot.side_effect = [10, failure]
                self.sdk.disconnect_robot.reset_mock()
                self.assertFalse(self.arm.Connect())
                self.sdk.disconnect_robot.assert_called_once_with(10)
                self.assertIsNone(self.arm.command_fd)
                self.assertFalse(self.arm.is_connected)
                self.assertTrue(self.arm.last_error)

    def test_close_failure_retains_handle_for_retry(self):
        self.arm.Connect()
        self.sdk.disconnect_robot.side_effect = [OSError("busy"), 0]
        self.assertFalse(self.arm.Disconnect())
        self.assertEqual(self.arm.servo_fd, 11)
        self.assertIsNone(self.arm.command_fd)
        self.sdk.disconnect_robot.side_effect = None
        self.assertTrue(self.arm.Disconnect())
        self.assertIsNone(self.arm.servo_fd)

    def test_movements_use_base_keyword_and_sdk_signature(self):
        self.arm.Connect()
        count = self.arm.MAX_JOINT_COUNT
        self.assertTrue(self.arm.Move_l(target_positions=[1] * 6, speed=10,
                                        acceleration=20, deceleration=20))
        fd, cmd = self.sdk.robot_movel.call_args.args
        self.assertEqual(fd, 10)
        self.assertEqual(cmd.targetPosValue, [1.0] * 6 + [0.0] * (count - 6))
        self.assertTrue(self.arm.Move_j(target_positions=[2] * count, speed=10,
                                        acceleration=20, deceleration=20))
        self.assertEqual(len(self.sdk.robot_movej.call_args.args), 2)

    def test_invalid_motion_never_reaches_sdk(self):
        count = self.arm.MAX_JOINT_COUNT
        self.assertFalse(self.arm.Move_j([0] * count, 10, 20, 20))
        self.arm.Connect()
        for values, speed in (([0] * (count - 1), 10), ([math.nan] * count, 10),
                              ([0] * count, -1), ([0] * count, math.inf)):
            self.assertFalse(self.arm.Move_j(values, speed, 20, 20))
        self.sdk.robot_movej.assert_not_called()

    def test_failed_read_is_not_zero_pose(self):
        self.assertEqual(self.arm.Get_joint_positions(), [])
        self.arm.Connect()
        # 真正的零位可以正常返回；SDK 报错必须返回空结果。
        self.assertEqual(self.arm.Get_joint_positions(), [0.0] * self.arm.MAX_JOINT_COUNT)
        self.sdk.get_current_position.return_value = -1
        self.assertEqual(self.arm.Get_joint_positions(), [])
        self.assertEqual(self.arm.Get_tcp_positions(), [])

    def test_servo_requires_open_and_valid_vector(self):
        self.arm.Connect()
        count = self.arm.MAX_JOINT_COUNT
        self.assertFalse(self.arm.Set_servoJ_pos([0] * count))
        self.arm.Open_servoJ()
        for values in ([0] * (count - 1), [math.inf] * count):
            self.assertFalse(self.arm.Set_servoJ_pos(values))
        self.sdk.set_servoJ_pos.assert_not_called()
        self.assertTrue(self.arm.Set_servoJ_pos([0] * count))


class GelloTests(unittest.TestCase):
    def test_read_conversion_and_rejection_of_bad_samples(self):
        arm = GelloArm("gello")
        arm.is_connected = True
        arm.dynamixel_driver = Mock()
        arm.dynamixel_driver.get_joints.return_value = [math.pi] * 7
        self.assertEqual(arm.Get_joint_positions(), [180.0] * 7)
        for sample in (None, [0] * 6, [0] * 8, [math.nan] * 7, [1e308] * 7):
            arm.dynamixel_driver.get_joints.return_value = sample
            self.assertEqual(arm.Get_joint_positions(), [])

    def test_failed_close_can_be_retried(self):
        arm = GelloArm("gello")
        driver = Mock()
        driver.close.side_effect = [OSError("close failed"), None]
        arm.dynamixel_driver = driver
        self.assertFalse(arm.Disconnect())
        self.assertIs(arm.dynamixel_driver, driver)
        self.assertTrue(arm.Disconnect())
        self.assertIsNone(arm.dynamixel_driver)


class HandTests(unittest.TestCase):
    def setUp(self):
        self.hand = LinkHand("hand", hand_joint="o6")
        self.hand.is_connected = True
        self.hand.hand_api = Mock()
        self.hand.hand_api.finger_move.return_value = None
        self.hand.hand_api.set_speed.return_value = None

    def test_valid_command_and_invalid_values(self):
        self.assertTrue(self.hand.Set_joint_positions([100] * 6))
        self.hand.hand_api.finger_move.assert_called_once_with([100] * 6)
        self.hand.hand_api.finger_move.reset_mock()
        for values in ([0] * 5, [-1] * 6, [256] * 6, [math.nan] * 6):
            self.assertFalse(self.hand.Set_joint_positions(values))
        self.hand.hand_api.finger_move.assert_not_called()

    def test_speed_is_list_and_validated_before_sdk(self):
        for values in (100, [100] * 5, [math.inf] * 6):
            self.assertFalse(self.hand.Set_speed(values))
        self.hand.hand_api.set_speed.assert_not_called()
        self.assertTrue(self.hand.Set_speed([100] * 6))

    def test_sdk_exit_does_not_terminate_application(self):
        self.hand.hand_api = None
        self.hand.is_connected = False
        sdk = SimpleNamespace(LinkerHandApi=Mock(side_effect=SystemExit(1)))
        with patch.dict("sys.modules", {"vendor.linkerhand_python_sdk.LinkerHand.linker_hand_api": sdk}):
            self.assertFalse(self.hand.Connect())
        self.assertTrue(self.hand.last_error)


class CameraTests(unittest.TestCase):
    def test_failed_disconnect_reports_error_and_can_retry(self):
        camera = CameraD435("camera")
        camera.is_connected = True
        camera.camera_manager = Mock()
        camera.camera_manager.is_connected.return_value = True
        camera.camera_manager.disconnect.side_effect = [RuntimeError("busy"), None]
        self.assertFalse(camera.Disconnect())
        self.assertTrue(camera.last_error)
        self.assertTrue(camera.is_connected)
        self.assertTrue(camera.Disconnect())
        self.assertFalse(camera.is_connected)

    def test_lifecycle_and_error_reporting(self):
        camera = CameraD435("camera")
        manager = Mock()
        manager.is_connected.return_value = True
        camera.camera_manager = manager
        self.assertIsNone(camera.Get_color_frame())
        self.assertTrue(camera.Connect())
        self.assertTrue(camera.Connect())
        manager.connect.assert_called_once()
        manager.get_color_frame.return_value = None
        self.assertIsNone(camera.Get_color_frame())
        self.assertEqual(camera.last_error, "")
        manager.get_color_frame.side_effect = RuntimeError("read failed")
        self.assertIsNone(camera.Get_color_frame())
        self.assertTrue(camera.last_error)
        self.assertTrue(camera.Disconnect())
        self.assertFalse(camera.is_connected)

    def test_enumeration_failure_returns_empty_list(self):
        camera = CameraD435("camera")
        camera.camera_manager = Mock()
        camera.camera_manager.list_devices.side_effect = RuntimeError("missing sdk")
        self.assertEqual(camera.list_devices(), [])
        self.assertTrue(camera.last_error)


if __name__ == "__main__":
    logging.basicConfig(level=logging.CRITICAL)
    unittest.main()
