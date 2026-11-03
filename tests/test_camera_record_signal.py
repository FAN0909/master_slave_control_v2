"""相机工作线程向采集邮箱发布独立 RGB 图像与读取时间。"""

import unittest
from unittest.mock import patch

import numpy as np

from src.threads.camera_thread import CameraThread
from src.recording.pipeline import RecordingMailbox


class CameraRecordSignalTests(unittest.TestCase):
    def test_record_frame_is_separate_from_preview(self):
        mailbox = RecordingMailbox()
        mailbox.start()
        worker = CameraThread(mailbox, "front")
        frame = np.zeros((4, 5, 3), dtype=np.uint8)
        frame[0, 0] = [1, 2, 3]
        preview = []
        worker.sig_color_frame.connect(preview.append)
        with patch.object(worker, "Get_color_frame", return_value=frame), patch(
            "src.threads.camera_thread.monotonic_ns", return_value=123
        ):
            worker.read_color_frame()
            self.assertEqual(mailbox.snapshot(("camera:front",)), {})
            worker.set_recording(True)
            worker.read_color_frame()
        recorded, timestamp = mailbox.snapshot(("camera:front",))["camera:front"]
        self.assertEqual(timestamp, 123)
        self.assertIsNot(recorded, frame)
        self.assertEqual(recorded[0, 0].tolist(), [3, 2, 1])
        self.assertIs(preview[-1], frame)


if __name__ == "__main__":
    unittest.main()
