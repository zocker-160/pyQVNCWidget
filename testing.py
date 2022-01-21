#! /usr/bin/env python3

import sys
import logging

from PyQt5.QtWidgets import QApplication, QMainWindow
from qvncwidget import QVNCWidget

log = logging.getLogger("testing")

class Window(QMainWindow):
    def __init__(self):
        super(Window, self).__init__()

        self.initUI()

    def initUI(self):
        self.setWindowTitle("QVNCWidget")

        self.vnc = QVNCWidget(
            parent=self,
            host="127.0.0.1", port=5900,
            password="1234"
        )
        self.setCentralWidget(self.vnc)
        self.vnc.start()

logging.basicConfig(
    format="[%(name)s] %(levelname)s: %(message)s", level=logging.DEBUG
)

app = QApplication(sys.argv)
window = Window()
#window.setFixedSize(800, 600)
window.resize(800, 600)
window.show()

sys.exit(app.exec_())
