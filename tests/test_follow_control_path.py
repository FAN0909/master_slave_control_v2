"""Follow Control 保存目录的选择与恢复。"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from src.ui.follow_control_dialog import FollowControlDialog


class FollowControlPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_browse_and_manual_path_persist(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            default = root / "record_data"
            first = root / "first"
            second = root / "second"
            first.mkdir()
            second.mkdir()
            settings = QSettings(str(root / "settings.ini"), QSettings.Format.IniFormat)
            with (patch("src.ui.follow_control_dialog.QSettings", return_value=settings),
                  patch.object(FollowControlDialog, "DEFAULT_SAVE_PATH", default)):
                dialog = FollowControlDialog()
                self.assertEqual(dialog.save_path, default)
                self.assertTrue(default.is_dir())
                self.assertEqual(dialog.ui.lineEdit_save_file_path.text(), str(default))
                with patch("src.ui.follow_control_dialog.QFileDialog.getExistingDirectory",
                           return_value=str(first)):
                    dialog.ui.pushButton_browse_save_path.click()
                self.assertEqual(dialog.save_path, first)
                self.assertEqual(dialog.ui.lineEdit_save_file_path.text(), str(first))

                dialog.ui.lineEdit_save_file_path.setText(str(second))
                dialog._save_typed_path()
                self.assertEqual(dialog.save_path, second)
                settings.sync()

                reopened = FollowControlDialog()
                self.assertEqual(reopened.save_path, second)
                self.assertEqual(reopened.ui.lineEdit_save_file_path.text(), str(second))

                reopened.ui.lineEdit_save_file_path.clear()
                reopened._save_typed_path()
                self.assertEqual(reopened.save_path, default)
                self.assertEqual(reopened.ui.lineEdit_save_file_path.text(), str(default))

                settings.setValue(FollowControlDialog.SAVE_PATH_KEY, str(root / "missing"))
                settings.sync()
                fallback = FollowControlDialog()
                self.assertEqual(fallback.save_path, default)
                self.assertEqual(fallback.ui.lineEdit_save_file_path.text(), str(default))

                with patch("src.ui.follow_control_dialog.QMessageBox.warning") as warning:
                    reopened.ui.lineEdit_save_file_path.setText(str(root / "missing"))
                    reopened._save_typed_path()
                warning.assert_called_once()
                self.assertEqual(reopened.save_path, default)
                self.assertEqual(reopened.ui.lineEdit_save_file_path.text(), str(default))


if __name__ == "__main__":
    unittest.main()
