from mrom import MaskROM, mask_b2i

'''
References
https://github.com/andrew-gardner/django-monkeys/blob/master/tools/romimg.py

Think 34 is the same layout
'''
class MB86233(MaskROM):
    def ob2rc(self, offset, maskb):
        biti = offset * 8 + mask_b2i(maskb)
        #print biti
        # Each column has 16 bytes
        # Actually starts from right of image
        col = (32 * 8 - 1) - biti / (8 * 32)
        # 0, 8, 16, ... 239, 247, 255
        row = (biti % 32) * 8 + (biti / 32) % 8
        #print row
        return (col, row)

    def run(self):
        raise Exception("FIXME")
