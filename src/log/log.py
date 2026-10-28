"""Thread-safe bridge from application code to the GUI log panel."""

from datetime import datetime

from PySide6.QtCore import QObject, Signal


class Logger(QObject):
    """Small singleton logger that displays messages in the main window."""

    message_logged = Signal(str, str)
    _instance = None

    def __init__(self):
        super().__init__()

    @classmethod
    def instance(cls) -> "Logger":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def debug(self, message) -> None:
        self._log("DEBUG", message)

    def info(self, message) -> None:
        self._log("INFO", message)

    def warning(self, message) -> None:
        self._log("WARNING", message)

    def error(self, message) -> None:
        self._log("ERROR", message)

    def critical(self, message) -> None:
        self._log("CRITICAL", message)

    def _log(self, level: str, message) -> None:
        timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
        self.message_logged.emit(level, f"[{timestamp}] [{level}] {message}")
