# pyQVNCWidget
VNC Widget for Python using PyQt5

## How to install

```bash
pip3 install qvncwidget
```

### TODO:
- Proper error handling `onFatalError`
- support for more than just RAW and RGB32 PIXEL_FORMATs
- support for compression
- implement rfb 3.7 and 3.8
- implement local and remote clipboard

## Examples (see /examples folder)

```python
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
```

### Example with widget input events

```python
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
        # we need to request focus otherwise we will not get keyboard input events
        self.vnc.setFocus()

        # you can disable mouse tracking if desired
        self.vnc.setMouseTracking(False)

        self.vnc.start()

    def closeEvent(self, ev):
        self.vnc.stop()
        return super().closeEvent(ev)

app = QApplication(sys.argv)
window = Window()
window.resize(800, 600)
window.show()

sys.exit(app.exec_())
```

### Example with window input events

In this example we are passing input events from the window to the widget

```python
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
```

## References

- https://datatracker.ietf.org/doc/html/rfc6143
- https://vncdotool.readthedocs.io/en/0.8.0/rfbproto.html?highlight=import#string-encodings
