"""设备快照、定时对齐与 LeRobot 写入线程。"""

from __future__ import annotations

import importlib.util
from collections import deque
from queue import Full, Queue
from threading import Event, Lock, Thread
from time import monotonic, monotonic_ns

from PySide6.QtCore import QObject, Signal

from .lerobot_recorder import LeRobotRecorder
from .lerobot_v21_recorder import LeRobotV21Recorder


class RecordingMailbox:
    """设备线程只发布最新样本，不在控制循环里等待磁盘。"""

    def __init__(self) -> None:
        self._lock = Lock()
        self._active = False
        self._values: dict[str, deque[tuple[object, int]]] = {}

    def start(self) -> None:
        with self._lock:
            self._values.clear()
            self._active = True

    def stop(self) -> None:
        with self._lock:
            self._active = False

    def publish(self, key: str, value: object, timestamp_ns: int | None = None) -> None:
        with self._lock:
            if self._active:
                self._values.setdefault(key, deque(maxlen=4)).append(
                    (value, monotonic_ns() if timestamp_ns is None else timestamp_ns)
                )

    def snapshot(self, keys: tuple[str, ...], at_ns: int | None = None) -> dict[str, tuple[object, int]]:
        at_ns = monotonic_ns() if at_ns is None else at_ns
        with self._lock:
            return {
                key: min(self._values[key], key=lambda sample: abs(sample[1] - at_ns))
                for key in keys if key in self._values
            }


class RecordingPipeline(QObject):
    ready = Signal()
    stopped = Signal(int, object)
    finished = Signal(str, str, object)
    failed = Signal(str)
    operation_failed = Signal(str)

    MAX_SAMPLE_AGE_NS = 250_000_000
    QUEUE_SIZE = 32

    @staticmethod
    def _empty_stats() -> dict:
        return {
            "missing_or_stale": 0, "misaligned": 0, "queue_full": 0,
            "queue_peak": 0, "prepare_ms": 0.0,
            "write_avg_ms": 0.0, "write_max_ms": 0.0,
            "max_frame_gap_ms": 0.0, "effective_fps": 0.0,
        }

    def __init__(self, mailbox: RecordingMailbox, parent=None):
        super().__init__(parent)
        self.mailbox = mailbox
        self._sample_queue: Queue = Queue(maxsize=self.QUEUE_SIZE)
        self._decision_queue: Queue = Queue(maxsize=1)
        self._stop_event = Event()
        self._writer_failed = Event()
        self._stats = self._empty_stats()
        self._active = False

    def start(self, root, task: str, fps: int, cameras: tuple[str, ...], hand: bool,
              recording_format: str = "v3.0") -> None:
        if self._active:
            raise RuntimeError("已有采集任务")
        if recording_format not in ("v2.1", "v3.0"):
            raise ValueError(f"不支持的采集格式：{recording_format}")
        if importlib.util.find_spec("lerobot") is None:
            raise RuntimeError("未安装 LeRobot；请安装 requirements.txt")
        self.root, self.task, self.fps = root, task, fps
        self.recording_format = recording_format
        self.cameras, self.hand = cameras, hand
        self._keys = ("master", "slave", "target") + (("hand",) if hand else ()) + tuple(
            f"camera:{camera}" for camera in cameras
        )
        self._sample_queue = Queue(maxsize=self.QUEUE_SIZE)
        self._decision_queue = Queue(maxsize=1)
        self._stop_event = Event()
        self._writer_failed = Event()
        self._stats = self._empty_stats()
        self._started_ns = 0
        self._first_sample_ns = 0
        self._last_sample_ns = 0
        self._sampler = None
        self.mailbox.start()
        self._active = True
        self._writer = Thread(target=self._write_loop, name="lerobot-writer", daemon=True)
        self._writer.start()

    def stop(self) -> None:
        self.mailbox.stop()
        self._stop_event.set()

    def save(self) -> None:
        self._decision_queue.put_nowait("save")

    def discard(self) -> None:
        self._decision_queue.put_nowait("discard")

    def _select_frame(self, now_ns: int, started_ns: int) -> tuple[tuple | None, str | None]:
        latest = self.mailbox.snapshot(self._keys, now_ns)
        if len(latest) != len(self._keys) or any(
            not 0 <= now_ns - timestamp <= self.MAX_SAMPLE_AGE_NS
            for _, timestamp in latest.values()
        ):
            return None, "missing_or_stale"
        if max(timestamp for _, timestamp in latest.values()) - min(
            timestamp for _, timestamp in latest.values()
        ) > int(2 * 1_000_000_000 / self.fps):
            return None, "misaligned"
        return (
            latest["slave"][0], latest["target"][0], latest["master"][0],
            latest["hand"][0] if self.hand else None,
            {camera: latest[f"camera:{camera}"][0] for camera in self.cameras},
            (now_ns - started_ns) / 1_000_000_000,
        ), None

    def _wait_for_first_frame(self) -> tuple | None:
        """先取得字段形状，供写入线程初始化数据集；该帧不计入 episode。"""
        while not self._stop_event.is_set():
            frame, _ = self._select_frame(monotonic_ns(), 0)
            if frame is not None:
                return frame
            self._stop_event.wait(0.01)
        return None

    def _sample_loop(self) -> None:
        period = 1 / self.fps
        next_tick = monotonic() + period
        while not self._stop_event.is_set():
            if self._stop_event.wait(max(0, next_tick - monotonic())):
                break
            now_ns = monotonic_ns()
            frame, reason = self._select_frame(now_ns, self._started_ns)
            if reason is not None:
                self._stats[reason] += 1
            else:
                try:
                    self._sample_queue.put_nowait(frame)
                except Full:
                    self._stats["queue_full"] += 1
                else:
                    self._stats["queue_peak"] = max(
                        self._stats["queue_peak"], 1, self._sample_queue.qsize()
                    )
                    if self._first_sample_ns == 0:
                        self._first_sample_ns = now_ns
                    else:
                        gap_ms = (now_ns - self._last_sample_ns) / 1_000_000
                        self._stats["max_frame_gap_ms"] = max(
                            self._stats["max_frame_gap_ms"], gap_ms
                        )
                    self._last_sample_ns = now_ns
            next_tick += period
            if next_tick < monotonic():
                next_tick = monotonic() + period
        while not self._writer_failed.is_set():
            try:
                self._sample_queue.put(None, timeout=0.1)
                break
            except Full:
                pass

    def _write_loop(self) -> None:
        recorder = None
        write_count = 0
        write_total_ns = 0
        write_max_ns = 0
        try:
            preflight = self._wait_for_first_frame()
            if preflight is not None:
                recorder_type = LeRobotV21Recorder if self.recording_format == "v2.1" else LeRobotRecorder
                recorder = recorder_type(self.root, self.task, self.fps, self.cameras)
                prepare_start_ns = monotonic_ns()
                recorder.prepare(*preflight)
                self._stats["prepare_ms"] = (monotonic_ns() - prepare_start_ns) / 1_000_000
                if not self._stop_event.is_set():
                    self._started_ns = monotonic_ns()
                    self._sampler = Thread(
                        target=self._sample_loop, name="record-sampler", daemon=True
                    )
                    self._sampler.start()
                    self.ready.emit()
                    while True:
                        item = self._sample_queue.get()
                        if item is None:
                            break
                        started_ns = monotonic_ns()
                        recorder.add_frame(*item)
                        elapsed_ns = monotonic_ns() - started_ns
                        write_count += 1
                        write_total_ns += elapsed_ns
                        write_max_ns = max(write_max_ns, elapsed_ns)
        except Exception as error:
            self._writer_failed.set()
            self.stop()
            if self._sampler is not None:
                self._sampler.join()
            if recorder is not None:
                try:
                    recorder.discard()
                except Exception:
                    pass
            self._active = False
            self.failed.emit(f"采集写入失败：{error}")
            return
        if write_count:
            self._stats["write_avg_ms"] = write_total_ns / write_count / 1_000_000
            self._stats["write_max_ms"] = write_max_ns / 1_000_000
            span_ns = self._last_sample_ns - self._first_sample_ns
            if span_ns > 0:
                self._stats["effective_fps"] = (write_count - 1) * 1_000_000_000 / span_ns
        count = recorder.stop() if recorder is not None else 0
        self.stopped.emit(count, dict(self._stats))
        while True:
            decision = self._decision_queue.get()
            try:
                if decision == "save" and recorder is not None:
                    path = str(recorder.save())
                elif decision == "discard":
                    if recorder is not None:
                        recorder.discard()
                    path = ""
                else:
                    raise RuntimeError("没有可保存的样本")
            except Exception as error:
                self.operation_failed.emit(f"处理 episode 失败：{error}")
                continue
            self._active = False
            self.finished.emit(decision, path, dict(self._stats))
            return
