"""
Example for QVNCWidget using input events from the window
and pass them to the VNC widget (v0.3.0)
"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from qvncwidget import QVNCWidget

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

        # you can disable mouse tracking if desired
        self.vnc.setMouseTracking(False)

        self.vnc.start()

    def keyPressEvent(self, ev):
        self.vnc.keyPressEvent(ev)
        return super().keyPressEvent(ev) # in case you need the signal somewhere else in the window

    def keyReleaseEvent(self, ev):
        self.vnc.keyReleaseEvent(ev)
        return super().keyReleaseEvent(ev) # in case you need the signal somewhere else in the window

    def closeEvent(self, ev):
        self.vnc.stop()
        return super().closeEvent(ev)

app = QApplication(sys.argv)
window = Window()
window.resize(800, 600)
window.show()

sys.exit(app.exec_())