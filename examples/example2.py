#! /usr/bin/env python3

### [Software Information]
### Base OS: Fedora release 31 (Thirty One)
### Linux Kernel: 5.8.18-100.fc31.x86_64
### Python: 3.7.9
### Qt: 5.13.2
### xorg-x11-server-Xvfb: 1.20.6
### x11vnc: 0.9.14

### [X Server]
### $ Xvfb :0 -screen 0 1200x800x24 -nolock -ac -br -audit 0 r
###      -co /usr/local/lib/rgb -ardelay 500 -arinterval 50
###      -fp /usr/share/X11/fonts/misc,/usr/share/X11/fonts/Type1,
###      /usr/local/share/fonts/100dpi,/usr/local/share/fonts/ttf

### [VNC Server]
### $ x11vnc -display :0 -rfbport 5900 -repeat -forever -shared -sb 0

### [VNC Client]
### $ example2.py --host vncserver --port 5900 --width 1200 --height 800

import sys
import inspect
from PyQt5.QtCore import (QEvent, QTimer, Qt, pyqtSignal, pyqtSlot)
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtGui import QCursor, QPixmap, QImage, QPainter
from qvncwidget import QVNCWidget
from qvncwidget import rfb
from qvncwidget.rfb import *
from qvncwidget.workers import FrameBufferWorker, VNCFactory, RFB, log
from twisted.internet import protocol, reactor
from twisted.internet.protocol import Factory, Protocol

# dumb client chooser
rfbclients = {}
def selectClient(event):
    global rfbclients
    clients = list(rfbclients.keys())
    if len(clients) == 0:
        return None
    else:
        client = clients[0]   # FIXME
        return rfbclients[client]

class HidManager:
    KeyTranslation = {
        Qt.Key.Key_Backspace:  rfb.KEY_BackSpace,
        Qt.Key.Key_Tab:        rfb.KEY_Tab,
        Qt.Key.Key_Return:     rfb.KEY_Return,
        Qt.Key.Key_Escape:     rfb.KEY_Escape,
        Qt.Key.Key_Insert:     rfb.KEY_Insert,
        Qt.Key.Key_Delete:     rfb.KEY_Delete,
        Qt.Key.Key_Home:       rfb.KEY_Home,
        Qt.Key.Key_End:        rfb.KEY_End,
        Qt.Key.Key_PageUp:     rfb.KEY_PageUp,
        Qt.Key.Key_PageDown:   rfb.KEY_PageDown,
        Qt.Key.Key_Left:       rfb.KEY_Left,
        Qt.Key.Key_Up:         rfb.KEY_Up,
        Qt.Key.Key_Right:      rfb.KEY_Right,
        Qt.Key.Key_Down:       rfb.KEY_Down,
        Qt.Key.Key_F1:         rfb.KEY_F1,
        Qt.Key.Key_F2:         rfb.KEY_F2,
        Qt.Key.Key_F3:         rfb.KEY_F3,
        Qt.Key.Key_F4:         rfb.KEY_F4,
        Qt.Key.Key_F5:         rfb.KEY_F5,
        Qt.Key.Key_F6:         rfb.KEY_F6,
        Qt.Key.Key_F7:         rfb.KEY_F7,
        Qt.Key.Key_F8:         rfb.KEY_F8,
        Qt.Key.Key_F9:         rfb.KEY_F9,
        Qt.Key.Key_F10:        rfb.KEY_F10,
        Qt.Key.Key_F11:        rfb.KEY_F11,
        Qt.Key.Key_F12:        rfb.KEY_F12,
        Qt.Key.Key_F13:        rfb.KEY_F13,
        Qt.Key.Key_F14:        rfb.KEY_F14,
        Qt.Key.Key_F15:        rfb.KEY_F15,
        Qt.Key.Key_F16:        rfb.KEY_F16,
        Qt.Key.Key_F17:        rfb.KEY_F17,
        Qt.Key.Key_F18:        rfb.KEY_F18,
        Qt.Key.Key_F19:        rfb.KEY_F19,
        Qt.Key.Key_F20:        rfb.KEY_F20,
        Qt.Key.Key_Shift:      rfb.KEY_ShiftLeft,
        Qt.Key.Key_Control:    rfb.KEY_ControlLeft,
        Qt.Key.Key_Meta:       rfb.KEY_MetaLeft,
        Qt.Key.Key_Alt:        rfb.KEY_AltLeft,
        Qt.Key.Key_ScrollLock: rfb.KEY_Scroll_Lock,
        Qt.Key.Key_SysReq:     rfb.KEY_Sys_Req,
        Qt.Key.Key_NumLock:    rfb.KEY_Num_Lock,
        Qt.Key.Key_CapsLock:   rfb.KEY_Caps_Lock,
        Qt.Key.Key_Pause:      rfb.KEY_Pause,
        Qt.Key.Key_Super_L:    rfb.KEY_Super_L,
        Qt.Key.Key_Super_R:    rfb.KEY_Super_R,
        Qt.Key.Key_Hyper_L:    rfb.KEY_Hyper_L,
        Qt.Key.Key_Hyper_R:    rfb.KEY_Hyper_R,
        Qt.Key.Key_Enter:      rfb.KEY_KP_Enter,
    }

    def __init__(self):
        self.x       = 0
        self.y       = 0
        self.mask    = 0
        self.count   = 0
        self.pressed = set([])

    def translate(self, event):
        key = event.key()
        # alphabet characters
        if (0x41 <= key and key <= 0x5a) or (0x61 <= key and key <= 0x7a):
            key = ord(event.text())
        # special characters
        if key in HidManager.KeyTranslation:
            key = HidManager.KeyTranslation[key]
        return key

    def keyboard(self, event, action):
        ek = event.key()
        tk = self.translate(event)
        client = selectClient(event)
        if client == None:
            #print("keyboard: vnc connection may have not been established.")
            return

        if action == 0:
            #print(f"keyReleaseEvent: {hex(ek)} -> {hex(tk)}")
            client.keyEvent(tk, 0)
        elif action == 1:
            #print(f"keyPressEvent: {hex(ek)} -> {hex(tk)}")
            client.keyEvent(tk, 1)
        else:
            #print(f"keyboard: unknown action {action}")
            True

    def mouse(self, event, action):
        self.x = event.pos().x()
        self.y = event.pos().y()
        client = selectClient(event)
        if client == None:
            #print("mouse: vnc connection may have not been established.")
            return

        if action == None:
                #print(f"mouseMoveEvent: pos({self.x},{self.y}) button({bin(self.mask)})")
                True
        else:
            button = event.button()
            if button == Qt.LeftButton:
                bits = 1 << 0
            elif button == Qt.MidButton:
                bits = 1 << 1
            elif button == Qt.RightButton:
                bits = 1 << 2
            else:
                print("mouse: unknown button released?")
                return

            if action == 0:
                self.mask = self.mask & ~bits
                #print(f"mouseReleaseEvent: pos({self.x},{self.y}) button({bin(self.mask)})")
            elif action == 1:
                self.mask = self.mask | bits
                #print(f"mousePressEvent:   pos({self.x},{self.y}) button({bin(self.mask)})")
            else:
                print(f"mouse: unknown action {action}")
                return

        client.pointerEvent(self.x, self.y, self.mask)

class Window(QMainWindow):
    def __init__(self, host, port, password):
        self.host = host
        self.port = port
        self.password = password
        super(Window, self).__init__()
        self.initUI()

        # keyboard/mouse manager
        self.hid = HidManager()

        # local cursor shape on this application
        pixmap = QPixmap(2,2)
        pixmap.fill(Qt.white)
        myCursor = QCursor(pixmap)
        QApplication.setOverrideCursor(myCursor);

    def initUI(self):
        self.setWindowTitle("QVNCViewer")

        self.vnc = QVNCWidget(
            parent=self, host=self.host, port=self.port, password=self.password
        )
        self.setCentralWidget(self.vnc)
        self.vnc.setMouseTracking(True)
        self.vnc.start()

    def keyPressEvent(self, event):
        self.hid.keyboard(event, 1)

    def keyReleaseEvent(self, event):
        self.hid.keyboard(event, 0)

    def mousePressEvent(self, event):
        self.hid.mouse(event, 1)

    def mouseReleaseEvent(self, event):
        self.hid.mouse(event, 0)

    def mouseMoveEvent(self, event):
        self.hid.mouse(event, None)

### Patch to RFBClient class definition

old_handler = RFBClient._handleInitial

def new_handler(self):
    global old_handler
    old_handler(self)
    peer = self.transport.getPeer()
    self.name = f"{peer.type}:{peer.host}:{peer.port}"
    print(f"RFBClient._handleInitial: connecting peer {self.name}")
    global rfbclients
    rfbclients[self.name] = self

RFBClient._handleInitial = new_handler

### Main

if __name__ == '__main__':
    def get_options():
        from argparse import ArgumentParser
        argparser = ArgumentParser()
        argparser.add_argument('--host',     type=str, default='127.0.0.1', help='VNC Host')
        argparser.add_argument('--port',     type=int, default=5900, help='VNC Port')
        argparser.add_argument('--password', type=str, default=None, help='VNC Password')
        argparser.add_argument('--width',    type=int, default=800,  help='Window Width')
        argparser.add_argument('--height',   type=int, default=600,  help='Window Height')
        return argparser.parse_args()

    args = get_options()
    print(f"VNC Host: {args.host}")
    print(f"VNC Port: {args.port}")
    print(f"VNC Password:  {args.password}")
    print(f"Window Width:  {args.width}")
    print(f"Window Height: {args.height}")

    app = QApplication(sys.argv)
    window = Window(host = args.host, port = args.port, password = args.password)
    window.setMouseTracking(True)
    #window.setFixedSize(args.width, args.height)
    window.resize(args.width, args.height)
    window.show()

    sys.exit(app.exec_())

