"""主从手线程共享的最新关节位置快照。"""

from dataclasses import dataclass
from threading import Lock
from time import monotonic_ns


@dataclass(frozen=True)
class JointSample:
    positions: tuple[float, ...]
    timestamp_ns: int
    generation: int


class JointSnapshot:
    def __init__(self) -> None:
        self._lock = Lock()
        self._sample: JointSample | None = None
        self._generation = 0

    def update(self, positions: list[float]) -> None:
        values = tuple(positions)
        timestamp_ns = monotonic_ns()
        with self._lock:
            self._sample = JointSample(values, timestamp_ns, self._generation)

    def read(self) -> JointSample | None:
        with self._lock:
            return self._sample

    def clear(self) -> None:
        with self._lock:
            self._generation += 1
            self._sample = None
