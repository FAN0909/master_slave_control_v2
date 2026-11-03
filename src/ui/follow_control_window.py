# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'follow_control_window.ui'
##
## Created by: Qt User Interface Compiler version 6.12.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QSizePolicy, QSpacerItem, QVBoxLayout, QWidget)

class Ui_FollowControlDialog(object):
    def setupUi(self, FollowControlDialog):
        if not FollowControlDialog.objectName():
            FollowControlDialog.setObjectName(u"FollowControlDialog")
        FollowControlDialog.resize(800, 535)
        self.verticalLayout = QVBoxLayout(FollowControlDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)

        self.buttonBox = QDialogButtonBox(FollowControlDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Close)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(FollowControlDialog)

        QMetaObject.connectSlotsByName(FollowControlDialog)
    # setupUi

    def retranslateUi(self, FollowControlDialog):
        FollowControlDialog.setWindowTitle(QCoreApplication.translate("FollowControlDialog", u"Follow Control", None))
    # retranslateUi

