#! /usr/bin/env python3

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtGui import QKeyEvent, QMouseEvent, QCursor, QPixmap
from qvncwidget import QVNCWidget

class Window(QMainWindow):
    def __init__(self, app: QApplication):
        super(Window, self).__init__()

        self.app = app
        self.initUI()

        # local cursor shape on this application
        pixmap = QPixmap(2,2)
        pixmap.fill(Qt.white)
        myCursor = QCursor(pixmap)
        QApplication.setOverrideCursor(myCursor)

    def initUI(self):
        self.setWindowTitle("QVNCWidget")

        self.vnc = QVNCWidget(
            parent=self,
            host="127.0.0.1", port=5900,
            password="1234",
            mouseTracking=True
        )
        self.setCentralWidget(self.vnc)
        self.vnc.onInitialResize.connect(self.resize)
        self.vnc.start()

    def keyPressEvent(self, ev: QKeyEvent):
        self.vnc.onKeyPress.emit(ev)

    def keyReleaseEvent(self, ev: QKeyEvent):
        self.vnc.onKeyRelease.emit(ev)

app = QApplication(sys.argv)
window = Window(app)
window.resize(800, 600)
window.show()

sys.exit(app.exec_())
