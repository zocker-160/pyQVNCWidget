
class RFBPixelformat:
    def __init__(self,
        bpp=32, depth=24, bigendian=False, truecolor=True,
        redmax=255, greenmax=255, bluemax=255,
        redshift=0, greenshift=0, blueshift=16):

        self.bitspp = bpp
        self.bytespp = self.bitspp // 8
        self.depth = depth
        self.bigendian = 1 if bigendian else 0
        self.truecolor = 1 if truecolor else 0

        self.redmax = redmax
        self.greenmax = greenmax
        self.bluemax = bluemax
        
        self.redshift = redshift
        self.greenshift = greenshift
        self.blueshift = blueshift

    @staticmethod
    def getRGB32():
        return RFBPixelformat(
            bpp=32, depth=32,
            redshift=16, greenshift=8, blueshift=0
        )

    def asTuple(self) -> tuple:
        return (
            self.bitspp, self.depth, self.bigendian, self.truecolor,
            self.redmax, self.greenmax, self.bluemax,
            self.redshift, self.greenshift, self.blueshift
        )

class RFBRectangle:
    def __init__(self, xPos: int, yPos: int, width: int, height: int):
        self.xPos = xPos
        self.yPos = yPos
        self.width = width
        self.height = height

    def asTuple(self) -> tuple:
        return (self.xPos, self.yPos, self.width, self.height)

    def __str__(self) -> str:
        return f"x: {self.xPos} y: {self.yPos} width: {self.width} height: {self.height}"
