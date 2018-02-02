import sys
import os
import rompar
# Pickle hack
from rompar import *

from PIL import Image

def run(img_fn_in, grid_fn_in, dir_out):
    self = rompar.Rompar()
    rompar.load_grid(self, grid_file=grid_fn_in, gui=False)
    im = Image.open(img_fn_in)

    if not os.path.exists(dir_out):
        os.mkdir(dir_out)

    dirs = {'0': dir_out + '/0', '1': dir_out + '/1'}
    for d in dirs.values():
        if not os.path.exists(d):
            os.mkdir(d)

    for data, (xc, yc) in zip(self.Data, self.grid_intersections):
        x0 = xc - self.config.radius
        x1 = xc + self.config.radius
        y0 = yc - self.config.radius
        y1 = yc + self.config.radius
        
        im2 = im.crop((x0, y0, x1, y1))
        fn_out = dirs[data] + '/' + 'x%05d_y%05d.png' % (xc, yc)
        im2.save(fn_out)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Extract mask ROM image')
    parser.add_argument('image', help='Input image')
    parser.add_argument('grid_file', nargs='?', help='Load saved grid file')
    parser.add_argument('dir_out', nargs='?', help='Output directory')
    args = parser.parse_args()

    run(args.image, args.grid_file, args.dir_out)
