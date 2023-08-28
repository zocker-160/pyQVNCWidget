"""
Example for QVNCWidget using input events from the widget (v0.3.0)
"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from ..qvncwidget import QVNCWidget

class Window(QMainWindow):
    def __init__(self):
        super(Window, self).__init__()

        self.setWindowTitle("QVNCWidget")

        self.vnc = QVNCWidget(
            parent=self,
            host="127.0.0.1", port=5900,
            password="1234",
            readOnly=False
        )

        self.setCentralWidget(self.vnc)
        # we need to request focus otherwise we will not get keyboard input events
        self.vnc.setFocus()

        # you can disable mouse tracking if desired
        self.vnc.setMouseTracking(False)

        self.vnc.start()

    def closeEvent(self, ev):
        self.vnc.stop()
        return super().closeEvent(ev)

app = QApplication(sys.argv)
window = Window()
window.resize(800, 600)
window.show()

sys.exit(app.exec_())