
from PyQt5 import QtCore
from PyQt5.QtGui import (
    QImage,
    QPixmap,
    QResizeEvent
)

from PyQt5.QtWidgets import (
    QLabel
)

from .workers import FrameBufferWorker

class QVNCWidget(QLabel):
    def __init__(self, parent, host, port=5900, password=""):
        super().__init__(parent)

        self.host = host
        self.port = port

        self.Image: QPixmap = None
        self.VNCClient = FrameBufferWorker(host, port, password)

        self.VNCClient.signals.onNewFrame.connect(self.setImage)
        self.VNCClient.signals.onFatalError.connect(self._onFatalError)

    def start(self):
        self.VNCClient.start()

    def resizeEvent(self, a0: QResizeEvent):
        if self.Image:
            x, y = self.width(), self.height()
            self.setPixmap(self.Image.scaled(
                    x, y, 
                    QtCore.Qt.KeepAspectRatio,
                    QtCore.Qt.SmoothTransformation
                )
            )

    def setImage(self, image):
        #print("QT Widget: got new image!", image.size())
        if image:
            if type(image) == QImage:
                self.Image = QPixmap.fromImage(image)
            elif type(image) == QPixmap:
                self.Image = image
            else:
                print("Unknown image type")
                print(type(image))

            self.resizeEvent(None)


    def _onFatalError(self, error):
        print(error)

    def __del__(self):
        self.VNCClient.stop()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.VNCClient.stop()

    def stop(self):
        self.VNCClient.stop()
