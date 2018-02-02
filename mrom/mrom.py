import string

class InvalidData(Exception):
    pass

def mask_b2i(maskb):
    '''Convert bitmask to bit number'''
    return {
        0x80: 7,
        0x40: 6,
        0x20: 5,
        0x10: 4,
        0x08: 3,
        0x04: 2,
        0x02: 1,
        0x01: 0,
        }[maskb]

def mask_i2b(maski):
    '''Convert bit number to bitmask'''
    return 1 << maski

class MaskROM(object):
    def __init__(self, f_in, f_out, verbose=False):
        self.f_in = f_in
        self.f_out= f_out
        self.verbose = verbose

    @staticmethod
    def txtwh():
        '''
        Return expected txt file width/height in the canonical orientation
        Typically this is with row/column decoding down and to the right
        '''
        raise Exception("Required")

    @staticmethod
    def invert():
        '''
        During visual entry, convention is usually to use brighter / more featureful as 1
        However, this is often actually 0
        Set True to default to swap 0/1 bits
        '''
        return False

    def txt(self):
        '''Read input file, stripping extra whitespace and checking format'''
        ret = ''
        wh = self.txtwh()
        if wh:
            w, h = wh
        else:
            w, h = None, None
        lines = 0
        for linei, l in enumerate(self.f_in):
            l = l.strip().replace(' ', '')
            if not l:
                continue
            if len(l) != w:
                raise InvalidData('Line %s want length %d, got %d' % (linei, w, len(l)))
            if l.replace('1', '').replace('0', ''):
                raise InvalidData('Line %s unexpected char' % linei)
            ret += l + '\n'
            lines += 1
        if lines != h:
            raise InvalidData('Want %d lines, got %d' % (h, lines))
        return ret

    def txtbits(self):
        '''Return contents as char array of bits (ie string with no whitespace)'''
        txt = self.txt()
        # remove all but bits
        table = string.maketrans('','')
        not_bits = table.translate(table, '01')
        return txt.translate(table, not_bits)

    def rc2ob(self, col, row):
        '''Given image row/col return byte (offset, binary mask)'''
        raise Exception("Required")

    def ob2rc(self, offset, maskb):
        '''Given (offset, binary mask) return image row/col return byte'''
        raise Exception("Required")

    def txt2bin(self):
        raise Exception("Required")
