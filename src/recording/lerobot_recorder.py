"""使用 LeRobot v3.0 API 记录一条本地 episode。"""

import json
import shutil
from pathlib import Path

import numpy as np


class LeRobotRecorder:
    CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "recording.json"
    DATASET_DIR = "lerobot_v30"
    CODEBASE_VERSION = "v3.0"

    def __init__(self, root: Path, task: str, fps: int, cameras: tuple[str, ...]):
        try:
            from lerobot.datasets.lerobot_dataset import LeRobotDataset
        except ImportError as error:
            raise RuntimeError("未安装 LeRobot；请安装 requirements.txt") from error
        self.dataset_type = LeRobotDataset
        self.root = Path(root)
        self.task = task
        self.fps = fps
        self.cameras = cameras
        self.recorded_joints = self._load_recording_config()
        self.path = self.root / self.DATASET_DIR
        self._created_dataset = False
        self.dataset = None
        self.count = 0
        self.stopped = False

    def _load_recording_config(self) -> dict[str, int]:
        try:
            with self.CONFIG_PATH.open(encoding="utf-8") as config_file:
                config = json.load(config_file)
            counts = {
                device: config[device]["recorded_joints"]
                for device in ("master", "slave", "hand")
            }
            if any(type(count) is not int or count <= 0 for count in counts.values()):
                raise ValueError("recorded_joints 必须是正整数")
            return counts
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            raise ValueError(f"采集关节配置无效 ({self.CONFIG_PATH}): {error}") from error

    def prepare(self, state, action, master, hand, images: dict[str, np.ndarray],
                capture_elapsed_s: float | None = None) -> None:
        """根据设备样本确定字段并初始化数据集，但不写入预检样本。"""
        if self.dataset is not None:
            return
        self._validate_sample(state, action, master, hand, images)
        master_count = self.recorded_joints["master"]
        slave_count = self.recorded_joints["slave"]
        features = {
            "observation.state": {"dtype": "float32", "shape": (slave_count,), "names": [f"joint_{i}" for i in range(slave_count)]},
            "action": {"dtype": "float32", "shape": (slave_count,), "names": [f"joint_{i}" for i in range(slave_count)]},
            "observation.master_joints": {"dtype": "float32", "shape": (master_count,), "names": [f"joint_{i}" for i in range(master_count)]},
        }
        if capture_elapsed_s is not None:
            features["capture_elapsed_s"] = {
                "dtype": "float64", "shape": (1,), "names": ["seconds"],
            }
        if hand is not None:
            hand_count = self.recorded_joints["hand"]
            features["observation.hand_joints"] = {
                "dtype": "float32", "shape": (hand_count,),
                "names": [f"joint_{i}" for i in range(hand_count)],
            }
        for camera, image in images.items():
            features[f"observation.images.{camera}"] = {
                "dtype": "video", "shape": image.shape,
                "names": ["height", "width", "channels"],
            }
        options = {}
        if self.cameras:
            from lerobot.configs.video import RGBEncoderConfig
            options = {
                "rgb_encoder": RGBEncoderConfig(
                    vcodec="h264", pix_fmt="yuv420p", crf=18,
                    preset="fast", g=self.fps,
                ),
                "streaming_encoding": True,
                "encoder_queue_maxsize": max(4, self.fps // 2),
                "encoder_threads": 2,
            }
        repo_id = f"local/{self.path.name}"
        info_path = self.path / "meta" / "info.json"
        if self.path.exists():
            if not info_path.is_file():
                raise ValueError(f"数据集目录已存在但缺少 meta/info.json：{self.path}")
            with info_path.open(encoding="utf-8") as info_file:
                info = json.load(info_file)
            self._check_existing_schema(info, features)
            self.dataset = self.dataset_type.resume(
                repo_id=repo_id, root=self.path, **options,
            )
        else:
            self.dataset = self.dataset_type.create(
                repo_id=repo_id, root=self.path,
                fps=self.fps, features=features, robot_type="NRC",
                use_videos=bool(self.cameras), **options,
            )
            self._created_dataset = True

    def _check_existing_schema(self, info: dict, features: dict) -> None:
        if info.get("codebase_version") != self.CODEBASE_VERSION or info.get("fps") != self.fps:
            raise ValueError(f"已有数据集的格式或帧率与当前采集不一致：{self.path}")
        existing = info.get("features", {})
        if set(existing) != set(features) | {
            "timestamp", "frame_index", "episode_index", "index", "task_index"
        }:
            raise ValueError(f"已有数据集字段与当前设备配置不一致：{self.path}")
        for key, feature in features.items():
            saved = existing[key]
            if (saved.get("dtype") != feature["dtype"]
                    or tuple(saved.get("shape", ())) != tuple(feature["shape"])
                    or saved.get("names") != feature["names"]):
                raise ValueError(f"已有数据集的 {key} 与当前设备配置不一致：{self.path}")

    def _validate_sample(self, state, action, master, hand,
                         images: dict[str, np.ndarray]) -> None:
        state = np.asarray(state, dtype=np.float32)
        action = np.asarray(action, dtype=np.float32)
        master = np.asarray(master, dtype=np.float32)
        if (state.ndim != 1 or action.ndim != 1 or master.ndim != 1
                or not len(state) or len(action) != len(state) or not len(master)):
            raise ValueError("主手、从手反馈和从手目标必须是一维关节数组，且从手反馈与目标长度相同")
        if not all(np.isfinite(values).all() for values in (state, action, master)):
            raise ValueError("关节数据包含无效数值")
        for device, values in (("slave", state), ("slave", action), ("master", master)):
            if self.recorded_joints[device] > len(values):
                raise ValueError(f"{device} 配置采集 {self.recorded_joints[device]} 轴，设备仅提供 {len(values)} 轴")
        if hand is not None:
            hand_values = np.asarray(hand, dtype=np.float32)
            if hand_values.ndim != 1 or self.recorded_joints["hand"] > hand_values.size:
                raise ValueError(
                    f"hand 配置采集 {self.recorded_joints['hand']} 轴，设备仅提供 {hand_values.size} 轴"
                )
            if not np.isfinite(hand_values).all():
                raise ValueError("灵巧手关节数据包含无效数值")
        if set(images) != set(self.cameras):
            raise ValueError("相机帧尚未齐全")
        for image in images.values():
            if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
                raise ValueError("相机图像必须为 HWC uint8 RGB")

    def add_frame(self, state, action, master, hand, images: dict[str, np.ndarray],
                  capture_elapsed_s: float | None = None) -> None:
        if self.stopped:
            raise RuntimeError("episode 已停止")
        self._validate_sample(state, action, master, hand, images)
        self.prepare(state, action, master, hand, images, capture_elapsed_s)
        # 只在数据集写入边界截取；设备线程仍保留完整数据供控制使用。
        master_count = self.recorded_joints["master"]
        slave_count = self.recorded_joints["slave"]
        frame = {
            "observation.state": np.asarray(state[:slave_count], dtype=np.float32),
            "action": np.asarray(action[:slave_count], dtype=np.float32),
            "observation.master_joints": np.asarray(master[:master_count], dtype=np.float32),
            "task": self.task,
        }
        if "capture_elapsed_s" in self.dataset.features:
            frame["capture_elapsed_s"] = np.asarray([capture_elapsed_s], dtype=np.float64)
        if "observation.hand_joints" in self.dataset.features:
            if hand is None:
                raise ValueError("灵巧手数据缺失")
            frame["observation.hand_joints"] = np.asarray(
                hand[:self.recorded_joints["hand"]], dtype=np.float32
            )
        for camera, image in images.items():
            frame[f"observation.images.{camera}"] = image
        self.dataset.add_frame(frame)
        self.count += 1

    def stop(self) -> int:
        self.stopped = True
        return self.count

    def save(self) -> Path:
        if not self.stopped or self.dataset is None or self.count == 0:
            raise RuntimeError("没有可保存的 episode")
        self.dataset.save_episode()
        self.dataset.finalize()
        return self.path

    def discard(self) -> None:
        if self.dataset is not None:
            self.dataset.clear_episode_buffer()
            self.dataset.finalize()
        if self._created_dataset and self.path.exists():
            shutil.rmtree(self.path)
