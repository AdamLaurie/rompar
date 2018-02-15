import sys
import os
import json

from rompar.data import load_grid
from rompar.config import Rompar

from PIL import Image

def run(img_fn_in, grid_fn_in, dir_out):
    self = Rompar()
    load_grid(self, grid_file=grid_fn_in, gui=False)
    im = Image.open(img_fn_in)

    if not os.path.exists(dir_out):
        os.mkdir(dir_out)
    if not os.path.exists(dir_out + '/bit'):
        os.mkdir(dir_out + '/bit')

    meta = {
        "meta": {
            "source": "rompar-imgbits",
            "img": img_fn_in,
        },
        #"bit": meta_bits
    }

    meta_bits = {}
    for data, (xc, yc) in zip(self.Data, self.grid_intersections):
        x0 = xc - self.config.radius
        x1 = xc + self.config.radius
        y0 = yc - self.config.radius
        y1 = yc + self.config.radius
        
        bitfn = "%02dgc-%02dgr.png" % (xc, yc)
        meta_bit = {
            # Global absolute coordinates
            'col': self.grid_points_x.index(xc),
            'row': self.grid_points_y.index(yc),
            # Gloal pixels coordinates
            'roi': (x0, y0, x1, y1),
            # Answer frequency distribution like
            # {'0': 3, '1': 1, '?': 1}
            "dist": {data: 1},
            "best": int(data),
            }
        #print meta_bit
        imc = im.crop((x0, y0, x1, y1))
        imc.save(os.path.join(dir_out, "bit", bitfn))
        imc.close()
        meta_bits[bitfn] = meta_bit

    meta['bit'] = meta_bits

    json.dump(meta, open(os.path.join(dir_out, 'meta.json'), 'w'),
              sort_keys=True, indent=4, separators=(',', ': '))

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Extract mask ROM image')
    parser.add_argument('image', help='Input image')
    parser.add_argument('grid_file', nargs='?', help='Load saved grid file')
    parser.add_argument('dir_out', nargs='?', help='Output directory')
    args = parser.parse_args()

    run(args.image, args.grid_file, args.dir_out)
