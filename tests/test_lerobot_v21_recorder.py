"""验证 v2.1 实际生成可读取的 episode 文件和元数据。"""

import json
import tempfile
import unittest
from pathlib import Path

import av
import numpy as np
import pyarrow.parquet as pq

from src.recording.lerobot_v21_recorder import LeRobotV21Recorder


class LeRobotV21RecorderTests(unittest.TestCase):
    def test_save_episode_with_video(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = LeRobotV21Recorder(Path(directory), "抓取", 20, ("front",))
            image = np.zeros((16, 16, 3), dtype=np.uint8)
            for index in range(3):
                recorder.add_frame(
                    [index] * 7, [index + 1] * 7, [index + 2] * 7,
                    None, {"front": image}, index / 20,
                )
            self.assertEqual(recorder.stop(), 3)
            path = recorder.save()
            info = json.loads((path / "meta/info.json").read_text(encoding="utf-8"))
            self.assertEqual(info["codebase_version"], "v2.1")
            self.assertEqual(info["total_frames"], 3)
            self.assertEqual(info["features"]["observation.state"]["shape"], [6])
            table = pq.read_table(path / "data/chunk-000/episode_000000.parquet")
            self.assertEqual(table.num_rows, 3)
            self.assertEqual(table["observation.state"][0].as_py(), [0.0] * 6)
            np.testing.assert_allclose(table["timestamp"].to_pylist(), [0.0, 0.05, 0.1])
            video_path = path / "videos/chunk-000/observation.images.front/episode_000000.mp4"
            with av.open(str(video_path)) as container:
                self.assertEqual(sum(1 for _ in container.decode(video=0)), 3)
            self.assertEqual(json.loads((path / "meta/episodes.jsonl").read_text())["length"], 3)


if __name__ == "__main__":
    unittest.main()
