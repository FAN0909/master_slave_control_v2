from PySide6.QtWidgets import QDialog

from .follow_control_window import Ui_FollowControlDialog


class FollowControlDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_FollowControlDialog()
        self.ui.setupUi(self)
        self.ui.buttonBox.rejected.connect(self.reject)
