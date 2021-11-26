"""
RFB protocol implementattion, client side.

Override RFBClient and RFBFactory in your application.
See vncviewer.py for an example.

Reference:
http://www.realvnc.com/docs/rfbproto.pdf

https://github.com/rfbproto/rfbproto/blob/master/rfbproto.rst

(C) 2003 cliechti@gmx.net

MIT License
"""

import sys
from struct import pack, unpack

from twisted.python import usage
from twisted.internet.protocol import Factory, Protocol
from twisted.internet import protocol
from twisted.application import internet, service

import pyDes
import time

#~ from twisted.internet import reactor


#encoding-type
#for SetEncodings()
RAW_ENCODING =                  0
COPY_RECTANGLE_ENCODING =       1
RRE_ENCODING =                  2
CORRE_ENCODING =                4
HEXTILE_ENCODING =              5
ZLIB_ENCODING =                 6
TIGHT_ENCODING =                7
ZLIBHEX_ENCODING =              8 
ZRLE_ENCODING =                 16
#0xffffff00 to 0xffffffff tight options
CURSOR_ENCODING =				-239	# Cursor position pseudo-encoding

#keycodes
#for KeyEvent()
KEY_BackSpace = 0xff08
KEY_Tab =       0xff09
KEY_Return =    0xff0d
KEY_Escape =    0xff1b
KEY_Insert =    0xff63
KEY_Delete =    0xffff
KEY_Home =      0xff50
KEY_End =       0xff57
KEY_PageUp =    0xff55
KEY_PageDown =  0xff56
KEY_Left =      0xff51
KEY_Up =        0xff52
KEY_Right =     0xff53
KEY_Down =      0xff54
KEY_F1 =        0xffbe
KEY_F2 =        0xffbf
KEY_F3 =        0xffc0
KEY_F4 =        0xffc1
KEY_F5 =        0xffc2
KEY_F6 =        0xffc3
KEY_F7 =        0xffc4
KEY_F8 =        0xffc5
KEY_F9 =        0xffc6
KEY_F10 =       0xffc7
KEY_F11 =       0xffc8
KEY_F12 =       0xffc9
KEY_F13 =       0xFFCA
KEY_F14 =       0xFFCB
KEY_F15 =       0xFFCC
KEY_F16 =       0xFFCD
KEY_F17 =       0xFFCE
KEY_F18 =       0xFFCF
KEY_F19 =       0xFFD0
KEY_F20 =       0xFFD1
KEY_ShiftLeft = 0xffe1
KEY_ShiftRight = 0xffe2
KEY_ControlLeft = 0xffe3
KEY_ControlRight = 0xffe4
KEY_MetaLeft =  0xffe7
KEY_MetaRight = 0xffe8
KEY_AltLeft =   0xffe9
KEY_AltRight =  0xffea

KEY_Scroll_Lock = 0xFF14
KEY_Sys_Req =   0xFF15
KEY_Num_Lock =  0xFF7F
KEY_Caps_Lock = 0xFFE5
KEY_Pause =     0xFF13
KEY_Super_L =   0xFFEB
KEY_Super_R =   0xFFEC
KEY_Hyper_L =   0xFFED
KEY_Hyper_R =   0xFFEE

KEY_KP_0 =      0xFFB0
KEY_KP_1 =      0xFFB1
KEY_KP_2 =      0xFFB2
KEY_KP_3 =      0xFFB3
KEY_KP_4 =      0xFFB4
KEY_KP_5 =      0xFFB5
KEY_KP_6 =      0xFFB6
KEY_KP_7 =      0xFFB7
KEY_KP_8 =      0xFFB8
KEY_KP_9 =      0xFFB9
KEY_KP_Enter =  0xFF8D


# Authentication protocol types
AUTH_FAIL =		0
AUTH_NONE = 	1
AUTH_VNCAUTH = 	2


# Server message types
SMSG_FBUPDATE = 		0
SMSG_SETCOLORMAP = 		1
SMSG_BELL = 			2
SMSG_SERVERCUTTEXT = 	3


# Client message types
CMSG_SETPIXELFORMAT = 	0
CMSG_SETENCODINGS =		2
CMSG_FBUPDATEREQ = 		3
CMSG_KEYEVENT =			4
CMSG_POINTEREVENT =		5
CMSG_CLIENTCUTTEXT =	6

class RFBClient(Protocol):
    
    def __init__(self):
        self._packet = []
        self._packet_len = 0
        self._handler = self._handleInitial
        self._already_expecting = 0

    #------------------------------------------------------
    # states used on connection startup
    #------------------------------------------------------

    def _handleInitial(self):
        buffer = b''.join(self._packet)
        if b'\n' in buffer and self._packet_len >= 12:
            if buffer[:3] == b'RFB':
                print("VNC: RFB from server:", buffer)
                maj, min = [int(x) for x in buffer[3:-1].split(b'.')]
                if (maj, min) in [(3,3)]: # supported / implemented versions
                    pass
                elif (maj, min) in [(3,6), (3,7), (3,8), (4,0), (4,1), (5,0)]:
                    """
                    3.3: official
                    3.6: UltraVNC
                    3.7: official
                    3.8: official
                    4.0: Intel AMT KVM
                    4.1: RealVNC 4.6
                    5.0: RealVNC 5.3
                    """
                    # force protocol version 3.3 because 3.7 and up does not work with this client for some fucking reason
                    maj, min = 3, 3
                else:
                    print(f"VNC: ERROR: unknown RFB version {maj}.{min}")
                    self.transport.loseConnection()
            
            buffer = buffer[12:] 

            self.transport.write('RFB {:03d}.{:03d}\n'.format(maj, min).encode())
            self.version_major, self.version_min = maj, min

            print("VNC: connected")
            self._packet[:] = [buffer]
            self._packet_len = len(buffer)
            self._handler = self._handleExpected
            if min == 3:
                self.expect(self._handleAuth33, 4)
            else:
                self.expect(self._handleAuth37, 1)
        else:
            self._packet[:] = [buffer]
            self._packet_len = len(buffer)
    
    def _handleAuth33(self, block):
        """Handle security handshake for protocol version 3.3.
        In this version, the server decides the protocol (failed, none or VNCAuth)"""
        (auth,) = unpack("!I", block)
        #~ print "auth:", auth
        if auth == AUTH_FAIL:
            self.expect(self._handleConnFailed, 4)
        elif auth == AUTH_NONE:
            self._doClientInitialization()
            return
        elif auth == AUTH_VNCAUTH:
            self.expect(self._handleVNCAuth, 16)
        else:
            print("unknown auth response (%d)\n" % auth)

    def _handleAuth37(self, block):
        """Handle security handshake for protocol version 3.7 and upwards.
        In this version the protocol is negotiated with the client.
        This resolves the amount of supported types."""
        print("BLOCK:", block)
        (types,) = unpack("!B", block)
        print("TYPES:", types)
        self.expect(self._handleAuthTypes37, types)
        
    def _handleAuthTypes37(self, auth):
        """Security handshake for version 3.7 upwards. This lists
        and selects a suitable authentication type (highest supported)."""
        print("handleAuthTypes37:", auth)
        time.sleep(1)
        if AUTH_VNCAUTH in auth:
            print("VNCAUTH")
            self.expect(self._handleVNCAuth, 16)
        elif AUTH_NONE in auth:
            print("VNCNONE")
            if self.version_min <= 7:
                self._doClientInitialization()
            else: # 3.8 and upwards
                self.expect(self._handleAuthResult, 4)
            return
        elif AUTH_FAIL in auth:
            print("VNCFAIL")
            self.expect(self._handleConnFailed, 4)
        else:
            print(f"no supported auth types ({auth})\n")
            print(f"no supported auth types ({auth})\n")

    def _handleConnFailed(self, block):
        (waitfor,) = unpack("!I", block)
        self.expect(self._handleConnMessage, waitfor)

    def _handleConnMessage(self, block):
        print("Connection refused: %r\n" % block)


    
    def _handleVNCAuth(self, block):
        self._challenge = block
        print("requesting password")
        self.vncRequestPassword()
        self.expect(self._handleAuthResult, 4)

    def sendPassword(self, password):
        """send password"""
        if type(password) is str:
            password = bytes(password, "ascii")
        pw = (password + bytes(8))[:8]        #make sure its 8 chars long, zero padded
        des = RFBDes(pw)
        response = des.encrypt(self._challenge)
        self.transport.write(response)
    
    def _handleAuthResult(self, block):
        """Handle the server result for authentication."""
        (result,) = unpack("!I", block)
        print("auth result:", result)
        if result == 0:     #OK
            self._doClientInitialization()
            return
        elif result == 1:   #failed
            if self.version_min > 7: # 3.8 and upwards
                self.expect(self._handleAuthError, 4)
            else:
                self.vncAuthFailed("authentication failed")
                self.transport.loseConnection()
        elif result == 2:   #too many (Not in RFC 6143)
            self.vncAuthFailed("too many tries to log in")
            self.transport.loseConnection()
        else:
            print("unknown auth response (%d)\n" % result)
       
    def _handleAuthError(self, block):
        (waitfor,) = unpack("!I", block)
        self.expect(self._handleAuthMessage(self, waitfor))
        
    def _handleAuthMessage(self, block):
        #print("Authentication failed: %2\n", % block)
        self.vncAuthFailed(block)
        self.transport.loseConnection()	
        
    def _doClientInitialization(self):
        self.transport.write(pack("!B", self.factory.shared))
        self.expect(self._handleServerInit, 24)
    
    def _handleServerInit(self, block):
        (self.width, self.height, pixformat, namelen) = unpack("!HH16sI", block)
        (self.bpp, self.depth, self.bigendian, self.truecolor, 
         self.redmax, self.greenmax, self.bluemax,
         self.redshift, self.greenshift, self.blueshift) = \
           unpack("!BBBBHHHBBBxxx", pixformat)
        self.bypp = self.bpp // 8        #calc bytes per pixel
        print("SERVER INIT:", self.bpp, self.depth, self.bigendian, self.truecolor, 
         self.redmax, self.greenmax, self.bluemax,
         self.redshift, self.greenshift, self.blueshift)
        self.expect(self._handleServerName, namelen)
        
    def _handleServerName(self, block):
        self.name = block
        #callback:
        self.vncConnectionMade()
        self.expect(self._handleConnection, 1)

    #------------------------------------------------------
    # Server to client messages
    #------------------------------------------------------
    def _handleConnection(self, block):
        (msgid,) = unpack("!B", block)
        if msgid == SMSG_FBUPDATE:
            self.expect(self._handleFramebufferUpdate, 3)
        elif msgid == SMSG_BELL:
            self.bell()
            self.expect(self._handleConnection, 1)
        elif msgid == SMSG_SERVERCUTTEXT:
            self.expect(self._handleServerCutText, 7)
        # elif msgid == SMSG_SETCOLORMAP:
            # TODO: Implement
        else:
            print("unknown message received (id %d)\n" % msgid)
            self.expect(self._handleConnection, 1)

    def _handleFramebufferUpdate(self, block):
        (self.rectangles,) = unpack("!xH", block)
        self.rectanglePos = []
        self.beginUpdate()
        self._doConnection()
    
    def _doConnection(self):
        if self.rectangles:
            self.expect(self._handleRectangle, 12)
        else:
            self.commitUpdate(self.rectanglePos)
            self.expect(self._handleConnection, 1)
    
    def _handleRectangle(self, block):
        (x, y, width, height, encoding) = unpack("!HHHHI", block)
        if self.rectangles:
            self.rectangles -= 1
            self.rectanglePos.append( (x, y, width, height) )
            if encoding == COPY_RECTANGLE_ENCODING:
                self.expect(self._handleDecodeCopyrect, 4, x, y, width, height)

            elif encoding == RAW_ENCODING:
                self.expect(self._handleDecodeRAW, width*height*self.bypp, x, y, width, height)
            
            elif encoding == HEXTILE_ENCODING:
                self._doNextHextileSubrect(None, None, x, y, width, height, None, None)
            elif encoding == CORRE_ENCODING:
                self.expect(self._handleDecodeCORRE, 4 + self.bypp, x, y, width, height)
            elif encoding == RRE_ENCODING:
                self.expect(self._handleDecodeRRE, 4 + self.bypp, x, y, width, height)
            #~ elif encoding == ZRLE_ENCODING:
                #~ self.expect(self._handleDecodeZRLE, )
            elif encoding == CURSOR_ENCODING:
                self.expect(self._handleDecodeCursor, width*height*self.bypp + ((width+7)//8)*height, x, y, width, height)
            else:
                print("unknown encoding received (encoding %d)\n" % encoding)
                self._doConnection()
        else:
            self._doConnection()

    # ---  RAW Encoding
    
    def _handleDecodeRAW(self, block, x, y, width, height):
        #TODO convert pixel format?
        self.updateRectangle(x, y, width, height, block)
        self._doConnection()
    
    # ---  CopyRect Encoding
    
    def _handleDecodeCopyrect(self, block, x, y, width, height):
        (srcx, srcy) = unpack("!HH", block)
        self.copyRectangle(srcx, srcy, x, y, width, height)
        self._doConnection()
        
    # ---  RRE Encoding
    
    def _handleDecodeRRE(self, block, x, y, width, height):
        (subrects,) = unpack("!I", block[:4])
        color = block[4:]
        self.fillRectangle(x, y, width, height, color)
        if subrects:
            self.expect(self._handleRRESubRectangles, (8 + self.bypp) * subrects, x, y)
        else:
            self._doConnection()

    def _handleRRESubRectangles(self, block, topx, topy):
        #~ print "_handleRRESubRectangle"
        pos = 0
        end = len(block)
        sz  = self.bypp + 8
        format = "!%dsHHHH" % self.bypp
        while pos < end:
            (color, x, y, width, height) = unpack(format, block[pos:pos+sz])
            self.fillRectangle(topx + x, topy + y, width, height, color)
            pos += sz
        self._doConnection()

    # ---  CoRRE Encoding

    def _handleDecodeCORRE(self, block, x, y, width, height):
        (subrects,) = unpack("!I", block[:4])
        color = block[4:]
        self.fillRectangle(x, y, width, height, color)
        if subrects:
            self.expect(self._handleDecodeCORRERectangles, (4 + self.bypp)*subrects, x, y)
        else:
            self._doConnection()

    def _handleDecodeCORRERectangles(self, block, topx, topy):
        #~ print "_handleDecodeCORRERectangle"
        pos = 0
        end = len(block)
        sz  = self.bypp + 4
        format = "!%dsBBBB" % self.bypp
        while pos < sz:
            (color, x, y, width, height) = unpack(format, block[pos:pos+sz])
            self.fillRectangle(topx + x, topy + y, width, height, color)
            pos += sz
        self._doConnection()

    # ---  Hexile Encoding
    
    def _doNextHextileSubrect(self, bg, color, x, y, width, height, tx, ty):
        #~ print "_doNextHextileSubrect %r" % ((color, x, y, width, height, tx, ty), )
        #coords of next tile
        #its line after line of tiles
        #finished when the last line is completly received
        
        #dont inc the first time
        if tx is not None:
            #calc next subrect pos
            tx += 16
            if tx >= x + width:
                tx = x
                ty += 16
        else:
            tx = x
            ty = y
        #more tiles?
        if ty >= y + height:
            self._doConnection()
        else:
            self.expect(self._handleDecodeHextile, 1, bg, color, x, y, width, height, tx, ty)
        
    def _handleDecodeHextile(self, block, bg, color, x, y, width, height, tx, ty):
        (subencoding,) = unpack("!B", block)
        #calc tile size
        tw = th = 16
        if x + width - tx < 16:   tw = x + width - tx
        if y + height - ty < 16:  th = y + height- ty
        #decode tile
        if subencoding & 1:     #RAW
            self.expect(self._handleDecodeHextileRAW, tw*th*self.bypp, bg, color, x, y, width, height, tx, ty, tw, th)
        else:
            numbytes = 0
            if subencoding & 2:     #BackgroundSpecified
                numbytes += self.bypp
            if subencoding & 4:     #ForegroundSpecified
                numbytes += self.bypp
            if subencoding & 8:     #AnySubrects
                numbytes += 1
            if numbytes:
                self.expect(self._handleDecodeHextileSubrect, numbytes, subencoding, bg, color, x, y, width, height, tx, ty, tw, th)
            else:
                self.fillRectangle(tx, ty, tw, th, bg)
                self._doNextHextileSubrect(bg, color, x, y, width, height, tx, ty)
    
    def _handleDecodeHextileSubrect(self, block, subencoding, bg, color, x, y, width, height, tx, ty, tw, th):
        subrects = 0
        pos = 0
        if subencoding & 2:     #BackgroundSpecified
            bg = block[:self.bypp]
            pos += self.bypp
        self.fillRectangle(tx, ty, tw, th, bg)
        if subencoding & 4:     #ForegroundSpecified
            color = block[pos:pos+self.bypp]
            pos += self.bypp
        if subencoding & 8:     #AnySubrects
            #~ (subrects, ) = unpack("!B", block)
            subrects = block[pos]
        #~ print subrects
        if subrects:
            if subencoding & 16:    #SubrectsColoured
                self.expect(self._handleDecodeHextileSubrectsColoured, (self.bypp + 2)*subrects, bg, color, subrects, x, y, width, height, tx, ty, tw, th)
            else:
                self.expect(self._handleDecodeHextileSubrectsFG, 2*subrects, bg, color, subrects, x, y, width, height, tx, ty, tw, th)
        else:
            self._doNextHextileSubrect(bg, color, x, y, width, height, tx, ty)
    
    
    def _handleDecodeHextileRAW(self, block, bg, color, x, y, width, height, tx, ty, tw, th):
        """the tile is in raw encoding"""
        self.updateRectangle(tx, ty, tw, th, block)
        self._doNextHextileSubrect(bg, color, x, y, width, height, tx, ty)
    
    def _handleDecodeHextileSubrectsColoured(self, block, bg, color, subrects, x, y, width, height, tx, ty, tw, th):
        """subrects with their own color"""
        sz = self.bypp + 2
        pos = 0
        end = len(block)
        while pos < end:
            pos2 = pos + self.bypp
            color = block[pos:pos2]
            xy = block[pos2]
            wh = block[pos2+1]
            sx = xy >> 4
            sy = xy & 0xf
            sw = (wh >> 4) + 1
            sh = (wh & 0xf) + 1
            self.fillRectangle(tx + sx, ty + sy, sw, sh, color)
            pos += sz
        self._doNextHextileSubrect(bg, color, x, y, width, height, tx, ty)
    
    def _handleDecodeHextileSubrectsFG(self, block, bg, color, subrects, x, y, width, height, tx, ty, tw, th):
        """all subrect with same color"""
        pos = 0
        end = len(block)
        while pos < end:
            xy = block[pos]
            wh = block[pos+1]
            sx = xy >> 4
            sy = xy & 0xf
            sw = (wh >> 4) + 1
            sh = (wh & 0xf) + 1
            self.fillRectangle(tx + sx, ty + sy, sw, sh, color)
            pos += 2
        self._doNextHextileSubrect(bg, color, x, y, width, height, tx, ty)


    # ---  ZRLE Encoding
    
    def _handleDecodeZRLE(self, block):
        raise NotImplementedError
        
    # --- Cursor Pseudo Encoding
    
    def _handleDecodeCursor(self, block, x, y, width, height):
        # Decode cursor to array
        pos = 0
        cursor = [[0 for x in range(width)] for y in range(height)]
        for x in range(width):
            for y in range(height):
                pos2 = pos + self.bypp
                cursor[x, y] = block[pos:pos2]
                pos += self.bypp

        # Decode mask to array, 1 bit / pixel (MSb is leftmost)
        mask_width = (width+7)//8
        mask = [[0 for _ in range(mask_width)] for _ in range(height)]
        for x in range(mask_width):
            for y in range(height):
                mask[x, y] = block[pos]
                pos += 1

        self.cursorEvent(x, y, width, height, cursor, mask)
        

    #width*height*self.bypp + ((width+7)//8)*height, x, y, width, height)

    # ---  other server messages
    
    def _handleServerCutText(self, block):
        (length, ) = unpack("!xxxI", block)
        self.expect(self._handleServerCutTextValue, length)
    
    def _handleServerCutTextValue(self, block):
        self.copy_text(block)
        self.expect(self._handleConnection, 1)
    
    #------------------------------------------------------
    # incomming data redirector
    #------------------------------------------------------
    def dataReceived(self, data):
        #~ sys.stdout.write(repr(data) + '\n')
        #~ print len(data), ", ", len(self._packet)
        self._packet.append(data)
        self._packet_len += len(data)
        self._handler()

    def _handleExpected(self):
        if self._packet_len >= self._expected_len:
            buffer = b''.join(self._packet)
            while len(buffer) >= self._expected_len:
                self._already_expecting = 1
                block, buffer = buffer[:self._expected_len], buffer[self._expected_len:]
                #~ print("handle %r with %r\n" % (block, self._expected_handler.__name__))
                self._expected_handler(block, *self._expected_args, **self._expected_kwargs)
            self._packet[:] = [buffer]
            self._packet_len = len(buffer)
            self._already_expecting = 0
    
    def expect(self, handler, size, *args, **kwargs):
        #~ print("expect(%r, %r, %r, %r)\n" % (handler.__name__, size, args, kwargs))
        self._expected_handler = handler
        self._expected_len = size
        self._expected_args = args
        self._expected_kwargs = kwargs
        if not self._already_expecting:
            self._handleExpected()   #just in case that there is already enough data
    
    #------------------------------------------------------
    # client -> server messages
    #------------------------------------------------------
    
    def setPixelFormat(self, bpp=32, depth=24, bigendian=0, truecolor=1, redmax=255, greenmax=255, bluemax=255, redshift=0, greenshift=8, blueshift=16):
        pixformat = pack("!BBBBHHHBBBxxx", bpp, depth, bigendian, truecolor, redmax, greenmax, bluemax, redshift, greenshift, blueshift)
        self.transport.write(pack("!Bxxx16s", CMSG_SETPIXELFORMAT, pixformat))
        #rember these settings
        self.bpp, self.depth, self.bigendian, self.truecolor = bpp, depth, bigendian, truecolor
        self.redmax, self.greenmax, self.bluemax = redmax, greenmax, bluemax
        self.redshift, self.greenshift, self.blueshift = redshift, greenshift, blueshift
        self.bypp = self.bpp // 8        #calc bytes per pixel
        #~ print self.bypp

    def setEncodings(self, list_of_encodings):
        self.transport.write(pack("!BxH", CMSG_SETENCODINGS, len(list_of_encodings)))
        for encoding in list_of_encodings:
            self.transport.write(pack("!I", encoding))
    
    def framebufferUpdateRequest(self, x=0, y=0, width=None, height=None, incremental=0):
        if width  is None: width  = self.width - x
        if height is None: height = self.height - y
        self.transport.write(pack("!BBHHHH", CMSG_FBUPDATEREQ, incremental, x, y, width, height))

    def keyEvent(self, key, down=1):
        """For most ordinary keys, the "keysym" is the same as the corresponding ASCII value.
        Other common keys are shown in the KEY_ constants."""
        self.transport.write(pack("!BBxxI", CMSG_KEYEVENT, down, key))

    def pointerEvent(self, x, y, buttonmask=0):
        """Indicates either pointer movement or a pointer button press or release. The pointer is
           now at (x-position, y-position), and the current state of buttons 1 to 8 are represented
           by bits 0 to 7 of button-mask respectively, 0 meaning up, 1 meaning down (pressed).
        """
        self.transport.write(pack("!BBHH", CMSG_POINTEREVENT, buttonmask, x, y))

    def clientCutText(self, message):
        """The client has new ASCII text in its cut buffer.
           (aka clipboard)
        """
        self.transport.write(pack("!BxxxI", CMSG_CLIENTCUTTEXT, len(message)) + message)


    #------------------------------------------------------
    # callbacks
    # override these in your application
    #------------------------------------------------------
    def vncConnectionMade(self):
        """connection is initialized and ready.
           typicaly, the pixel format is set here."""

    def vncRequestPassword(self):
        """a password is needed to log on, use sendPassword() to
           send one."""
        if self.factory.password is None:
            print("need a password\n")
            self.transport.loseConnection()
            return
        self.sendPassword(self.factory.password)

    def vncAuthFailed(self, reason):
        """called when the authentication failed.
           the connection is closed."""
        print("Cannot connect: %s\n" % reason)

    def beginUpdate(self):
        """called before a series of updateRectangle(),
           copyRectangle() or fillRectangle()."""
    
    def commitUpdate(self, rectangles=None):
        """called after a series of updateRectangle(), copyRectangle()
           or fillRectangle() are finished.
           typicaly, here is the place to request the next screen 
           update with FramebufferUpdateRequest(incremental=1).
           argument is a list of tuples (x,y,w,h) with the updated
           rectangles."""
        
    def updateRectangle(self, x, y, width, height, data):
        """new bitmap data. data is a string in the pixel format set
           up earlier."""
    
    def copyRectangle(self, srcx, srcy, x, y, width, height):
        """used for copyrect encoding. copy the given rectangle
           (src, srxy, width, height) to the target coords (x,y)"""
    
    def fillRectangle(self, x, y, width, height, color):
        """fill the area with the color. the color is a string in
           the pixel format set up earlier"""
        #fallback variant, use update recatngle
        #override with specialized function for better performance
        self.updateRectangle(x, y, width, height, color*width*height)

    def bell(self):
        """bell"""
    
    def copy_text(self, text):
        """The server has new ASCII text in its cut buffer.
           (aka clipboard)"""
           
    def cursorEvent(self, x, y, width, height, cursor, mask):
        """Server sent cursor position, picture and mask"""
        

class RFBFactory(protocol.ClientFactory):
    """A factory for remote frame buffer connections."""

    # the class of the protocol to build
    # should be overriden by application to use a derrived class
    protocol = RFBClient
    
    def __init__(self, password = None, shared = 0):
        self.password = password
        self.shared = shared

class RFBDes(pyDes.des):
    def setKey(self, key):
        """RFB protocol for authentication requires client to encrypt
           challenge sent by server with password using DES method. However,
           bits in each byte of the password are put in reverse order before
           using it as encryption key."""
        newkey = []
        for ki in range(len(key)):
            bsrc = key[ki]
            btgt = 0
            for i in range(8):
                if bsrc & (1 << i):
                    btgt = btgt | (1 << 7-i)
            newkey.append(btgt)
        super(RFBDes, self).setKey(newkey)


# --- test code only, see vncviewer.py

if __name__ == '__main__':
    class RFBTest(RFBClient):
        """dummy client"""
        def vncConnectionMade(self):
            print("Screen format: depth=%d bytes_per_pixel=%r" % (self.depth, self.bpp))
            print("Desktop name: %r" % self.name)
            self.SetEncodings([RAW_ENCODING])
            self.FramebufferUpdateRequest()
        
        def updateRectangle(self, x, y, width, height, data):
            print("%s " * 5 % (x, y, width, height, repr(data[:20])))
    
    class RFBTestFactory(protocol.ClientFactory):
        """test factory"""
        protocol = RFBTest
        def clientConnectionLost(self, connector, reason):
            print(reason)
            from twisted.internet import reactor
            reactor.stop()
            #~ connector.connect()
    
        def clientConnectionFailed(self, connector, reason):
            print("connection failed:", reason)
            from twisted.internet import reactor
            reactor.stop()

    class Options(usage.Options):
        """command line options"""
        optParameters = [
            ['display',     'd', '0',               'VNC display'],
            ['host',        'h', 'localhost',       'remote hostname'],
            ['outfile',     'o', None,              'Logfile [default: sys.stdout]'],
        ]
        
    o = Options()
    try:
        o.parseOptions()
    except usage.UsageError as errortext:
        print("%s: %s" % (sys.argv[0], errortext))
        print("%s: Try --help for usage details." % (sys.argv[0]))
        raise SystemExit

    logFile = sys.stdout
    if o.opts['outfile']:
        logFile = o.opts['outfile']
    log.startLogging(logFile)
    
    host = o.opts['host']
    port = int(o.opts['display']) + 5900

    application = service.Application("rfb test") # create Application

    # connect to this host and port, and reconnect if we get disconnected
    vncClient = internet.TCPClient(host, port, RFBFactory()) # create the service
    vncClient.setServiceParent(application)

    # this file should be run as 'twistd -y rfb.py' but it didn't work -
    # could't import crippled_des.py, so using this hack.
    # now with crippled_des.py replaced with pyDes this can be no more actual
    from twisted.internet import reactor
    vncClient.startService()
    reactor.run()
