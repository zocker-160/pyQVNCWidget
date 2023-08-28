"""
Minimal example for QVNCWidget (v0.3.0)
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
            readOnly=True
        )

        self.setCentralWidget(self.vnc)

        # if you want to resize the window to the resolution of the 
        # VNC remote device screen, you can do this
        self.vnc.onInitialResize.connect(self.resize)

        self.vnc.start()

    def closeEvent(self, ev):
        self.vnc.stop()
        return super().closeEvent(ev)

app = QApplication(sys.argv)
window = Window()
window.resize(800, 600)
window.show()

sys.exit(app.exec_())