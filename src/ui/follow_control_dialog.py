from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from .follow_control_window import Ui_FollowControlDialog


class FollowControlDialog(QDialog):
    SAVE_PATH_KEY = "save_path"
    DEFAULT_SAVE_PATH = Path(__file__).resolve().parents[2] / "record_data"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_FollowControlDialog()
        self.ui.setupUi(self)
        self.settings = QSettings("master_slave_control_v2", "follow_control")
        self.DEFAULT_SAVE_PATH.mkdir(parents=True, exist_ok=True)
        self.save_path = self.DEFAULT_SAVE_PATH
        saved_path = self.settings.value(self.SAVE_PATH_KEY, "", type=str)
        if saved_path:
            path = Path(saved_path).expanduser()
            if path.is_dir():
                self.save_path = path.resolve()
        self.ui.lineEdit_save_file_path.setText(str(self.save_path))
        self.ui.pushButton_browse_save_path.clicked.connect(self._browse_save_path)
        self.ui.lineEdit_save_file_path.editingFinished.connect(self._save_typed_path)
        self.ui.buttonBox.rejected.connect(self.reject)

    def _browse_save_path(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "选择保存目录", str(self.save_path))
        if selected:
            self._set_save_path(Path(selected))

    def _save_typed_path(self) -> None:
        entered = self.ui.lineEdit_save_file_path.text().strip()
        if not entered:
            self.settings.remove(self.SAVE_PATH_KEY)
            self.save_path = self.DEFAULT_SAVE_PATH
            self.ui.lineEdit_save_file_path.setText(str(self.save_path))
            return
        path = Path(entered).expanduser()
        if not path.is_dir():
            QMessageBox.warning(self, "保存路径无效", "请选择已存在的目录")
            self.ui.lineEdit_save_file_path.setText(str(self.save_path))
            return
        self._set_save_path(path)

    def _set_save_path(self, path: Path) -> None:
        self.save_path = path.resolve()
        self.ui.lineEdit_save_file_path.setText(str(self.save_path))
        self.settings.setValue(self.SAVE_PATH_KEY, str(self.save_path))
