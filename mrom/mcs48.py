import string

from util import hexdump
from mrom import MaskROM

'''
Reference ROM: decap #8, #9 (FIXME: add link)
Reference version by EdHunter with help from Haze
'''
class D8041AH(MaskROM):
    def desc(self):
        return 'NEC D8041AH'

    @staticmethod
    def txtwh():
        '''
        Layout
        -Orientation: decode logic down/right / NEC logo left
        -128 bit wide lines
        -66 lines tall
        -Last two rows may contain a bunch of 1s
        '''
        return (128, 66)

    @staticmethod
    def invert():
        '''
        Actual: bit with extra circle contact => 0
        Convention: xpol bright (ie circle => 0) recorded as 1
        Result: invert
        '''
        return True

    def txt2bin(self):
        bits = self.txtbits()
    
        def bits2byte(s):
            b = 0
            for bit in s:
                b = b << 1
                b = b | int(bit)
            return chr(b)
        
        data = ""
        for a in range(0, len(bits), 128):
            s = bits[a:a+128]
            for b in range(0, 16):
                x = ""
                for c in range(0, 8):
                    x = x + s[(c*16)+b:(c*16)+b+1]
                data = data + bits2byte(x)
        
        # rotate - thanks haze
        ROM = bytearray(data)
        ROM2 = bytearray(data)
        
        destaddr = 0;
        for i in range(0,4):
            for j in range(0,0x400, 4):
                sourceaddr = j+i
                ROM2[destaddr] = ROM[sourceaddr]
                destaddr = destaddr + 1
    
        destaddr = 0;
        for i in range(0,4):
            for j in range(0,0x400, 4):
                sourceaddr = j+i
                ROM[destaddr] = ROM2[sourceaddr]
                destaddr = destaddr + 1
        
        # rearrange
        data = str(ROM)[0x300:0x400] + str(ROM)[0x200:0x300] + str(ROM)[0x100:0x200] + str(ROM)[0x000:0x100]
        
        if self.verbose:
            print "### data invert ###"
            print hexdump(data)
            print
        
        self.f_out.write(data)

'''
References
-http://caps0ff.blogspot.com/2016/12/39-rom-extracted.html
-http://siliconpr0n.org/map/taito/m-001/mz_mit20x/
# TODO: requested source code. Add something if we get it
'''
class MSL8042(MaskROM):
    def run(self):
        raise Exception("FIXME")
