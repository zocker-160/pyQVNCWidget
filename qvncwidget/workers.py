# Shamelessly copied from https://github.com/bordaigorl/rmview/blob/vnc/src/rmview/workers.py (GPL v3)

from PyQt5.QtCore import (
    QObject,
    QRunnable,
    QThread,
    pyqtSignal,
    pyqtSlot
)
from PyQt5.QtGui import (
    QImage,
    QPainter
)



from twisted.internet import reactor
from twisted.application import internet

from .rfb import *
import logging

log = logging.getLogger('QVNCWidget worker')


class FBWSignals(QObject):
    onFatalError = pyqtSignal(Exception)
    onNewFrame = pyqtSignal(QImage)


class RFB(RFBClient):
    IMG_FORMAT = QImage.Format_RGB32

    img: QImage = None
    painter: QPainter = None

    def vncConnectionMade(self):
        self.signals = self.factory.signals

        self.setPixelFormat(
            bpp=32, depth=32,
            redshift=16, greenshift=8, blueshift=0
        )
        self.setEncodings([RAW_ENCODING])

        time.sleep(0.1)  # get first image without artifacts
        print("QT: SENDING FB REQUEST on start")
        self.framebufferUpdateRequest()

    def vncRequestPassword(self):
        if not self.factory.password:
            self.signals.onFatalError.emit(
                Exception("Password needed, but none specified!")
            )
        else:
            self.sendPassword(self.factory.password)

    def vncAuthFailed(self, reason):
        self.factory.signals.onFatalError.emit(
            Exception(f"Could not connect: {reason}")
        )

    def commitUpdate(self, rectangles=None):
        #print("QT: SENDING FB REQUEST on update")
        self.signals.onNewFrame.emit(self.img)
        self.framebufferUpdateRequest(incremental=1)

    def updateRectangle(self, x, y, width, height, data):
        #print("QT: got image data", width, height)
        if not self.img and not self.painter:
            self.img = QImage(data, width, height,  width * self.bypp, self.IMG_FORMAT)
            self.painter = QPainter(self.img)

            # save raw data for debugging
            #with open(f"{width}_{height}.raw", "wb") as rawimage:
            #    rawimage.write(data)
        else:
            self.painter.drawImage(
                x, y,
                QImage(data, width, height, width * self.bypp, self.IMG_FORMAT)
            )
        #self.img = QImage(data, width, height, QImage.Format_RGB32)
        #self.painter.drawImage(x, y, self.img)


class VNCFactory(RFBFactory):
    protocol = RFB

    def __init__(self, signals, password):
        super(VNCFactory, self).__init__()
        self.signals = signals
        self.password = password

    def clientConnectionLost(self, connector, reason):
        log.warning("Connection lost: %s", reason.getErrorMessage())
        #connector.connect()

    def clientConnectionFailed(self, connector, reason):
        self.signals.onFatalError.emit(
            Exception("Connection failed: " + str(reason))
        )
        reactor.callFromThread(reactor.stop)


class FrameBufferWorker(QThread):
    _stop = False

    def __init__(self, hostname, port, password):
        super(FrameBufferWorker, self).__init__()
        self.hostname = hostname
        self.port = port
        self.password = password

        self.signals = FBWSignals()

    def stop(self):
        self._stop = True
        log.info("Stopping framebuffer thread...")
        reactor.callFromThread(reactor.stop)
        log.info("Framebuffer thread stopped")

    @pyqtSlot()
    def run(self):
        while not self._stop:
            try:
                self.vncClient = internet.TCPClient(
                    self.hostname, self.port, VNCFactory(self.signals, self.password)
                )
                self.vncClient.startService()
                reactor.run(installSignalHandlers=0)
            except Exception as e:
                log.error(e)
