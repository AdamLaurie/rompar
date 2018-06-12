from __future__ import print_function
from __future__ import division
import subprocess
import sys
import cv2
import traceback
import json
import numpy
import os

from .config import *
from .cmd_help import *

K_RIGHT = 65363
K_DOWN = 65362
K_LEFT = 65361
K_UP = 65364


def symlinka(target, alias):
    '''Atomic symlink'''
    tmp = alias + '_'
    if os.path.exists(tmp):
        os.unlink(tmp)
    os.symlink(target, alias + '_')
    os.rename(tmp, alias)


# create binary printable string
def to_bin(x):
    return ''.join(x & (1 << i) and '1' or '0' for i in range(7, -1, -1))


class Rompar(object):
    def __init__(self):
        self.gui = True

        self.img_fn = None

        # Main state
        # Have we attempted to decode bits?
        self.data_read = False

        # Pixels between cols
        self.step_x = 0
        # Pixels between rows
        self.step_y = 0
        # Number of rows/cols per bit grouping
        self.group_cols = 0
        self.group_rows = 0

        self.Search_HEX = None
        # Number of save commands issued
        # Used to create unique save file postfix per save
        self.saven = 0

        # >= 0 when in edit mode
        self.Edit_x = -1
        self.Edit_y = -1

        # Processed data
        self.inverted = False
        self.data = []
        # Global
        self.grid_points_x = []
        self.grid_points_y = []
        self.grid_intersections = []

        # Misc
        # Process events while true
        self.running = True

        # Image buffers
        self.img_target = None
        self.img_grid = None
        self.img_mask = None
        self.img_peephole = None
        self.img_display = None
        self.img_display_viewport = None
        self.img_blank = None
        self.img_hex = None
        # Font currently rendering
        self.font = None

        # Be more verbose
        # Crash on exceptions
        self.debug = False
        self.basename = None

        self.config = Config()

    def load_grid(self, grid_json=None, gui=True):
        self.gui = gui

        self.grid_intersections = grid_json['grid_intersections']
        data = grid_json['data']
        self.grid_points_x = grid_json['grid_points_x']
        self.grid_points_y = grid_json['grid_points_y']
        # self.config = grid_json['config']
        for k, v in grid_json['config'].items():
            if k == 'view':
                for kv, vv in v.items():
                    self.config.view.__dict__[kv] = vv
            else:
                self.config.__dict__[k] = v

        # Possible only one direction is drawn
        if self.grid_intersections:
            # Some past DBs had corrupt sets with duplicates
            # Maybe better to just trust them though
            self.grid_points_x = []
            self.grid_points_y = []
            for x, y in self.grid_intersections:
                try:
                    self.grid_points_x.index(x)
                except:
                    self.grid_points_x.append(x)

                try:
                    self.grid_points_y.index(y)
                except:
                    self.grid_points_y.append(y)

        print ('Grid points: %d x, %d y' % (len(self.grid_points_x), len(self.grid_points_y)))
        squared = len(self.grid_points_x) * len(self.grid_points_y)
        if len(self.grid_intersections) != squared:
            print (self.grid_points_x)
            print (self.grid_points_y)
            raise Exception("%d != %d" % (len(self.grid_intersections), squared))

        self.step_x = 0.0
        if len(self.grid_points_x) > 1:
            self.step_x = self.grid_points_x[1] - self.grid_points_x[0]
        self.step_y = 0.0
        if len(self.grid_points_y) > 1:
            self.step_y = self.grid_points_y[1] - self.grid_points_y[0]
        if not self.config.default_radius:
            if self.step_x:
                self.config.radius = self.step_x / 3
            else:
                self.config.radius = self.step_y / 3
        self.redraw_grid()

        if data:
            print ('Initializing data')
            if len(data) != len(self.grid_intersections):
                raise Exception("%d != %d" % (len(data), len(self.grid_intersections)))
            self.read_data(data_ref=data, force=True)

    def do_loop(self):
        # image processing
        cv2.dilate(self.img_target, (3,3))

        if self.config.threshold:
            cv2.threshold(self.img_original, self.config.pix_thresh_min, 0xff, cv2.THRESH_BINARY, self.img_target)
            cv2.bitwise_and(self.img_target, self.img_mask, self.img_target)
        if self.config.dilate:
            cv2.dilate(self.img_target, (3,3))
        if self.config.erode:
            cv2.erode(self.img_target, (3,3))
        self.show_image()

        sys.stdout.write('> ')
        sys.stdout.flush()
        # keystroke processing
        ki = cv2.waitKey(0)

        # Simple character value, if applicable
        kc = None
        # Char if a common char, otherwise the integer code
        k = ki

        if 0 <= ki < 256:
            kc = chr(ki)
            k = kc
        elif 65506 < ki < 66000 and ki != 65535:
            ki2 = ki - 65506 - 30
            # modifier keys
            if ki2 >= 0:
                kc = chr(ki2)
                k = kc

        if kc:
            print ('%d (%s)\n' % (ki, kc))
        else:
            print ('%d\n' % ki)

        if ki > 66000:
            return
        if ki < 0:
            print ("Exiting on closed")
            self.running = False
            return
        self.on_key(k)

    def run(self, img_fn=None, grid_file=None):
        self.img_fn = img_fn
        grid_json = None
        if grid_file:
            with open(grid_file, 'rb') as gridfile:
                grid_json = json.load(gridfile)
            if self.img_fn is None:
                self.img_fn = grid_json.get('img_fn')
            if self.group_cols is None:
                self.group_cols = grid_json.get('group_cols')
                self.group_rows = grid_json.get('group_rows')
        else:
            # Then need critical args
            if not self.img_fn:
                raise Exception("Filename required")
            if not self.group_cols:
                raise Exception("cols required")
            if not self.group_rows:
                raise Exception("rows required")

        if self.img_fn is None:
            raise Exception("Image required")

        #testing ground for new cv version
        #load img as numpy ndarray dimensions (height, width, channels)
        self.img_original = cv2.imread(self.img_fn, cv2.IMREAD_COLOR)
        print ('Image is %dx%d' % (self.img_original.shape[1], self.img_original.shape[0]))


        self.basename = self.img_fn[:self.img_fn.find('.')]

        # new cv image buffers
        self.img_target = numpy.zeros(self.img_original.shape, numpy.uint8)
        self.img_grid = numpy.zeros(self.img_original.shape, numpy.uint8)
        self.img_mask = numpy.ndarray(self.img_original.shape, numpy.uint8)
        self.img_mask[:] = (0, 0, 255)
        self.img_peephole = numpy.zeros(self.img_original.shape, numpy.uint8)
        self.img_display = numpy.zeros(self.img_original.shape, numpy.uint8)
        self.img_blank = numpy.zeros(self.img_original.shape, numpy.uint8)
        self.img_hex = numpy.zeros(self.img_original.shape, numpy.uint8)


        self.config.font_size = 1.0


        self.title = "rompar %s" % img_fn
        cv2.namedWindow(self.title, 0)
        cv2.setMouseCallback(self.title, self.on_mouse, None)

        self.img_target = numpy.copy(self.img_original)

        if grid_json:
            self.load_grid(grid_json)

        cmd_help()
        cmd_help2()

        # main loop
        while self.running:
            try:
                self.do_loop()
            except Exception:
                if self.debug:
                    raise
                print ('WARNING: exception')
                traceback.print_exc()

        print ('Exiting')

    def on_key(self, k):
        if k == 65288 and self.Edit_x >= 0:
            # BS
            print ('deleting column')
            self.grid_points_x.remove(self.grid_points_x[self.Edit_x])
            self.Edit_x = -1
            self.read_data()
        elif k == K_LEFT:
            self.pan(-self.config.view.incx, 0)
        elif k == K_RIGHT:
            self.pan(self.config.view.incx, 0)
        elif k == K_UP:
            self.pan(0, -self.config.view.incy)
        elif k == K_DOWN:
            self.pan(0, self.config.view.incy)
            '''
        elif k == K_UP and self.Edit_y >= 0:
            # up arrow
            print ('editing line', self.Edit_y)
            self.grid_points_y[self.grid_points_y.index(self.Edit_y)] -= 1
            self.Edit_y -= 1
            self.read_data()
        elif k == K_DOWN and self.Edit_y >= 0:
            # down arrow
            print ('editing line', self.Edit_y)
            self.grid_points_y[self.grid_points_y.index(self.Edit_y)] += 1
            self.Edit_y += 1
            self.read_data()
        elif k == K_RIGHT and self.Edit_x >= 0:
            # right arrow - edit entrie column group
            print ('editing column', self.Edit_x)
            sx = self.Edit_x - (self.Edit_x % self.group_cols)
            for x in range(sx, sx + self.group_cols):
                self.grid_points_x[x] += 1
            self.read_data()
        elif k == K_LEFT and self.Edit_x >= 0:
            # left arrow
            print ('editing column', self.Edit_x)
            sx = self.Edit_x - (self.Edit_x % self.group_cols)
            for x in range(sx, sx + self.group_cols):
                self.grid_points_x[x] -= 1
            self.read_data()
            '''
        elif k == 65432 and self.Edit_x >= 0:
            # right arrow on numpad - edit single column
            print ('editing column', self.Edit_x)
            self.grid_points_x[self.Edit_x] += 1
            self.read_data()
        elif k == 65430 and self.Edit_x >= 0:
            # left arrow on numpad - edit single column
            print ('editing column', self.Edit_x)
            self.grid_points_x[self.Edit_x] -= 1
            self.read_data()
        elif (k == 65439 or k == 65535) and self.Edit_y >= 0:
            # delete
            print ('deleting row', self.Edit_y)
            self.grid_points_y.remove(self.Edit_y)
            self.Edit_y = -1
            self.read_data()
        elif k == chr(10):
            # enter
            self.Edit_x = -1
            self.Edit_y = -1
            print ('Done editing')
            self.read_data()
        elif k == 'a':
            if self.config.radius:
                self.config.radius -= 1
                self.read_data()
            print ('Radius: %d' % self.config.radius)
        elif k == 'A':
            self.config.radius += 1
            self.read_data()
            print ('Radius: %d' % self.config.radius)
        elif k == 'b':
            self.config.img_display_blank_image = not self.config.img_display_blank_image
        elif k == 'c':
            self.print_config()
        elif k == 'd':
            self.config.dilate = max(self.config.dilate - 1, 0)
            print ('Dilate: %d' % self.config.dilate)
            self.read_data()
        elif k == 'D':
            self.config.dilate += 1
            print ('Dilate: %d' % self.config.dilate)
            self.read_data()
        elif k == 'e':
            self.config.erode = max(self.config.erode - 1, 0)
            print ('Erode: %d' % self.config.erode)
            self.read_data()
        elif k == 'E':
            self.config.erode += 1
            print ('Erode: %d' % self.config.erode)
            self.read_data()
        elif k == 'f':
            if self.config.font_size > 0.1:
                self.config.font_size -= 0.1
            print ('Font size: %d' % self.config.font_size)
        elif k == 'F':
            self.config.font_size += 0.1
            print ('Font size: %d' % self.config.font_size)
        elif k == 'g':
            self.config.img_display_grid = not self.config.img_display_grid
            print ('Display grid:', self.config.img_display_grid)
        elif k == 'h' or k == '?':
            cmd_help()
        elif k == 'H':
            self.config.img_display_binary = not self.config.img_display_binary
            print ('Display binary:', self.config.img_display_binary)
        elif k == 'i':
            self.inverted = not self.inverted
            print ('Inverted:', self.inverted)
        elif k == 'l':
            self.config.LSB_Mode = not self.config.LSB_Mode
            print ('LSB self.data mode:', self.config.LSB_Mode)
        elif k == 'm':
            self.config.bit_thresh_div -= 1
            print ('thresh_div:', self.config.bit_thresh_div)
            self.read_data()
        elif k == 'M':
            self.config.bit_thresh_div += 1
            print ('thresh_div:', self.config.bit_thresh_div)
            self.read_data()
        elif k == 'o':
            self.config.img_display_original = not self.config.img_display_original
            print ('display original:', self.config.img_display_original)
        elif k == 'p':
            self.config.img_display_peephole = not self.config.img_display_peephole
            print ('display peephole:', self.config.img_display_peephole)
        elif k == 'r':
            print ('reading %d points...' % len(self.grid_intersections))
            self.read_data(force=True)
        elif k == 'R':
            self.redraw_grid()
            self.data_read = False
        elif k == 's':
            self.config.img_display_data = not self.config.img_display_data
            print ('show data:', self.config.img_display_data)
        elif k == 'S':
            self.cmd_save()
        elif k == 'q':
            print ("Exiting on q")
            self.running = False
        elif k == 't':
            self.config.threshold = True
            print ('Threshold:', self.config.threshold)
        elif k == '-':
            self.config.pix_thresh_min = max(self.config.pix_thresh_min - 1, 0x01)
            print ('Threshold filter %02x' % self.config.pix_thresh_min)
            if self.data_read:
                self.read_data()
        elif k == '+':
            self.config.pix_thresh_min = min(self.config.pix_thresh_min + 1, 0xFF)
            print ('Threshold filter %02x' % self.config.pix_thresh_min)
            if self.data_read:
                self.read_data()
        elif k == '/':
            self.cmd_find(k)
        #else:
        #    print ('Unknown command %s' % k)

    def cmd_find(self, k):
        print ('Enter space delimeted HEX (in image window), e.g. 10 A1 EF: ',)
        sys.stdout.flush()
        shx = ''
        while 42:
            c = cv2.waitKey(0)
            # BS or DEL
            if c == 65288 or c == 65535 or k == 65439:
                c = 0x08
            if c > 255:
                continue

            # Newline
            if c == 0x0d or c == 0x0a:
                print()
                break
            # Backspace
            elif c == 0x08:
                if not shx:
                    sys.stdout.write('\a')
                    sys.stdout.flush()
                    continue
                sys.stdout.write('\b \b')
                sys.stdout.flush()
                shx = shx[:-1]
            else:
                c = chr(c)
                sys.stdout.write(c)
                sys.stdout.flush()
                shx += c
        try:
            self.Search_HEX = [int(h, 16) for h in shx.strip().split(' ')]
        except ValueError:
            print ('Invalid hex value')
            return
        print ('searching for', shx.upper())

    def cmd_save(self):
        print ('saving...')

        self.next_save()
        self.save_grid()

        if not self.data_read:
            print ('No bits to save')
        else:
            if 0 and self.save_dat:
                self.save_dat()
            self.save_txt()

    def print_config(self):
        print ('Display')
        print ('  Grid      %s' % self.config.img_display_grid)
        print ('  Original  %s' % self.config.img_display_original)
        print ('  Peephole  %s' % self.config.img_display_peephole)
        print ('  Data      %s' % self.config.img_display_data)
        print ('    As binary %s' % self.config.img_display_binary)
        print ('Pixel processing')
        print ('  Bit threshold divisor   %s' % self.config.bit_thresh_div)
        print ('  Pixel threshold minimum %s (0x%02X)' % (self.config.pix_thresh_min, self.config.pix_thresh_min))
        print ('  Dilate    %s' % self.config.dilate)
        print ('  Erode     %s' % self.config.erode)
        print ('  Radius    %s' % self.config.radius)
        print ('  Threshold %s' % self.config.threshold)
        print ('  Step')
        print ('    X       % 5.1f' % self.step_x)
        print ('    X       % 5.1f' % self.step_y)
        print ('Bit state')
        print ('  Data read %d' % self.data_read)
        print ('  Bits per group')
        print ('    X       %d cols' % self.group_cols)
        print ('    Y       %d rows' % self.group_rows)
        print ('  Bit points total')
        print ('    X       %d cols' % len(self.grid_points_x))
        print ('    Y       %d rows' % len(self.grid_points_y))
        print ('  Inverted  %d' % self.inverted)
        print ('  Intersections %d' % len(self.grid_intersections))
        print ('  Viewport')
        print ('    X       %d' % self.config.view.x)
        print ('    Y       %d' % self.config.view.y)
        print ('    W       %d' % self.config.view.w)
        print ('    H       %d' % self.config.view.h)
        print ('    PanX    %d' % self.config.view.incx)
        print ('    PanY    %d' % self.config.view.incy)

    def redraw_grid(self):
        if not self.gui:
            return
        self.img_grid.fill(0)
        self.img_peephole.fill(0)

        self.grid_intersections = []
        self.grid_points_x.sort()
        self.grid_points_y.sort()

        for x in self.grid_points_x:
            cv2.line(self.img_grid, (x, 0), (x, self.img_target.shape[0]), (0xff, 0x00, 0x00),
                    1)
            for y in self.grid_points_y:
                self.grid_intersections.append((x, y))
        self.grid_intersections.sort()
        for y in self.grid_points_y:
            cv2.line(self.img_grid, (0, y), (self.img_target.shape[1], y), (0xff, 0x00, 0x00),
                    1)
        for x, y in self.grid_intersections:
            cv2.circle(
                self.img_grid, (x, y), self.config.radius, (0x00, 0x00, 0x00), -1)
            cv2.circle(
                self.img_grid, (x, y), self.config.radius, (0xff, 0x00, 0x00), 1)
            cv2.circle(
                self.img_peephole, (x, y),
                self.config.radius + 1,
                (0xff, 0xff, 0xff),
                -1)

    def read_data(self, data_ref=None, force=False):
        if not force and not self.data_read:
            return

        self.redraw_grid()

        # maximum possible value if all pixels are set
        maxval = (self.config.radius * self.config.radius) * 255
        print ('read_data max aperture value:', maxval)

        if data_ref:
            print ('read_data: loading reference data (%d entries)' % len(data_ref))
            print ('Grid intersections: %d' % len(self.grid_intersections))
            self.data = data_ref
        else:
            print ('read_data: computing')
            # Compute
            self.data = []
            for x, y in self.grid_intersections:
                value = 0
                # FIXME: misleading
                # This isn't a radius but rather a bounding box
                for xx in range(x - (self.config.radius // 2), x + (self.config.radius // 2)):
                    for yy in range(y - (self.config.radius // 2), y + (self.config.radius // 2)):
                        value += self.get_pixel(yy, xx)
                if value > maxval / self.config.bit_thresh_div:
                    self.data.append('1')
                else:
                    self.data.append('0')

        # Render
        for i, (x, y) in enumerate(self.grid_intersections):
            if self.data[i] == '1':
                cv2.circle(
                    self.img_grid, (x, y), self.config.radius, (0x00, 0xff, 0x00), 2)
                # highlight if we're in edit mode
                if y == self.Edit_y:
                    sx = self.Edit_x - (self.Edit_x % self.group_cols)
                    if self.grid_points_x.index(x) >= sx and self.grid_points_x.index(
                            x) < sx + self.group_cols:
                        cv2.circle(
                            self.img_grid, (x, y),
                            self.config.radius,
                            (0xff, 0xff, 0xff),
                            2)
            else:
                pass
        self.data_read = True

    def get_pixel(self, x, y):
        return self.img_target[x, y][0] + self.img_target[x, y][1] + self.img_target[x, y][2]

    def next_save(self):
        '''Look for next unused save slot by checking grid files'''
        while True:
            fn = self.basename + '_s%d.grid' % self.saven
            if not os.path.exists(fn):
                break
            self.saven += 1

    def save_txt(self):
        '''Write text file like bits sown in GUI. Space between row/cols'''
        fn = self.basename + '_s%d.txt' % self.saven
        symlinka(fn, self.basename + '.txt')
        crs = self.data_as_cr()
        with open(fn, 'w') as f:
            for row in xrange(len(self.grid_points_y)):
                # Put a space between row gaps
                if row and row % self.group_rows == 0:
                    f.write('\n')
                for col in xrange(len(self.grid_points_x)):
                    if col and col % self.group_cols == 0:
                        f.write(' ')
                    f.write(crs[(col, row)])
                # Newline afer every row
                f.write('\n')
        print ('Saved %s' % fn)

    def save_grid(self, fn=None):
        config = dict(self.config.__dict__)
        config['view'] = config['view'].__dict__

        # XXX: this first cut is partly due to ease of converting old DB
        # Try to move everything non-volatile into config object
        j = {
            # Increment major when a fundamentally breaking change occurs
            # minor reserved for now, but could be used for non-breaking
            'version': (1, 0),
            'grid_intersections': self.grid_intersections,
            'data': self.data,
            'grid_points_x': self.grid_points_x,
            'grid_points_y': self.grid_points_y,
            'fn': config,
            'group_cols': self.group_cols,
            'group_rows': self.group_rows,
            'config': config,
            'img_fn': self.img_fn,
            }

        if self.basename:
            if not fn:
                fn = self.basename + '_s%d.json' % self.saven
            symlinka(fn, self.basename + '.json')
        gridout = open(fn, 'wb')
        json.dump(j, gridout, indent=4, sort_keys=True)
        print ('Saved %s' % fn)

    def data_as_cr(self):
        '''Return data as binary chars in ret[(column, row)] map'''
        ret = {}
        xys = self.data_as_xy()
        for xi, x in enumerate(self.grid_points_x):
            for yi, y in enumerate(self.grid_points_y):
                ret[(xi, yi)] = xys[(x, y)]
        return ret

    def data_as_xy(self):
        '''Return data as binary chars in ret[(x, y)] map'''
        ret = {}
        for d, (x, y) in zip(self.data, self.grid_intersections):
            ret[(x, y)] = d
        return ret

    def pan(self, x, y):
        #imgw = self.img_target.cols
        #imgh = self.img_target.rows
        #imgw, imgh, _channels = self.img_target.shape
        imgw = self.img_target.shape[1]
        imgh = self.img_target.shape[0]

        self.config.view.x = min(max(0, self.config.view.x + x), imgw - self.config.view.w)
        self.config.view.y = min(max(0, self.config.view.y + y), imgh - self.config.view.h)

    def get_all_data(self):
        '''Return data as bytes'''
        out = ''
        for column in range(len(self.grid_points_x) // self.group_cols):
            for row in range(len(self.grid_points_y)):
                thischunk = ''
                for x in range(self.group_cols):
                    thisbit = self.data[x * len(self.grid_points_y) + row +
                                   column * self.group_cols * len(self.grid_points_y)]
                    if self.inverted:
                        if thisbit == '0':
                            thisbit = '1'
                        else:
                            thisbit = '0'
                    thischunk += thisbit
                for x in range(self.group_cols // 8):
                    thisbyte = thischunk[x * 8:x * 8 + 8]
                    # reverse self.group_cols if we want LSB
                    if self.config.LSB_Mode:
                        thisbyte = thisbyte[::-1]
                    out += chr(int(thisbyte, 2))
        return out

    # call with exact values for intersection
    def get_data(self, x, y):
        return self.data[self.grid_intersections.index((x, y))]

    def set_data(self, x, y, val):
        i = self.grid_intersections.index((x, y))
        self.data[i] = val

    def toggle_data(self, x, y):
        i = self.grid_intersections.index((x, y))
        if self.data[i] == '0':
            self.data[i] = '1'
        else:
            self.data[i] = '0'
        return self.data[i]

    def update_radius(self):
        if self.config.radius:
            return

        if self.config.default_radius:
            self.config.radius = self.config.default_radius
        else:
            if self.step_x:
                self.config.radius = int(self.step_x / 3)
            elif self.step_y:
                self.config.radius = int(self.step_y / 3)

    # mouse events
    def on_mouse(self, event, mouse_x, mouse_y, flags, param):
        img_x = mouse_x + self.config.view.x
        img_y = mouse_y + self.config.view.y

        # draw vertical grid lines
        if event == cv2.EVENT_LBUTTONDOWN:
            self.on_mouse_left(img_x, img_y, flags)
        if event == cv2.EVENT_RBUTTONDOWN:
            self.on_mouse_right(img_x, img_y, flags)

    def on_mouse_left(self, img_x, img_y, flags):
        # Edit data
        if self.data_read:
            # find nearest intersection and toggle its value
            for x in self.grid_points_x:
                if img_x >= x - self.config.radius / 2 and img_x <= x + self.config.radius / 2:
                    for y in self.grid_points_y:
                        if img_y >= y - self.config.radius / 2 and img_y <= y + self.config.radius / 2:
                            value = self.toggle_data(x, y)
                            #print (self.img_target[x, y])
                            #print ('value', value)
                            if value == '0':
                                cv2.circle(
                                    self.img_grid, (x, y),
                                    self.config.radius,
                                    (0xff, 0x00, 0x00),
                                    2)
                            else:
                                cv2.circle(
                                    self.img_grid, (x, y),
                                    self.config.radius,
                                    (0x00, 0xff, 0x00),
                                    2)

                            self.show_image()
        # Edit grid
        else:
            #if not Target[img_y, img_x]:
            if flags != cv2.EVENT_FLAG_SHIFTKEY and not self.get_pixel(img_y, img_x):
                print ('autocenter: miss!')
                return

            if img_x in self.grid_points_x:
                return
            # only draw a single line if this is the first one
            if len(self.grid_points_x) == 0 or self.group_cols == 1:
                if flags != cv2.EVENT_FLAG_SHIFTKEY:
                    img_x, img_y = self.auto_center(img_x, img_y)

                # don't try to auto-center if shift key pressed
                self.draw_line(img_x, img_y, 'V', False)
                self.grid_points_x.append(img_x)
                if self.group_rows == 1:
                    self.draw_line(img_x, img_y, 'V', True)
            else:
                # set up auto draw
                if len(self.grid_points_x) == 1:
                    # use a float to reduce rounding errors
                    self.step_x = float(img_x - self.grid_points_x[0]) / (self.group_cols - 1)
                    # reset stored self.data as main loop will add all entries
                    img_x = self.grid_points_x[0]
                    self.grid_points_x = []
                    self.update_radius()
                # draw a full set of self.group_cols
                for x in range(self.group_cols):
                    draw_x = int(img_x + x * self.step_x)
                    self.grid_points_x.append(draw_x)
                    self.draw_line(draw_x, img_y, 'V', True)

    def on_mouse_right(self, img_x, img_y, flags):
        # Edit data
        if self.data_read:
            # find row and select for editing
            for x in self.grid_points_x:
                for y in self.grid_points_y:
                    if img_y >= y - self.config.radius / 2 and img_y <= y + self.config.radius / 2:
                        #print ('value', get_data(x,y))
                        # select the whole row
                        xcount = 0
                        for x in self.grid_points_x:
                            if img_x >= x - self.config.radius / 2 and img_x <= x + self.config.radius / 2:
                                self.Edit_x = xcount
                                break
                            else:
                                xcount += 1
                        # highlight the bit group we're in
                        sx = self.Edit_x - (self.Edit_x % self.group_cols)
                        self.Edit_y = y
                        self.read_data()
                        self.show_image()
                        return
        # Edit grid
        else:
            if flags != cv2.EVENT_FLAG_SHIFTKEY and not self.get_pixel(img_y, img_x):
                print ('autocenter: miss!')
                return

            if img_y in self.grid_points_y:
                return
            # only draw a single line if this is the first one
            if len(self.grid_points_y) == 0 or self.group_rows == 1:
                if flags != cv2.EVENT_FLAG_SHIFTKEY:
                    img_x, img_y = self.auto_center(img_x, img_y)

                self.draw_line(img_x, img_y, 'H', False)
                self.grid_points_y.append(img_y)
                if self.group_rows == 1:
                    self.draw_line(img_x, img_y, 'H', True)
            else:
                # set up auto draw
                if len(self.grid_points_y) == 1:
                    # use a float to reduce rounding errors
                    self.step_y = float(img_y - self.grid_points_y[0]) / (self.group_rows - 1)
                    # reset stored self.data as main loop will add all entries
                    img_y = self.grid_points_y[0]
                    self.grid_points_y = []
                    self.update_radius()
                # draw a full set of self.group_rows
                for y in range(self.group_rows):
                    draw_y = int(img_y + y * self.step_y)
                    # only draw up to the edge of the image
                    if draw_y > self.img_original.height:
                        break
                    self.grid_points_y.append(draw_y)
                    self.draw_line(img_x, draw_y, 'H', True)

    def show_image(self):
        if self.config.img_display_original:
            self.img_display = numpy.copy(self.img_original)
        else:
            self.img_display = numpy.copy(self.img_target)
        if self.config.img_display_blank_image:
            self.img_display = numpy.copy(self.img_blank)

        if self.config.img_display_grid:
            cv2.bitwise_or(self.img_display, self.img_grid, self.img_display)

        if self.config.img_display_peephole:
            cv2.bitwise_and(self.img_display, self.img_peephole, self.img_display)

        if self.config.img_display_data:
            self.show_data()
            cv2.bitwise_or(self.img_display, self.img_hex, self.img_display)

        self.img_display_viewport = self.img_display[self.config.view.y:self.config.view.y+self.config.view.h,
                                                     self.config.view.x:self.config.view.x+self.config.view.w]
        cv2.imshow(self.title, self.img_display_viewport)

    def auto_center(self, x, y):
        '''
        Auto center image global x/y coordinate on contiguous pixel x/y runs
        '''
        x_min = x
        while self.get_pixel(y, x_min) != 0.0:
            x_min -= 1
        x_max = x
        while self.get_pixel(y, x_max) != 0.0:
            x_max += 1
        x = x_min + ((x_max - x_min) / 2)
        y_min = y
        while self.get_pixel(y_min, x) != 0.0:
            y_min -= 1
        y_max = y
        while self.get_pixel(y_max, x) != 0.0:
            y_max += 1
        y = y_min + ((y_max - y_min) / 2)
        return x, y

    # draw grid
    def draw_line(self, x, y, direction, intersections):
        print ('draw_line', x, y, direction, intersections, len(self.grid_points_x), len(self.grid_points_y))

        if direction == 'H':
            print ('Draw H line', (0, y), (self.img_target.width, y))
            cv2.line(self.img_grid, (0, y), (self.img_target.width, y), (0xff, 0x00, 0x00),
                    1)
            for gridx in self.grid_points_x:
                print ('*****self.grid_points_x circle', (gridx, y), self.config.radius)
                cv2.circle(
                    self.img_grid, (gridx, y),
                    self.config.radius,
                    (0, 0, 0),
                    -1)
                cv2.circle(self.img_grid, (gridx, y), self.config.radius, (0xff, 0x00, 0x00))
                if intersections:
                    self.grid_intersections.append((gridx, y))
        else:
            cv2.line(self.img_grid, (x, 0), (x, self.img_target.height), (0xff, 0x00, 0x00),
                    1)
            for gridy in self.grid_points_y:
                cv2.circle(
                    self.img_grid, (x, gridy),
                    self.config.radius,
                    (0x00, 0x00, 0x00),
                    -1)
                cv2.circle(self.img_grid, (x, gridy), self.config.radius, (0xff, 0x00, 0x00))
                if intersections:
                    self.grid_intersections.append((x, gridy))
        self.show_image()
        print ('draw_line grid intersections:', len(self.grid_intersections))

    def show_data(self):
        if not self.data_read:
            return

        self.img_hex.fill(0)
        print()
        dat = self.get_all_data()
        for row in range(len(self.grid_points_y)):
            out = ''
            outbin = ''
            for column in range(len(self.grid_points_x) // self.group_cols):
                thisbyte = ord(dat[column * len(self.grid_points_y) + row])
                hexbyte = '%02X ' % thisbyte
                out += hexbyte
                outbin += to_bin(thisbyte) + ' '
                if self.config.img_display_binary:
                    disp_data = to_bin(thisbyte)
                else:
                    disp_data = hexbyte
                if self.config.img_display_data:
                    if self.Search_HEX and self.Search_HEX.count(thisbyte):
                        textcolor = (0x00, 0xff, 0xff)
                    else:
                        textcolor = (0xff, 0xff, 0xff)

                    cv2.putText(self.img_hex,
                                disp_data,
                                (self.grid_points_x[column * self.group_cols],
                                self.grid_points_y[row] + self.config.radius // 2 + 1),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                self.config.font_size,
                                textcolor)
            #print (outbin)
            #print()
            #print (out)
        print()
