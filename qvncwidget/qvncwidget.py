import logging
from threading import Semaphore
from PyQt5.QtCore import (
    QSize,
    Qt,
    pyqtSignal
)
from PyQt5.QtGui import (
    QImage,
    QPaintEvent,
    QPainter,
    QPixmap,
    QResizeEvent,
    QSurface
)

from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QWidget
)

from qvncwidget.rfb import RFBClient
from qvncwidget.rfbhelpers import RFBPixelformat

log = logging.getLogger("QVNCWidget")

class QVNCWidget(QLabel, RFBClient):
    
    IMG_FORMAT = QImage.Format_RGB32

    onInitialResize = pyqtSignal(QSize)
    onUpdatePixmap = pyqtSignal(int, int, int, int, bytes)
    onSetPixmap = pyqtSignal()


    def __init__(self, parent, host, port=5900, password: str=None):
        super().__init__(
            parent=parent,
            host=host,
            port=port,
            password=password,
            daemonThread=True
        )
        #import faulthandler
        #faulthandler.enable()
        self.screen: QImage = None

        self.onUpdatePixmap.connect(self._updateImage)
        self.onSetPixmap.connect(self._setImage)

    def start(self):
        self.startConnection()

    def stop(self):
        self.closeConnection()
        if self.screenPainter: self.screenPainter.end()

    def onConnectionMade(self):
        self.onInitialResize.emit(QSize(self.vncWidth, self.vncHeight))
        self.setPixelFormat(RFBPixelformat.getRGB32())

    def onRectangleUpdate(self,
            x: int, y: int, width: int, height: int, data: bytes):
        #img = QImage(data, width, height, self.IMG_FORMAT)
        self.onUpdatePixmap.emit(x, y, width, height, data)

    def onFramebufferUpdateFinished(self):
        self.onSetPixmap.emit()
        return

        if self.pixmap:
            #self.setPixmap(QPixmap.fromImage(self.image))
            self.resizeEvent(None)

    def onFatalError(self, error: Exception):
        log.error(str(error))
        #logging.exception(str(error))
        #self.reconnect()

    def _updateImage(self, x: int, y: int, width: int, height: int, data: bytes):
        if not self.screen:
            self.screen = QImage(width, height, self.IMG_FORMAT)
            self.screen.fill(Qt.red)
            self.screenPainter = QPainter(self.screen)

        #self.painter.beginNativePainting()
        #self.painter.drawPixmapFragments()

        #with open("/tmp/images/test.raw", "wb") as f:
        #    f.write(data)
        
        #p = QPainter(self.screen)
        self.screenPainter.drawImage(
            x, y, QImage(data, width, height, self.IMG_FORMAT))
        #p.end()

        #self.repaint()
        #self.update()

    def _drawPixmap(self, x: int, y: int, pix: QPixmap):
        #self.paintLock.acquire()
        self.pixmap = pix

        if not self.painter:
            self.painter = QPainter(self.pixmap)
        else:
            print("DRAW PIXMAP:", x, y, self.pixmap, self.painter, pix, pix.isNull())
            self.painter.drawPixmap(x, y, self.pixmap)
        #self.paintLock.release()

    def _drawPixmap2(self, x: int, y: int, pix: QPixmap, data: bytes):
        if not self.pixmap or (
            x == 0 and y == 0 and
            pix.width() == self.pixmap.width() and pix.height() == self.pixmap.height()):

            self.pixmap = pix.copy()
            self._setPixmap()
            return
        
        import time
        print("DRAW PIXMAP:", x, y, self.pixmap.width(), self.pixmap.height(), pix.width(), pix.height())
        _t = time.time()
        #self.pixmap.save(f"/tmp/images/imgP_{_t}", "jpg")
        #with open(f"/tmp/images/img_{_t}.raw", "wb") as f:
        #    f.write(data)
        #pix.save(f"/tmp/images/img_{_t}", "jpg")

        painter = QPainter(self.pixmap)
        painter.drawPixmap(x, y, pix)
        painter.end()
        #self._setPixmap()

    def _setPixmap(self):
        if self.pixmap:
            self.setPixmap(
                self.pixmap.scaled(
                    self.width(), self.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )

    def _setImage(self):
        if self.screen:
            self.setPixmap(QPixmap.fromImage(
                self.screen.scaled(
                    self.width(), self.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            ))

    def paintEvent(self, a0: QPaintEvent):
        return super().paintEvent(a0)
        if not self.screen:
            self.screen = QImage(self.size(), self.IMG_FORMAT)
            self.screen.fill(Qt.red)
            self.screenPainter = QPainter(self.screen)

        p = QPainter()
        p.begin(self)
        p.drawImage(0, 0,
            self.screen.scaled(
                self.width(), self.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))
        p.end()

    def resizeEvent(self, a0: QResizeEvent):
        return super().resizeEvent(a0)
        if self.pixmap and False:
            x, y = self.width(), self.height()
            self.setPixmap(
                self.pixmap.scaled(
                    x, y,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )

    def __del__(self):
        self.stop()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        self.deleteLater()
