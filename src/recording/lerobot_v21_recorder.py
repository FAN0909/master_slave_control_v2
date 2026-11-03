"""按 LeRobot v2.1 的单 episode Parquet、视频和元数据布局写入。"""

import json

import av
import datasets
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from .lerobot_recorder import LeRobotRecorder


class _RunningStats:
    def __init__(self):
        self.count = 0
        self.minimum = self.maximum = self.mean = self.m2 = None

    def add(self, value):
        value = np.asarray(value, dtype=np.float64)
        if self.count == 0:
            self.minimum = value.copy()
            self.maximum = value.copy()
            self.mean = value.copy()
            self.m2 = np.zeros_like(value)
        else:
            self.minimum = np.minimum(self.minimum, value)
            self.maximum = np.maximum(self.maximum, value)
            delta = value - self.mean
            self.mean += delta / (self.count + 1)
            self.m2 += delta * (value - self.mean)
        self.count += 1

    def result(self):
        return {
            "min": self.minimum.tolist(), "max": self.maximum.tolist(),
            "mean": self.mean.tolist(),
            "std": np.sqrt(self.m2 / self.count).tolist(), "count": self.count,
        }


class _V21Dataset:
    """使用当前环境的 Arrow/PyAV 写 v2.1 目录；不依赖旧版 LeRobot 安装。"""

    @classmethod
    def create(cls, *, repo_id, root, fps, features, robot_type, use_videos, **_options):
        return cls(root, fps, features, robot_type, use_videos)

    def __init__(self, root, fps, features, robot_type, use_videos):
        self.root = root
        self.fps = fps
        self.features = features
        self.robot_type = robot_type
        self.video_keys = [key for key, value in features.items() if value["dtype"] == "video"]
        self.frame_count = 0
        self.closed = False
        self.stats = {}
        self.videos = {}
        self.video_streams = {}
        self.rows = []
        self.root.mkdir(parents=True, exist_ok=False)

        hf_features = {}
        for key, feature in features.items():
            if key in self.video_keys:
                continue
            scalar = feature["shape"] == (1,)
            value = datasets.Value(feature["dtype"])
            hf_features[key] = value if scalar else datasets.Sequence(value, length=feature["shape"][0])
        for key, dtype in (("timestamp", "float32"), ("frame_index", "int64"),
                           ("episode_index", "int64"), ("index", "int64"),
                           ("task_index", "int64")):
            hf_features[key] = datasets.Value(dtype)
        self.schema = datasets.Features(hf_features).arrow_schema
        parquet_path = self.root / "data/chunk-000/episode_000000.parquet"
        parquet_path.parent.mkdir(parents=True)
        self.writer = pq.ParquetWriter(parquet_path, self.schema, compression="zstd")

    def add_frame(self, frame):
        if self.closed:
            raise RuntimeError("episode 已关闭")
        row = {}
        for key, feature in self.features.items():
            if key in self.video_keys:
                image = frame[key]
                self._write_video(key, image)
                continue
            value = np.asarray(frame[key])
            row[key] = value.item() if feature["shape"] == (1,) else value.tolist()
            self.stats.setdefault(key, _RunningStats()).add(value)
        row.update(timestamp=np.float32(self.frame_count / self.fps).item(),
                   frame_index=self.frame_count, episode_index=0,
                   index=self.frame_count, task_index=0)
        for key in ("timestamp", "frame_index", "episode_index", "index", "task_index"):
            self.stats.setdefault(key, _RunningStats()).add(row[key])
        self.rows.append(row)
        if len(self.rows) >= 64:
            self._flush_rows()
        self.frame_count += 1

    def _flush_rows(self):
        if self.rows:
            self.writer.write_table(pa.Table.from_pylist(self.rows, schema=self.schema))
            self.rows.clear()

    def _write_video(self, key, image):
        if key not in self.videos:
            path = self.root / f"videos/chunk-000/{key}/episode_000000.mp4"
            path.parent.mkdir(parents=True, exist_ok=True)
            container = av.open(str(path), mode="w")
            stream = container.add_stream("libx264", rate=self.fps)
            stream.width = image.shape[1]
            stream.height = image.shape[0]
            stream.pix_fmt = "yuv420p"
            stream.options = {"crf": "18", "preset": "fast"}
            self.videos[key] = container
            self.video_streams[key] = stream
        video_frame = av.VideoFrame.from_ndarray(image, format="rgb24")
        container = self.videos[key]
        for packet in self.video_streams[key].encode(video_frame):
            container.mux(packet)

    def finalize(self):
        if self.closed:
            return
        self.closed = True
        self._flush_rows()
        self.writer.close()
        for key, container in self.videos.items():
            for packet in self.video_streams[key].encode():
                container.mux(packet)
            container.close()

    def save_episode(self):
        if self.frame_count == 0:
            raise RuntimeError("没有可保存的样本")
        self.finalize()
        if self.video_keys:
            from lerobot.datasets.video_utils import get_video_info
            for key in self.video_keys:
                video_path = self.root / f"videos/chunk-000/{key}/episode_000000.mp4"
                self.features[key]["info"] = get_video_info(video_path)
        features = dict(self.features)
        for key, dtype in (("timestamp", "float32"), ("frame_index", "int64"),
                           ("episode_index", "int64"), ("index", "int64"),
                           ("task_index", "int64")):
            features[key] = {"dtype": dtype, "shape": (1,), "names": None}
        info = {
            "codebase_version": "v2.1", "robot_type": self.robot_type,
            "total_episodes": 1, "total_frames": self.frame_count,
            "total_tasks": 1, "total_videos": len(self.video_keys),
            "total_chunks": 1, "chunks_size": 1000, "fps": self.fps,
            "splits": {"train": "0:1"},
            "data_path": "data/chunk-{episode_chunk:03d}/episode_{episode_index:06d}.parquet",
            "video_path": "videos/chunk-{episode_chunk:03d}/{video_key}/episode_{episode_index:06d}.mp4"
            if self.video_keys else None,
            "features": features,
        }
        meta = self.root / "meta"
        meta.mkdir(exist_ok=True)
        (meta / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        for name, item in (
            ("tasks.jsonl", {"task_index": 0, "task": self.task}),
            ("episodes.jsonl", {"episode_index": 0, "tasks": [self.task], "length": self.frame_count}),
            ("episodes_stats.jsonl", {"episode_index": 0,
                                      "stats": {key: stat.result() for key, stat in self.stats.items()}}),
        ):
            (meta / name).write_text(json.dumps(item, ensure_ascii=False) + "\n", encoding="utf-8")


class LeRobotV21Recorder(LeRobotRecorder):
    """复用采样校验和关节截取逻辑，只替换数据集写入格式。"""

    def __init__(self, root, task, fps, cameras):
        super().__init__(root, task, fps, cameras)
        self.dataset_type = _V21Dataset

    def prepare(self, *args, **kwargs):
        super().prepare(*args, **kwargs)
        self.dataset.task = self.task
