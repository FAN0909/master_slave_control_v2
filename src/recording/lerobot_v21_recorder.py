"""按 LeRobot v2.1 的单 episode 文件布局向同一数据集追加。"""

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

    DEFAULT_DTYPES = {
        "timestamp": "float32", "frame_index": "int64", "episode_index": "int64",
        "index": "int64", "task_index": "int64",
    }

    @classmethod
    def create(cls, *, repo_id, root, fps, features, robot_type, use_videos, **_options):
        return cls(root, fps, features, robot_type, use_videos)

    @classmethod
    def resume(cls, *, repo_id, root, **_options):
        info = json.loads((root / "meta/info.json").read_text(encoding="utf-8"))
        features = {key: value for key, value in info["features"].items()
                    if key not in cls.DEFAULT_DTYPES}
        return cls(root, info["fps"], features, info["robot_type"],
                   bool(info["video_path"]), existing_info=info)

    def __init__(self, root, fps, features, robot_type, use_videos, existing_info=None):
        self.root = root
        self.fps = fps
        self.features = features
        self.robot_type = robot_type
        self.video_keys = [key for key, value in features.items() if value["dtype"] == "video"]
        self.previous_info = existing_info
        self.episode_index = existing_info["total_episodes"] if existing_info else 0
        self.global_start = existing_info["total_frames"] if existing_info else 0
        self.chunk = self.episode_index // (existing_info["chunks_size"] if existing_info else 1000)
        tasks_path = self.root / "meta/tasks.jsonl"
        self.tasks = {}
        if tasks_path.exists():
            for line in tasks_path.read_text(encoding="utf-8").splitlines():
                item = json.loads(line)
                self.tasks[item["task"]] = item["task_index"]
        self.frame_count = 0
        self.closed = False
        self.stats = {}
        self.videos = {}
        self.video_streams = {}
        self.rows = []
        if existing_info is None:
            self.root.mkdir(parents=True, exist_ok=False)

        hf_features = {}
        for key, feature in features.items():
            if key in self.video_keys:
                continue
            scalar = tuple(feature["shape"]) == (1,)
            value = datasets.Value(feature["dtype"])
            hf_features[key] = value if scalar else datasets.Sequence(value, length=feature["shape"][0])
        for key, dtype in self.DEFAULT_DTYPES.items():
            hf_features[key] = datasets.Value(dtype)
        self.schema = datasets.Features(hf_features).arrow_schema
        parquet_path = self._data_path()
        if parquet_path.exists():
            raise ValueError(f"目标 episode 文件已存在：{parquet_path}")
        parquet_path.parent.mkdir(parents=True, exist_ok=True)
        self.writer = pq.ParquetWriter(parquet_path, self.schema, compression="zstd")

    def _data_path(self):
        return self.root / f"data/chunk-{self.chunk:03d}/episode_{self.episode_index:06d}.parquet"

    def _video_path(self, key):
        return self.root / f"videos/chunk-{self.chunk:03d}/{key}/episode_{self.episode_index:06d}.mp4"

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
            row[key] = value.item() if tuple(feature["shape"]) == (1,) else value.tolist()
            self.stats.setdefault(key, _RunningStats()).add(value)
        row.update(timestamp=np.float32(self.frame_count / self.fps).item(),
                   frame_index=self.frame_count, episode_index=self.episode_index,
                   index=self.global_start + self.frame_count,
                   task_index=self.tasks.get(self.task, len(self.tasks)))
        for key in self.DEFAULT_DTYPES:
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
            path = self._video_path(key)
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
        if self.video_keys and self.episode_index == 0:
            from lerobot.datasets.video_utils import get_video_info
            for key in self.video_keys:
                self.features[key]["info"] = get_video_info(self._video_path(key))
        if self.previous_info is None:
            features = dict(self.features)
            for key, dtype in self.DEFAULT_DTYPES.items():
                features[key] = {"dtype": dtype, "shape": (1,), "names": None}
            info = {
                "codebase_version": "v2.1", "robot_type": self.robot_type,
                "total_episodes": 0, "total_frames": 0,
                "total_tasks": 0, "total_videos": 0,
                "total_chunks": 0, "chunks_size": 1000, "fps": self.fps,
                "splits": {},
                "data_path": "data/chunk-{episode_chunk:03d}/episode_{episode_index:06d}.parquet",
                "video_path": "videos/chunk-{episode_chunk:03d}/{video_key}/episode_{episode_index:06d}.mp4"
                if self.video_keys else None,
                "features": features,
            }
        else:
            info = dict(self.previous_info)
        task_index = self.tasks.get(self.task)
        if task_index is None:
            task_index = len(self.tasks)
        info["total_episodes"] += 1
        info["total_frames"] += self.frame_count
        info["total_tasks"] = max(info["total_tasks"], task_index + 1)
        info["total_videos"] += len(self.video_keys)
        info["total_chunks"] = max(info["total_chunks"], self.chunk + 1)
        info["splits"] = {"train": f"0:{info['total_episodes']}"}
        meta = self.root / "meta"
        meta.mkdir(exist_ok=True)
        if self.task not in self.tasks:
            self._append_jsonl(meta / "tasks.jsonl", {"task_index": task_index, "task": self.task})
        self._append_jsonl(meta / "episodes.jsonl", {
            "episode_index": self.episode_index, "tasks": [self.task], "length": self.frame_count,
        })
        self._append_jsonl(meta / "episodes_stats.jsonl", {
            "episode_index": self.episode_index,
            "stats": {key: stat.result() for key, stat in self.stats.items()},
        })
        temporary = meta / "info.json.tmp"
        temporary.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(meta / "info.json")

    @staticmethod
    def _append_jsonl(path, item):
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(item, ensure_ascii=False) + "\n")

    def clear_episode_buffer(self):
        self.finalize()
        self._data_path().unlink(missing_ok=True)
        for key in self.video_keys:
            self._video_path(key).unlink(missing_ok=True)


class LeRobotV21Recorder(LeRobotRecorder):
    """复用采样校验和关节截取逻辑，只替换数据集写入格式。"""

    DATASET_DIR = "lerobot_v21"
    CODEBASE_VERSION = "v2.1"

    def __init__(self, root, task, fps, cameras):
        super().__init__(root, task, fps, cameras)
        self.dataset_type = _V21Dataset

    def prepare(self, *args, **kwargs):
        super().prepare(*args, **kwargs)
        self.dataset.task = self.task
