"""采集线程的对齐、写入和停止流程。"""

import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication

from src.recording.pipeline import RecordingMailbox, RecordingPipeline


class FakeRecorder:
    calls = []

    def __init__(self, root, task, fps, cameras):
        self.count = 0
        self.path = Path(root) / "episode-test"

    def prepare(self, *frame):
        self.calls.append(("prepare", threading.current_thread().name))

    def add_frame(self, *frame):
        self.calls.append(("add", threading.current_thread().name))
        self.count += 1

    def stop(self):
        return self.count

    def save(self):
        return self.path

    def discard(self):
        pass


class SlowPrepareRecorder(FakeRecorder):
    def prepare(self, *frame):
        time.sleep(0.15)
        super().prepare(*frame)


class RecordingPipelineTests(unittest.TestCase):
    def test_mailbox_selects_nearest_sample_and_clears_on_restart(self):
        mailbox = RecordingMailbox()
        mailbox.start()
        mailbox.publish("master", [1], 100)
        mailbox.publish("master", [2], 200)
        self.assertEqual(mailbox.snapshot(("master",), 110)["master"][0], [1])
        mailbox.stop()
        mailbox.start()
        self.assertEqual(mailbox.snapshot(("master",)), {})

    @staticmethod
    def _wait_for(event: threading.Event) -> bool:
        app = QCoreApplication.instance() or QCoreApplication([])
        deadline = time.monotonic() + 2
        while not event.is_set() and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.005)
        return event.is_set()

    def test_device_mailbox_sampled_and_written_off_gui_thread(self):
        app = QCoreApplication.instance() or QCoreApplication([])
        FakeRecorder.calls.clear()
        mailbox = RecordingMailbox()
        pipeline = RecordingPipeline(mailbox)
        stopped = threading.Event()
        finished = threading.Event()
        counts = []
        stats_seen = []
        pipeline.stopped.connect(
            lambda count, stats: (counts.append(count), stats_seen.append(stats), stopped.set())
        )
        pipeline.finished.connect(lambda decision, path, stats: finished.set())
        with tempfile.TemporaryDirectory() as directory, patch(
            "src.recording.pipeline.importlib.util.find_spec", return_value=object()
        ), patch("src.recording.pipeline.LeRobotRecorder", FakeRecorder):
            pipeline.start(Path(directory), "task", 50, (), False)
            for _ in range(8):
                mailbox.publish("master", [1] * 7)
                mailbox.publish("slave", [2] * 7)
                mailbox.publish("target", [3] * 7)
                time.sleep(0.01)
            pipeline.stop()
            self.assertTrue(self._wait_for(stopped))
            self.assertGreater(counts[0], 0)
            pipeline.save()
            self.assertTrue(self._wait_for(finished))
        self.assertTrue(all(name == "lerobot-writer" for _, name in FakeRecorder.calls))
        self.assertEqual(FakeRecorder.calls[0][0], "prepare")
        self.assertGreaterEqual(stats_seen[0]["queue_peak"], 1)
        self.assertGreater(stats_seen[0]["effective_fps"], 0)

    def test_slow_dataset_initialization_does_not_fill_sample_queue(self):
        mailbox = RecordingMailbox()
        pipeline = RecordingPipeline(mailbox)
        pipeline.QUEUE_SIZE = 2
        ready = threading.Event()
        stopped = threading.Event()
        finished = threading.Event()
        result = []
        pipeline.ready.connect(ready.set)
        pipeline.stopped.connect(lambda count, stats: (result.append((count, stats)), stopped.set()))
        pipeline.finished.connect(lambda decision, path, stats: finished.set())
        with tempfile.TemporaryDirectory() as directory, patch(
            "src.recording.pipeline.importlib.util.find_spec", return_value=object()
        ), patch("src.recording.pipeline.LeRobotRecorder", SlowPrepareRecorder):
            pipeline.start(Path(directory), "task", 50, (), False)
            deadline = time.monotonic() + 0.35
            while time.monotonic() < deadline:
                for key in ("master", "slave", "target"):
                    mailbox.publish(key, [1] * 7)
                time.sleep(0.005)
            self.assertTrue(self._wait_for(ready))
            pipeline.stop()
            self.assertTrue(self._wait_for(stopped))
            pipeline.discard()
            self.assertTrue(self._wait_for(finished))
        self.assertGreater(result[0][0], 0)
        self.assertGreaterEqual(result[0][1]["prepare_ms"], 100)
        self.assertEqual(result[0][1]["queue_full"], 0)


if __name__ == "__main__":
    unittest.main()
