
from PyQt5.QtCore import QSize, pyqtSignal
from PyQt5.QtGui import (
    QImage,
    QPainter,
    QPixmap,
    QResizeEvent
)

from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow
)

from rfb import RFBClient
from rfbhelpers import RFBPixelformat

class QVNCWidget(QLabel, RFBClient):
    
    IMG_FORMAT = QImage.Format_RGB32

    onInitialResize = pyqtSignal(QSize)

    def __init__(self, parent, host, port=5900, password: str=None):
        super().__init__(
            parent=parent,
            host=host,
            port=port,
            password=password,
            daemonThread=True
        )
        self.image: QImage = None
        self.painter: QPainter = None

    def onConnectionMade(self):
        self.onInitialResize.emit(QSize(self.vncWidth, self.vncHeight))
        self.setPixelFormat(RFBPixelformat.getRGB32())

    def onRectangleUpdate(self,
            x: int, y: int, width: int, height: int, data: bytes):
        #print(x, y, width, height, len(data))
        #print(self.numRectangles)

        img = QImage(data,
                        width, height, width*self.pixformat.bytespp,
                        self.IMG_FORMAT)

        if not self.image and not self.painter:
            self.image = img
            self.painter = QPainter(self.image)
        else:
            self.painter.drawImage(x, y, img)

    def onFramebufferUpdateFinished(self):
        if self.image:
            self.setPixmap(QPixmap.fromImage(self.image))

    def onFatalError(self, error: Exception):
        raise error
        logging.exception(str(error))
        self.reconnect()

    def __del__(self):
        self.closeConnection()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.closeConnection()
        self.deleteLater()

### just an example

class Window(QMainWindow):
    def __init__(self):
        super(Window, self).__init__()

        self.initUI()

    def initUI(self):
        self.setWindowTitle("TEST")
        self.vnc = QVNCWidget(
            parent=self,
            host="10.0.12.186",
        )
        self.setCentralWidget(self.vnc)

        self.vnc.onInitialResize.connect(self.resize)

        self.vnc.startConnection()
    
import sys
import logging

logging.basicConfig(level=logging.DEBUG)

app = QApplication(sys.argv)

win = Window()
win.show()

sys.exit(app.exec_())
