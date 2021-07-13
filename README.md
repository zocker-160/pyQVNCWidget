# pyQVNCWidget
Passive VNC Widget for Python using PyQt5.

_NOTE:_ This project is pretty much still in WiP status and I am struggling with the PIXEL_FORMAT.\
So if someone knows a way to fix it or a better way of doing it in the first place, I would be happy about PRs ;)

## How to install

```bash
pip3 install qvncwidget
```

### TODO:
- Proper error handling `onFatalError`
- support for more than just RAW and RGB32 PIXEL_FORMATs
- support for compression
- (maybe) support for remote contol

## Example (see /examples/example1.py)

```python
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from qvncwidget import QVNCWidget

class Window(QMainWindow):
    def __init__(self):
        super(Window, self).__init__()

        self.initUI()

    def initUI(self):
        self.setWindowTitle("QVNCWidget")

        self.vnc = QVNCWidget(
            parent=self,
            host="127.0.0.1", port=5900,
            password="1234"
        )
        self.setCentralWidget(self.vnc)
        self.vnc.start()

app = QApplication(sys.argv)
window = Window()
#window.setFixedSize(800, 600)
window.resize(800, 600)
window.show()

sys.exit(app.exec_())

```
