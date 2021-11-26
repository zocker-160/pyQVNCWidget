
import pyDes

class RFBDes(pyDes.des):
    def setKey(self, key):
        """
        RFB protocol for authentication requires client to encrypt
        challenge sent by server with password using DES method. However,
        bits in each byte of the password are put in reverse order before
        using it as encryption key.
        """
        newkey = list()
        #for ki in range(len(key)):
        for bsrc in key:
            #bsrc = key[ki]
            btgt = 0
            for i in range(8):
                if bsrc & (1 << i):
                    btgt = btgt | (1 << 7-i)
            newkey.append(btgt)
        super(RFBDes, self).setKey(newkey)
