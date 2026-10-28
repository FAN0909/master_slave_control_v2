# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'MainWindow.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QGroupBox, QHBoxLayout,
    QMainWindow, QMenuBar, QPlainTextEdit, QPushButton,
    QSizePolicy, QSpacerItem, QStatusBar, QVBoxLayout,
    QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1214, 880)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.groupBox_log = QGroupBox(self.centralwidget)
        self.groupBox_log.setObjectName(u"groupBox_log")
        self.groupBox_log.setGeometry(QRect(20, 640, 881, 156))
        self.groupBox_log.setMinimumSize(QSize(0, 100))
        self.verticalLayout_4 = QVBoxLayout(self.groupBox_log)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.horizontalLayout_log_toolbar = QHBoxLayout()
        self.horizontalLayout_log_toolbar.setObjectName(u"horizontalLayout_log_toolbar")
        self.spacer_log = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_log_toolbar.addItem(self.spacer_log)

        self.checkBox_log_autoscroll = QCheckBox(self.groupBox_log)
        self.checkBox_log_autoscroll.setObjectName(u"checkBox_log_autoscroll")
        self.checkBox_log_autoscroll.setChecked(True)

        self.horizontalLayout_log_toolbar.addWidget(self.checkBox_log_autoscroll)

        self.pushButton_clear_log = QPushButton(self.groupBox_log)
        self.pushButton_clear_log.setObjectName(u"pushButton_clear_log")

        self.horizontalLayout_log_toolbar.addWidget(self.pushButton_clear_log)


        self.verticalLayout_4.addLayout(self.horizontalLayout_log_toolbar)

        self.plainTextEdit_log = QPlainTextEdit(self.groupBox_log)
        self.plainTextEdit_log.setObjectName(u"plainTextEdit_log")
        font = QFont()
        font.setFamilies([u"Monospace"])
        font.setPointSize(10)
        self.plainTextEdit_log.setFont(font)
        self.plainTextEdit_log.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.plainTextEdit_log.setReadOnly(True)
        self.plainTextEdit_log.setMaximumBlockCount(2000)

        self.verticalLayout_4.addWidget(self.plainTextEdit_log)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1214, 22))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.groupBox_log.setTitle(QCoreApplication.translate("MainWindow", u"Activity Log", None))
        self.checkBox_log_autoscroll.setText(QCoreApplication.translate("MainWindow", u"Auto Scroll", None))
        self.pushButton_clear_log.setText(QCoreApplication.translate("MainWindow", u"Clear Log", None))
        self.plainTextEdit_log.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Activity logs will appear here...", None))
    # retranslateUi

