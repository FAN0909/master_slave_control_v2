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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QComboBox, QDialog,
    QDialogButtonBox, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

class Ui_FollowControlDialog(object):
    def setupUi(self, FollowControlDialog):
        if not FollowControlDialog.objectName():
            FollowControlDialog.setObjectName(u"FollowControlDialog")
        FollowControlDialog.resize(800, 535)
        self.verticalLayout = QVBoxLayout(FollowControlDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.groupBox_follow_control = QGroupBox(FollowControlDialog)
        self.groupBox_follow_control.setObjectName(u"groupBox_follow_control")
        self.horizontalLayout_2 = QHBoxLayout(self.groupBox_follow_control)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_follow_header = QVBoxLayout()
        self.verticalLayout_follow_header.setObjectName(u"verticalLayout_follow_header")
        self.label_follow_hint = QLabel(self.groupBox_follow_control)
        self.label_follow_hint.setObjectName(u"label_follow_hint")
        self.label_follow_hint.setWordWrap(True)

        self.verticalLayout_follow_header.addWidget(self.label_follow_hint)

        self.horizontalLayout_follow_start = QHBoxLayout()
        self.horizontalLayout_follow_start.setObjectName(u"horizontalLayout_follow_start")
        self.pushButton_start_follow = QPushButton(self.groupBox_follow_control)
        self.pushButton_start_follow.setObjectName(u"pushButton_start_follow")

        self.horizontalLayout_follow_start.addWidget(self.pushButton_start_follow)

        self.label_follow_interval = QLabel(self.groupBox_follow_control)
        self.label_follow_interval.setObjectName(u"label_follow_interval")

        self.horizontalLayout_follow_start.addWidget(self.label_follow_interval)

        self.lineEdit_follow_rate = QLineEdit(self.groupBox_follow_control)
        self.lineEdit_follow_rate.setObjectName(u"lineEdit_follow_rate")

        self.horizontalLayout_follow_start.addWidget(self.lineEdit_follow_rate)

        self.pushButton_slave_home_pos = QPushButton(self.groupBox_follow_control)
        self.pushButton_slave_home_pos.setObjectName(u"pushButton_slave_home_pos")

        self.horizontalLayout_follow_start.addWidget(self.pushButton_slave_home_pos)


        self.verticalLayout_follow_header.addLayout(self.horizontalLayout_follow_start)


        self.verticalLayout_2.addLayout(self.verticalLayout_follow_header)

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.pushButton_start_recod = QPushButton(self.groupBox_follow_control)
        self.pushButton_start_recod.setObjectName(u"pushButton_start_recod")

        self.gridLayout.addWidget(self.pushButton_start_recod, 3, 1, 1, 1)

        self.pushButton_stop_recod = QPushButton(self.groupBox_follow_control)
        self.pushButton_stop_recod.setObjectName(u"pushButton_stop_recod")

        self.gridLayout.addWidget(self.pushButton_stop_recod, 3, 2, 1, 1)

        self.pushButton_discard_episode = QPushButton(self.groupBox_follow_control)
        self.pushButton_discard_episode.setObjectName(u"pushButton_discard_episode")

        self.gridLayout.addWidget(self.pushButton_discard_episode, 3, 4, 1, 1)

        self.label_2 = QLabel(self.groupBox_follow_control)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout.addWidget(self.label_2, 0, 0, 1, 1)

        self.pushButton_save_episode = QPushButton(self.groupBox_follow_control)
        self.pushButton_save_episode.setObjectName(u"pushButton_save_episode")

        self.gridLayout.addWidget(self.pushButton_save_episode, 3, 3, 1, 1)

        self.lineEdit_save_file_path = QLineEdit(self.groupBox_follow_control)
        self.lineEdit_save_file_path.setObjectName(u"lineEdit_save_file_path")

        self.gridLayout.addWidget(self.lineEdit_save_file_path, 0, 1, 1, 3)

        self.pushButton_browse_save_path = QPushButton(self.groupBox_follow_control)
        self.pushButton_browse_save_path.setObjectName(u"pushButton_browse_save_path")

        self.gridLayout.addWidget(self.pushButton_browse_save_path, 0, 4, 1, 1)

        self.label_task = QLabel(self.groupBox_follow_control)
        self.label_task.setObjectName(u"label_task")

        self.gridLayout.addWidget(self.label_task, 1, 0, 1, 1)

        self.lineEdit_task = QLineEdit(self.groupBox_follow_control)
        self.lineEdit_task.setObjectName(u"lineEdit_task")

        self.gridLayout.addWidget(self.lineEdit_task, 1, 1, 1, 4)

        self.label_recording_format = QLabel(self.groupBox_follow_control)
        self.label_recording_format.setObjectName(u"label_recording_format")

        self.gridLayout.addWidget(self.label_recording_format, 2, 0, 1, 1)

        self.comboBox_recording_format = QComboBox(self.groupBox_follow_control)
        self.comboBox_recording_format.setObjectName(u"comboBox_recording_format")

        self.gridLayout.addWidget(self.comboBox_recording_format, 2, 1, 1, 4)


        self.verticalLayout_2.addLayout(self.gridLayout)


        self.horizontalLayout_2.addLayout(self.verticalLayout_2)


        self.verticalLayout.addWidget(self.groupBox_follow_control)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)

        self.buttonBox = QDialogButtonBox(FollowControlDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Close)

        self.verticalLayout.addWidget(self.buttonBox)

#if QT_CONFIG(shortcut)
        self.label_task.setBuddy(self.lineEdit_task)
        self.label_recording_format.setBuddy(self.comboBox_recording_format)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(FollowControlDialog)

        QMetaObject.connectSlotsByName(FollowControlDialog)
    # setupUi

    def retranslateUi(self, FollowControlDialog):
        FollowControlDialog.setWindowTitle(QCoreApplication.translate("FollowControlDialog", u"Follow Control", None))
        self.groupBox_follow_control.setTitle(QCoreApplication.translate("FollowControlDialog", u"Follow Control", None))
        self.label_follow_hint.setText(QCoreApplication.translate("FollowControlDialog", u"\u8fde\u63a5\u4e3b\u624b\u3001\u4ece\u624b\u548c\u7075\u5de7\u624b\u540e\u53ef\u542f\u52a8\u8ddf\u968f", None))
        self.pushButton_start_follow.setText(QCoreApplication.translate("FollowControlDialog", u"Start Follow", None))
        self.label_follow_interval.setText(QCoreApplication.translate("FollowControlDialog", u"Interval (ms)", None))
        self.lineEdit_follow_rate.setText(QCoreApplication.translate("FollowControlDialog", u"20", None))
        self.pushButton_slave_home_pos.setText(QCoreApplication.translate("FollowControlDialog", u"Home", None))
        self.pushButton_start_recod.setText(QCoreApplication.translate("FollowControlDialog", u"StartRecod", None))
        self.pushButton_stop_recod.setText(QCoreApplication.translate("FollowControlDialog", u"StopRecod", None))
        self.pushButton_discard_episode.setText(QCoreApplication.translate("FollowControlDialog", u"Discard episode", None))
        self.label_2.setText(QCoreApplication.translate("FollowControlDialog", u"Save path", None))
        self.pushButton_save_episode.setText(QCoreApplication.translate("FollowControlDialog", u"Save episode", None))
        self.pushButton_browse_save_path.setText(QCoreApplication.translate("FollowControlDialog", u"Browse...", None))
        self.label_task.setText(QCoreApplication.translate("FollowControlDialog", u"Task", None))
#if QT_CONFIG(tooltip)
        self.lineEdit_task.setToolTip(QCoreApplication.translate("FollowControlDialog", u"\u6bcf\u6761 episode \u4f7f\u7528\u5f00\u59cb\u91c7\u96c6\u65f6\u586b\u5199\u7684\u4efb\u52a1\u63cf\u8ff0\uff1b\u4fdd\u5b58\u6216\u4e22\u5f03\u540e\u53ef\u4fee\u6539\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.lineEdit_task.setPlaceholderText(QCoreApplication.translate("FollowControlDialog", u"\u4f8b\u5982\uff1a\u5c06\u7ea2\u8272\u65b9\u5757\u653e\u5165\u76d2\u5b50", None))
        self.label_recording_format.setText(QCoreApplication.translate("FollowControlDialog", u"Format", None))
#if QT_CONFIG(tooltip)
        self.comboBox_recording_format.setToolTip(QCoreApplication.translate("FollowControlDialog", u"\u9009\u62e9 LeRobot \u6570\u636e\u96c6\u683c\u5f0f\uff1b\u4fdd\u5b58\u6216\u4e22\u5f03\u672c\u6761 episode \u540e\u53ef\u5207\u6362\u3002", None))
#endif // QT_CONFIG(tooltip)
    # retranslateUi

