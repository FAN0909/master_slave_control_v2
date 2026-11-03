"""LeRobot 写入器的字段、保存和丢弃生命周期。"""

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from src.recording.lerobot_recorder import LeRobotRecorder


class FakeDataset:
    instances = []

    @classmethod
    def create(cls, **kwargs):
        dataset = cls()
        dataset.features = kwargs["features"]
        dataset.kwargs = kwargs
        dataset.frames = []
        dataset.saved = False
        dataset.finalized = False
        cls.instances.append(dataset)
        kwargs["root"].mkdir()
        return dataset

    def add_frame(self, frame):
        self.frames.append(frame)

    def save_episode(self):
        self.saved = True

    def finalize(self):
        self.finalized = True


class FakeEncoder:
    def __init__(self, **kwargs):
        self.options = kwargs


class RecorderTests(unittest.TestCase):
    def setUp(self):
        config_dir = tempfile.TemporaryDirectory()
        self.addCleanup(config_dir.cleanup)
        self.config_path = Path(config_dir.name) / "recording.json"
        self.write_config(master=6, slave=6, hand=6)
        config_patch = patch.object(LeRobotRecorder, "CONFIG_PATH", self.config_path)
        config_patch.start()
        self.addCleanup(config_patch.stop)

    def write_config(self, *, master, slave, hand):
        self.config_path.write_text(json.dumps({
            "master": {"recorded_joints": master},
            "slave": {"recorded_joints": slave},
            "hand": {"recorded_joints": hand},
        }), encoding="utf-8")

    def test_record_and_save(self):
        module = types.ModuleType("lerobot.datasets.lerobot_dataset")
        module.LeRobotDataset = FakeDataset
        encoder_module = types.ModuleType("lerobot.configs.video")
        encoder_module.RGBEncoderConfig = FakeEncoder
        with tempfile.TemporaryDirectory() as directory, patch.dict(sys.modules, {
            "lerobot": types.ModuleType("lerobot"),
            "lerobot.datasets": types.ModuleType("lerobot.datasets"),
            "lerobot.datasets.lerobot_dataset": module,
            "lerobot.configs": types.ModuleType("lerobot.configs"),
            "lerobot.configs.video": encoder_module,
        }):
            recorder = LeRobotRecorder(Path(directory), "抓取", 50, ("front",))
            values = [1.0] * 6 + [99.0]
            image = np.zeros((8, 10, 3), dtype=np.uint8)
            recorder.prepare(values, values, values, None, {"front": image}, 0.0)
            self.assertEqual(FakeDataset.instances[-1].frames, [])
            recorder.add_frame(values, values, values, None, {"front": image}, 0.02)
            dataset = FakeDataset.instances[-1]
            self.assertEqual(dataset.kwargs["fps"], 50)
            self.assertTrue(dataset.kwargs["streaming_encoding"])
            self.assertEqual(dataset.kwargs["rgb_encoder"].options["vcodec"], "h264")
            for field in ("observation.state", "action", "observation.master_joints"):
                self.assertEqual(dataset.features[field]["shape"], (6,))
                self.assertEqual(dataset.features[field]["names"], [f"joint_{i}" for i in range(6)])
                self.assertEqual(dataset.frames[0][field].tolist(), [1.0] * 6)
            self.assertEqual(dataset.features["observation.images.front"]["shape"], (8, 10, 3))
            self.assertEqual(dataset.frames[0]["task"], "抓取")
            self.assertEqual(dataset.frames[0]["capture_elapsed_s"].tolist(), [0.02])
            self.assertEqual(recorder.stop(), 1)
            self.assertEqual(recorder.save(), recorder.path)
            self.assertTrue(dataset.saved)
            self.assertTrue(dataset.finalized)

    def test_discard(self):
        module = types.ModuleType("lerobot.datasets.lerobot_dataset")
        module.LeRobotDataset = FakeDataset
        with tempfile.TemporaryDirectory() as directory, patch.dict(sys.modules, {
            "lerobot": types.ModuleType("lerobot"),
            "lerobot.datasets": types.ModuleType("lerobot.datasets"),
            "lerobot.datasets.lerobot_dataset": module,
        }):
            recorder = LeRobotRecorder(Path(directory), "抓取", 50, ())
            recorder.add_frame([0] * 7, [0] * 7, [0] * 7, None, {})
            path = recorder.path
            recorder.stop()
            recorder.discard()
            self.assertFalse(path.exists())

    def test_joint_counts_come_from_config_and_are_fixed_for_episode(self):
        self.write_config(master=7, slave=6, hand=4)
        module = types.ModuleType("lerobot.datasets.lerobot_dataset")
        module.LeRobotDataset = FakeDataset
        with tempfile.TemporaryDirectory() as directory, patch.dict(sys.modules, {
            "lerobot": types.ModuleType("lerobot"),
            "lerobot.datasets": types.ModuleType("lerobot.datasets"),
            "lerobot.datasets.lerobot_dataset": module,
        }):
            recorder = LeRobotRecorder(Path(directory), "抓取", 20, ())
            self.write_config(master=6, slave=7, hand=6)
            recorder.add_frame(
                [1] * 6 + [99], [2] * 6 + [88], [3] * 6 + [77],
                [10, 11, 12, 13, 14, 15], {}, 0.05,
            )
            dataset = FakeDataset.instances[-1]
            self.assertEqual(dataset.features["observation.master_joints"]["shape"], (7,))
            self.assertEqual(dataset.features["observation.state"]["shape"], (6,))
            self.assertEqual(dataset.features["action"]["shape"], (6,))
            self.assertEqual(dataset.features["observation.hand_joints"]["shape"], (4,))
            self.assertEqual(dataset.frames[0]["observation.master_joints"].tolist(), [3.0] * 6 + [77.0])
            self.assertEqual(dataset.frames[0]["observation.state"].tolist(), [1.0] * 6)
            self.assertEqual(dataset.frames[0]["action"].tolist(), [2.0] * 6)
            self.assertEqual(dataset.frames[0]["observation.hand_joints"].tolist(), [10.0, 11.0, 12.0, 13.0])
            recorder.stop()
            recorder.discard()

            next_recorder = LeRobotRecorder(Path(directory), "抓取", 20, ())
            next_recorder.add_frame([1] * 6 + [99], [2] * 6 + [88],
                                    [3] * 6 + [77], [10, 11, 12, 13, 14, 15], {})
            next_dataset = FakeDataset.instances[-1]
            self.assertEqual(next_dataset.features["observation.state"]["shape"], (7,))
            self.assertEqual(next_dataset.features["action"]["shape"], (7,))
            self.assertEqual(next_dataset.features["observation.master_joints"]["shape"], (6,))
            self.assertEqual(next_dataset.frames[0]["action"].tolist(), [2.0] * 6 + [88.0])
            next_recorder.stop()
            next_recorder.discard()

    def test_config_cannot_request_more_joints_than_device_provides(self):
        self.write_config(master=6, slave=6, hand=7)
        module = types.ModuleType("lerobot.datasets.lerobot_dataset")
        module.LeRobotDataset = FakeDataset
        with tempfile.TemporaryDirectory() as directory, patch.dict(sys.modules, {
            "lerobot": types.ModuleType("lerobot"),
            "lerobot.datasets": types.ModuleType("lerobot.datasets"),
            "lerobot.datasets.lerobot_dataset": module,
        }):
            recorder = LeRobotRecorder(Path(directory), "抓取", 20, ())
            with self.assertRaisesRegex(ValueError, "hand 配置采集 7 轴，设备仅提供 6 轴"):
                recorder.prepare([0] * 7, [0] * 7, [0] * 7, [0] * 6, {}, 0.0)
