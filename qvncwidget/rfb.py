"""
RFB protocol implementattion, client side.

made by zocker-160 licensed under GPLv3

Reference:
http://www.realvnc.com/docs/rfbproto.pdf

https://github.com/rfbproto/rfbproto/blob/master/rfbproto.rst
"""

from qvncwidget.rfbhelpers import RFBPixelformat, RFBRectangle
from qvncwidget.rfbdes import RFBDes
import qvncwidget.rfbconstants as c
import qvncwidget.easystruct as es

from threading import Thread
import logging
import socket
from socket import SHUT_RDWR
import struct as s
import time

class RFBUnexpectedResponse(Exception):
    pass
class RFBNoResponse(Exception):
    pass
class RFBUnknownVersion(Exception):
    pass
class RFBHandshakeFailed(Exception):
    pass
class VNCAuthentificationFailed(Exception):
    pass

SUPPORTED_VERSIONS = [
    (3,3)
]
KNOWN_VERSIONS = [
    (3.3), (3,6), (3,7), (3,8),
    (4,0), (4,1),
    (5,0)
]
"""
3.3: official minimum version
3.6: UltraVNC
3.7: official
3.8: official
4.0: Intel AMT KVM
4.1: RealVNC 4.6
5.0: RealVNC 5.3
"""

MAX_BUFF_SIZE: int = 10*1024*1024 # 10MB

class RFBClient:

    log = logging.getLogger("RFB Client")
    logc = logging.getLogger("RFB -> Server")
    logs = logging.getLogger("RFB -> Client")

    pixformat: RFBPixelformat
    numRectangles = 0
    rectanglePositions = list() # list[RFBRectangle]

    _stop = False
    _requestFrameBufferUpdate = False
    _incrementalFrameBufferUpdate = True

    def __init__(self, host, port=5900,
                password: str=None,
                sharedConnection=True,
                keepRequesting=True,
                requestIncremental=True,
                daemonThread=False):
        self.host = host
        self.port = port
        self.password = password
        self.sharedConn = sharedConnection
        self._requestFrameBufferUpdate = keepRequesting
        self._incrementalFrameBufferUpdate = requestIncremental

        self._mainLoop = Thread(
            target=self._mainRequestLoop, daemon=daemonThread)

    def __recv(self, expectedSize: int =None, maxSize=MAX_BUFF_SIZE) -> bytes:
        if not expectedSize:
            buffer = self.connection.recv(4096)
        else:
            buffer = self.connection.recv(expectedSize, socket.MSG_WAITALL)    
        
        if len(buffer) <= 50:
            self.logs.debug(f"len: {len(buffer)} | {buffer}")
        else:
            self.logs.debug(f"{len(buffer)} Bytes | {len(buffer)//1024} KB")

        return buffer

    def __send(self, data: bytes):
        self.connection.send(data)
        self.logc.debug(data)

    def __start(self):
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection.connect( (self.host, self.port) )
        self._handleInitial()

    def __close(self):
        self.log.debug("Closing connection")
        if self._mainLoop.is_alive() and not self._stop:
            self._stop = True
            try:
                self.connection.shutdown(SHUT_RDWR)
                self.connection.close()
            except OSError:
                self.log.debug("TCP Connection already closed")
            #self._mainLoop.join() # this causes infinite blocking, why?

    def _handleInitial(self):
        buffer = self.__recv(12)

        if b'\n' in buffer and buffer.startswith(b'RFB'):
            maj, min = [int(x) for x in buffer[3:-1].split(b'.')]
            self.log.info(f"RFB from server: {maj}.{min}")

            if (maj, min) in KNOWN_VERSIONS:
                if (maj, min) not in SUPPORTED_VERSIONS:
                    # request highest supported version
                    # TODO: requested version must not be higher than
                    # the one requested by the server
                    maj, min = SUPPORTED_VERSIONS[-1]
            else:
                self.log.error(f"unknown RFB version {maj}.{min}")
                self.__close()
        else:
            self.__close()
            raise RFBUnknownVersion(buffer)

        self.version_maj, self.version_min = maj, min

        # request supported RFB version
        self.__send(f"RFB 00{maj}.00{min}\n".encode())
        self.log.info("VNC connected")

        if min == 3:
            self._handleAuth33(self.__recv(4))

    def _handleAuth33(self, data: bytes):
        """
        Handle security handshake for protocol version 3.3.
        In this version, the server decides the protocol (failed, none or VNCAuth)
        """
        auth = es.return_uint32_val(data, True)
        if auth == c.AUTH_FAIL:
            self._handleConnFailed(self.__recv(4))
        elif auth == c.AUTH_NONE:
            self._doClientInit()
        elif auth == c.AUTH_VNCAUTH:
            self._handleVNCAuth(self.__recv(16))
        else:
            self.__close()
            raise RFBUnexpectedResponse(f"Unknown auth response {auth}")

    def _doClientInit(self):
        shared = 1 if self.sharedConn else 0
        self.__send(es.return_uint8_bytes(shared, True))
        self._handleServerInit(self.__recv(24))

    def _handleServerInit(self, data: bytes):
        try:
            self.vncWidth, self.vncHeight, pixformat, namelen = s.unpack("!HH16sI", data)
        except s.error as e:
            self.log.error("Handshake failed!")
            raise RFBHandshakeFailed(e)

        self.desktopname = self.__recv(namelen).decode()

        pixformatData = s.unpack("!BBBBHHHBBBxxx", pixformat)
        self.pixformat = RFBPixelformat(*pixformatData)

        self.log.debug(f"PIXFORMAT: {self.pixformat}")

        self.onConnectionMade()
        # enter main request loop
        
        self._mainLoop.start()
        #self._mainRequestLoop()

    def _handleVNCAuth(self, data: bytes):
        self._VNCAuthChallenge = data

        self.log.info("Requesting password")
        self.vncRequestPassword()
        self._handleVNCAuthResult(self.__recv(4))

    def _handleVNCAuthResult(self, data: bytes):
        try:
            result = es.return_uint32_val(data)
        except s.error as e:
            raise VNCAuthentificationFailed(f"Authentication failed ({str(e)})")
        self.log.debug(f"Auth result {result}")

        if result == c.SMSG_AUTH_OK:
            self._doClientInit()
        elif result == c.SMSG_AUTH_FAIL:
            if self.version_min > 7:
                self._handleVNCAuthError(self.__recv(4))
            else:
                raise VNCAuthentificationFailed("Authentication failed")
        elif result == c.SMSG_AUTH_TOOMANY:
            raise VNCAuthentificationFailed("Too many login attempts")
        else:
            self.log.error(f"Unknown Auth response ({result})")

    def _handleVNCAuthError(self, data: bytes):
        waitfor = es.return_uint32_val(data)
        raise VNCAuthentificationFailed(
            f"Authentication failed ({self.__recv(waitfor)})")

    def _handleConnFailed(self, data: bytes):
        waitfor = es.return_uint32_val(data)
        raise RFBHandshakeFailed(self.__recv(waitfor))

    # ------------------------------------------------------------------
    ## Main request loop
    # ------------------------------------------------------------------

    def _mainRequestLoop(self):
        # first request is non incremental
        time.sleep(0.2)
        self.framebufferUpdateRequest(incremental=False)
        while not self._stop:
            try:
                self._handleConnection(self.__recv(1))
            except s.error as e:
                self.log.exception(str(e))
            except Exception as e:
                self.onFatalError(e)
            #print("AAA")
            if self._requestFrameBufferUpdate:
                self.framebufferUpdateRequest(
                    incremental=self._incrementalFrameBufferUpdate)
            #print("BBB")

    # ------------------------------------------------------------------
    ## Server -> Client messages
    # ------------------------------------------------------------------

    def _handleConnection(self, data: bytes):
        msgid = es.return_uint8_val(data)
        if msgid == c.SMSG_FBUPDATE:
            # Framebuffer Update
            self._handleFramebufferUpdate(self.__recv(3))
        elif msgid == c.SMSG_BELL:
            # bell
            self.onBell()
        elif msgid == c.SMSG_SERVERCUTTEXT:
            # server cut text
            self._handleServerCutText(self.__recv(7))
        elif msgid == c.SMSG_SETCOLORMAP:
            # set color map entries
            pass
        else:
            self.log.warning(f"Unknown message type recieved (id {msgid})")
            raise RFBUnexpectedResponse

    def _handleServerCutText(self, data: bytes):
        datalength = s.unpack("!xxxI", data)[0]
        data = self.__recv(datalength)

        self.log.debug(f"Server clipboard: {data}")
        # TODO: create callback

    def _handleFramebufferUpdate(self, data: bytes):
        self.numRectangles = s.unpack("!xH", data)[0]

        self.log.debug(f"numRectangles: {self.numRectangles}")

        self.onBeginUpdate()
        self._handlePostFramebufferUpdate()
        
    def _handlePostFramebufferUpdate(self):
        if self.numRectangles > 0:
            self._handleRectangle(self.__recv(12))
        else:
            self.onFramebufferUpdateFinished()
            #self._handleConnection(self.__recv(1))

    def _handleRectangle(self, data: bytes):
        xPos, yPos, width, height, encoding = s.unpack("!HHHHI", data)

        self.numRectangles -= 1

        rect = RFBRectangle(xPos, yPos, width, height)
        #self.rectanglePositions.append(rect)

        if encoding == c.RAW_ENCODING:
            self.log.debug(f"expected size: {width*height*self.pixformat.bytespp}")
            self._decodeRAW(
                self.__recv(expectedSize=width*height*self.pixformat.bytespp),
                rect
            )
        else:
            self.log.error(f"Unknown encoding received ({encoding})")
            self._handlePostFramebufferUpdate()

    # ------------------------------------------------------------------
    ## Image decoding stuff
    # ------------------------------------------------------------------        

    def _decodeRAW(self, data: bytes, rectangle: RFBRectangle):
        self.onRectangleUpdate(*rectangle.asTuple(), data)
        self._handlePostFramebufferUpdate()

    # ------------------------------------------------------------------
    ## Client -> Server messages
    # ------------------------------------------------------------------

    def setPixelFormat(self, pixelformat: RFBPixelformat):
        self.pixformat = pixelformat
        pformat = s.pack("!BBBBHHHBBBxxx", *pixelformat.asTuple())
        self.__send(s.pack("!Bxxx16s", c.CMSG_SETPIXELFORMAT, pformat))

    def setEncodings(self, encodings: list):
        self.__send(s.pack("!BxH", c.CMSG_SETENCODINGS, len(encodings)))
        for encoding in encodings:
            self.__send(es.return_sint32_bytes(encoding, True))

    def framebufferUpdateRequest(self,
        xPos=0, yPos=0, width=None, height=None,
        incremental=False):

        if not width: width = self.vncWidth - xPos
        if not height: height = self.vncHeight - yPos
        inc = 1 if incremental else 0

        self.__send(s.pack(
            "!BBHHHH",
            c.CMSG_FBUPDATEREQ, inc,
            xPos, yPos, width, height))

    def keyEvent(self, key, down=1):
        """
        For most ordinary keys, the "keysym" is the same as the corresponding ASCII value.
        Other common keys are shown in the KEY_ constants
        """
        self.log.debug(f'keyEvent: {key}, {"down" if down else "up"}')

        self.__send(s.pack(
            "!BBxxI",
            c.CMSG_KEYEVENT, down, key))

    def pointerEvent(self, x, y, buttommask=0):
        """
        Indicates either pointer movement or a pointer button press or release. The pointer is
           now at (x-position, y-position), and the current state of buttons 1 to 8 are represented
           by bits 0 to 7 of button-mask respectively, 0 meaning up, 1 meaning down (pressed)
        """
        self.log.debug(f"pointerEvent: {x}, {y}, {buttommask}")

        self.__send(s.pack(
            "!BBHH",
            c.CMSG_POINTEREVENT, buttommask, x, y))

    # ------------------------------------------------------------------
    ## Direct Calls
    # ------------------------------------------------------------------

    def startConnection(self):
        Thread(target=self.__start, daemon=True).start()
    
    def sendPassword(self, password):
        if type(password) is str:
            password = password.encode("ascii")
        password = (password + bytes(8))[:8]
        des = RFBDes(password)
        self.__send(des.encrypt(self._VNCAuthChallenge))

    def reconnect(self):
        self.closeConnection()
        self.startConnection()

    def closeConnection(self):
        self.__close()

    # ------------------------------------------------------------------
    ## Callbacks
    # ------------------------------------------------------------------

    def onConnectionMade(self):
        """
        connection is initialized and ready.
        typicaly, the pixel format and encoding is set here.

        set with setPixelFormat()
        and setEncodings()

        the RFB main update loop will start after this function is done
        """
        #self.setPixelFormat(RFBPixelformat.getRGB32())
        raise NotImplementedError

    def onBeginUpdate(self):
        """
        called before a series of updateRectangle(),
        copyRectangle() or fillRectangle().
        """

    def onRectangleUpdate(self,
            x: int, y: int, width: int, height: int, data: bytes):
        """
        new bitmap data. data are bytes in the pixel format set
        up earlier.
        """
        #print(x, y, width, height, len(data))
        #print(self.numRectangles)

    def onFramebufferUpdateFinished(self):
        """
        called after a series of updateRectangle(), copyRectangle()
        or fillRectangle() are finished.
        """

    def onBell(self):
        """
        a bell, yes that's right a BELL
        """

    def vncRequestPassword(self):
        """
        a password is needed to log on, use sendPassword() to
        send one.
        """
        if not self.password:
            raise VNCAuthentificationFailed("Password is missing!")
        else:
            self.sendPassword(self.password)

    def onFatalError(self, error: Exception):
        """
        called when fatal error occurs
        which caused the main loop to crash

        you can try to reconnect here with reconnect()
        """
        raise error

#logging.basicConfig(level=logging.DEBUG)
#cl = RFBClient("127.0.0.1", 5900)
