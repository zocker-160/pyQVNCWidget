
import sys
from PIL.ImageQt import QImage
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow
from ..qvncwidget import QVNCWidget

class Window(QMainWindow):
    def __init__(self):
        super(Window, self).__init__()

        self.initUI()

    def initUI(self):
        self.setWindowTitle("QVNCWidget")

        #self.test = QLabel(self)
        #self.setCentralWidget(self.test)
        #self.test.setPixmap(QPixmap.fromImage(QImage("800px-TuxFlat.svg.png")))

        self.vnc = QVNCWidget(self, "127.0.0.1", 5900, "1234")
        #self.vnc = QVNCWidget(self, "10.10.21.1", 5900, "1234")
        #self.vnc = QVNCWidget(self, "127.0.0.1", 5901, "vncpasswd")
        self.setCentralWidget(self.vnc)
        self.vnc.start()

app = QApplication(sys.argv)
window = Window()
#window.setFixedSize(800, 600)
window.resize(800, 600)
window.show()

sys.exit(app.exec_())
