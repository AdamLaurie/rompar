from collections import namedtuple
import cv2 as cv
import os.path
import json
import numpy
import time
import pathlib

BLACK  = (0x00, 0x00, 0x00)
BLUE   = (0xff, 0x00, 0x00)
GREEN  = (0x00, 0xff, 0x00)
RED    = (0x00, 0x00, 0xff)
YELLOW = (0x00, 0xff, 0xff)
WHITE  = (0xff, 0xff, 0xff)

ImgXY = namedtuple('ImgXY', ['x', 'y'])
BitXY = namedtuple('BitXY', ['x', 'y'])

class Rompar(object):
    def __init__(self, config, *, img_fn=None, grid_json=None,
                 group_cols=0, group_rows=0, grid_dir_path=None):
        self.img_fn = pathlib.Path(img_fn).expanduser().absolute() \
                      if img_fn else None
        self.config = config

        # Allow skipping of process_target_image if nothing changed.
        self.__process_cache = None

        # Pixels between cols and rows
        self.step_x, self.step_y = (0, 0)
        # Number of rows/cols per bit grouping
        self.group_cols, self.group_rows = (group_cols, group_rows)

        self.Search_HEX = None

        # >= 0 when in edit mode
        self.Edit_x, self.Edit_y = (-1, -1)

        # Global
        self._grid_points_x = []
        self._grid_points_y = []

        if grid_json:
            if self.img_fn is None:
                # TODO: If absolute paths are supported in the json
                # file, then saving the grid file should probably not
                # write in a relative path. For now, all img_fn paths
                # should be relative.
                self.img_fn = pathlib.Path(grid_json.get('img_fn'))
                if not self.img_fn.is_absolute():
                    # Eventually, it would be nice if this class was
                    # unaware of the file system so it can be used
                    # with any data source (Files, Databases, etc) in
                    # any system configuration (desktop, web backend,
                    # etc). But that is not the case yet, so the
                    # current grid file's directory is necessary to
                    # calculate the relative path of img_fn when
                    # saving and loading a grid's configuration.
                    self.img_fn = grid_dir_path / self.img_fn
                    self.img_fn = self.img_fn.resolve()
            if self.group_cols is None:
                self.group_cols = grid_json.get('group_cols')
                self.group_rows = grid_json.get('group_rows')

            self._grid_points_x = sorted(set(grid_json['grid_points_x']))
            self._grid_points_y = sorted(set(grid_json['grid_points_y']))
            self.config.update(grid_json['config'])

            print ('Grid points: %d x, %d y' % (len(self._grid_points_x),
                                                len(self._grid_points_y)))

            if len(self._grid_points_x) > 1:
                self.step_x = (self._grid_points_x[self.group_cols - 1] -
                               self._grid_points_x[0]) / \
                              (self.group_cols - 1)
            if len(self._grid_points_y) > 1:
                self.step_y = (self._grid_points_y[self.group_rows - 1] -
                               self._grid_points_y[0]) / \
                              (self.group_rows - 1)
            if not self.config.default_radius:
                if self.step_x:
                    self.config.radius = int(self.step_x / 3)
                else:
                    self.config.radius = int(self.step_y / 3)

        # Then need critical args
        if not self.img_fn:
            raise Exception("Filename required")
        if not self.group_cols:
            raise Exception("cols required")
        if not self.group_rows:
            raise Exception("rows required")

        #load img as numpy ndarray dimensions (height, width, channels)
        self.img_original = cv.imread(str(self.img_fn), cv.IMREAD_COLOR)
        print ('Image is %dx%d; %d channels' %
               (self.img_width, self.img_height, self.img_channels))

        # Image buffers
        self.img_target = numpy.copy(self.img_original)
        self.img_grid = numpy.zeros(self.img_original.shape, numpy.uint8)
        self.img_peephole = numpy.zeros(self.img_original.shape, numpy.uint8)

        self.__process_target_image()

        self.__data = numpy.ndarray((self.bit_height, self.bit_width), dtype=bool)

        if not (grid_json and grid_json['data'] and
                self.__parse_grid_bit_data(grid_json['data'])):
            self.read_data()

    def __parse_grid_bit_data(self, data):
        if isinstance(data, list):
            try:
                data = "".join(data)
            except Exception as e:
                print("File 'data' field is in unknown format. Ignoring.")
                return False
        if not isinstance(data, str):
            print("File 'data' field is incompatible type '%s'. Ignoring." %\
                  str(type(data)))
            return False
        if (self.bit_height*self.bit_width) != len(data):
            print("Data length (%d) is different than the number of "
                  "grid intersections (%d). Ignoring data" %
                  (len(data), self.bit_height*self.bit_width))
            return False
        if set(data).difference({'0', '1'}):
            print("File 'data' contains not 0/1 characters: %s." %\
                  set(data).difference({'0', '1'}))
            return False

        bit_iter = (bit == '1' for bit in data)
        for bit_x in range(self.bit_width):
            for bit_y in range(self.bit_height):
                self.set_data(BitXY(bit_x, bit_y), next(bit_iter))
        return True

    def redraw_grid(self):
        self.img_grid.fill(0)
        self.img_peephole.fill(0)

        t = time.time()
        for x in self._grid_points_x:
            cv.line(self.img_grid, (x, 0), (x, self.img_height), BLUE, 1)
        for y in self._grid_points_y:
            cv.line(self.img_grid, (0, y), (self.img_width, y), BLUE, 1)
        print("grid line redraw time:", time.time()-t)

        t = time.time()
        for bit_xy in self.iter_bitxy():
            img_xy = self.bitxy_to_imgxy(bit_xy)
            sx = self.Edit_x - (self.Edit_x % self.group_cols)
            if bit_xy.x == self.Edit_x or\
               (bit_xy.y == self.Edit_y and \
                (sx <= bit_xy.x < (sx + self.group_cols))):
                if self.get_data(bit_xy, inv=self.config.inverted):
                    color = WHITE # highlight if we're in edit mode
                else:
                    color = RED
            else:
                if self.get_data(bit_xy, inv=self.config.inverted):
                    color = GREEN
                else:
                    color = BLUE

            self.grid_draw_circle(img_xy, color, thick=2)
            cv.circle(self.img_peephole, img_xy, int(self.config.radius) + 1,
                      WHITE, -1)
        print("grid circle redraw time:", time.time()-t)

    def render_image(self, img_display=None, rgb=False):
        if img_display is None:
            img_display = numpy.ndarray(self.img_shape, numpy.uint8)
        else:
            if img_display.shape != self.img_shape:
                raise ValueError("Image must have the same shape as the Rompar")

        t = time.time()
        if self.config.img_display_blank_image:
            img_display.fill(0)
        elif self.config.img_display_original:
            numpy.copyto(img_display, self.img_original)
        else:
            numpy.copyto(img_display, self.img_target)

        if self.config.img_display_grid:
            self.redraw_grid()
            cv.bitwise_or(img_display, self.img_grid, img_display)

        if self.config.img_display_peephole:
            cv.bitwise_and(img_display, self.img_peephole, img_display)

        if self.config.img_display_data:
            self.render_data_layer(img_display)

        print("render_image time:", time.time()-t)

        if rgb:
            cv.cvtColor(img_display, cv.COLOR_BGR2RGB, img_display);

        return img_display

    def read_data(self, bit_pairs=None):
        process_redone = self.__process_target_image()
        if process_redone or bit_pairs is None:
            bit_pairs = self.iter_bitxy()

        # maximum possible value if all pixels are set
        maxval = (self.config.radius ** 2) * 255
        thresh = (maxval / self.config.bit_thresh_div)
        delta = int(self.config.radius // 2)

        print('read_data: computing')
        for bit_xy in bit_pairs:
            img_xy = self.bitxy_to_imgxy(bit_xy)
            datasub = self.img_target[img_xy.y - delta:img_xy.y + delta,
                                      img_xy.x - delta:img_xy.x + delta]
            value = datasub.sum(dtype=int)
            self.set_data(bit_xy, value > thresh)

    def get_pixel(self, img_xy):
        img_x, img_y = img_xy
        return self.img_target[img_y, img_x].sum()

    def write_data_as_txt(self, f):
        for bit_y in range(self.bit_height):
            if bit_y and bit_y % self.group_rows == 0:
                f.write('\n') # Put a space between row gaps
            for bit_x in range(self.bit_width):
                if bit_x and bit_x % self.group_cols == 0:
                    f.write(' ')
                f.write("1" if self.get_data(BitXY(bit_x, bit_y)) else "0")
            f.write('\n') # Newline afer every row

    def dump_grid_configuration(self, grid_dir_path):
        config = dict(self.config.__dict__)
        config['view'] = config['view'].__dict__

        # Store the img path relative to the grid file
        img_fn_rel = os.path.relpath(str(self.img_fn), str(grid_dir_path))

        # XXX: this first cut is partly due to ease of converting old DB
        # Try to move everything non-volatile into config object
        j = {
            # Increment major when a fundamentally breaking change occurs
            # minor reserved for now, but could be used for non-breaking
            'version': (1, 0),
            #'grid_intersections': list(self.iter_grid_intersections()),
            'data': ["1" if self.get_data(BitXY(bit_x, bit_y)) else "0"
                     for bit_x in range(self.bit_width)
                     for bit_y in range(self.bit_height)],
            'grid_points_x': self._grid_points_x,
            'grid_points_y': self._grid_points_y,
            'fn': config,
            'group_cols': self.group_cols,
            'group_rows': self.group_rows,
            'config': config,
            'img_fn': img_fn_rel,
            }
        return j

    def __process_target_image(self):
        new_cache_value = (self.config.pix_thresh_min,
                           self.config.dilate, self.config.erode)
        if self.__process_cache == new_cache_value:
            return False
        self.__process_cache = new_cache_value

        t = time.time()
        cv.dilate(self.img_target, (3,3))
        cv.threshold(self.img_original, self.config.pix_thresh_min,
                     0xff, cv.THRESH_BINARY, self.img_target)
        cv.bitwise_and(self.img_target, (0, 0, 255), self.img_target)
        if self.config.dilate:
            cv.dilate(self.img_target, (3,3))
        if self.config.erode:
            cv.erode(self.img_target, (3,3))
        print("process_image time", time.time()-t)
        return True

    def bitx_to_imgx(self, bit_x):
        if (0 > bit_x >= self.bit_width):
            raise IndexError("Bit x-coodrinate (%d) out of range"%bit_x)
        return self._grid_points_x[bit_x]

    def bity_to_imgy(self, bit_y):
        if (0 > bit_y >= self.bit_width):
            raise IndexError("Bit y-coodrinate (%d) out of range"%bit_y)
        return self._grid_points_y[bit_y]

    def bitxy_to_imgxy(self, bit_xy):
        bit_x, bit_y = bit_xy
        if (0 > bit_x >= self.bit_width) or \
           (0 > bit_y >= self.bit_height):
            raise IndexError("Bit coodrinate (%d, %d) out of range"%bit_xy)
        return ImgXY(self._grid_points_x[bit_x], self._grid_points_y[bit_y])

    def imgxy_to_bitxy(self, img_xy, autocenter=True):
        img_x, img_y = img_xy
        if (0 > img_x >= self.img_width) or (0 > img_y >= self.img_height):
            raise IndexError("Image coodrinate (%d, %d) out of range"%img_xy)

        if autocenter:
            delta = self.config.radius / 2
            for bit_x, x in enumerate(self._grid_points_x):
                if (x - delta) <= img_x <= (x + delta):
                    for bit_y, y in enumerate(self._grid_points_y):
                        if (y - delta) <= img_y <= (y + delta):
                            return BitXY(bit_x, bit_y)
            raise IndexError("No bit near image coordinate (%d, %d)"%img_xy)
        else:
            try:
                return BitXY(self._grid_points_x.index(img_x),
                             self._grid_points_y.index(img_y))
            except ValueError:
                raise IndexError("No bit at image coordinate (%d, %d)"%img_xy)

    def get_data(self, bit_xy, inv=False):
        bit_x, bit_y = bit_xy
        ret = self.__data[bit_y, bit_x]
        return (not ret) if inv else (ret)

    def set_data(self, bit_xy, val):
        bit_x, bit_y = bit_xy
        self.__data[bit_y, bit_x] = bool(val)
        return bool(val)

    def toggle_data(self, bit_xy):
        return self.set_data(bit_xy, not self.get_data(bit_xy))

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

    def auto_center(self, img_xy):
        '''
        Auto center image global x/y coordinate on contiguous pixel x/y runs
        '''
        img_x, img_y = img_xy
        x_min = img_x
        while self.get_pixel((img_y, x_min)) != 0.0:
            x_min -= 1
        x_max = img_x
        while self.get_pixel((img_y, x_max)) != 0.0:
            x_max += 1
        img_x = x_min + ((x_max - x_min) // 2)
        y_min = img_y
        while self.get_pixel((y_min, img_x)) != 0.0:
            y_min -= 1
        y_max = img_y
        while self.get_pixel((y_max, img_x)) != 0.0:
            y_max += 1
        img_y = y_min + ((y_max - y_min) // 2)
        return ImgXY(img_x, img_y)

    #def draw_Hline(self, img_y, intersections):
    #    cv.line(self.img_grid, (0, img_y), (self.img_width, img_y), BLUE, 1)
    #    for gridx in self._grid_points_x:
    #        self.grid_draw_circle((gridx, img_y), BLUE)
    #
    #def draw_Vline(self, img_x, intersections):
    #    cv.line(self.img_grid, (img_x, 0), (img_x, self.img_height), BLUE, 1)
    #    for gridy in self._grid_points_y:
    #        self.grid_draw_circle((img_x, gridy), BLUE)

    def grid_draw_circle(self, img_xy, color, thick=1):
        cv.circle(self.img_grid, img_xy, int(self.config.radius), BLACK, -1)
        cv.circle(self.img_grid, img_xy, int(self.config.radius), color, thick)

    def render_data_layer(self, img):
        if img is None:
            img = numpy.zeros(self.img_shape, numpy.uint8)
        for bit_y in range(self.bit_height):
            for bit_column in range(self.bit_width // self.group_cols):
                for column_byte in range(self.group_cols // 8):
                    byte = ''
                    bit_group_x = bit_column*self.group_cols + column_byte*8
                    for bit_x_offset in range(8):
                        bit = self.get_data(BitXY(bit_group_x+bit_x_offset, bit_y),
                                            inv=self.config.inverted)
                        byte += "1" if bit else "0"
                    if self.config.LSB_Mode:
                        byte = byte[::-1]
                    num = int(byte, 2)

                    if self.config.img_display_binary:
                        disp_data = format(num, '08b')
                    else:
                        disp_data = format(num, "02X")

                    textcolor = WHITE
                    if self.Search_HEX and self.Search_HEX.count(num):
                        textcolor = YELLOW

                    cv.putText(
                        img,
                        disp_data,
                        self.bitxy_to_imgxy(BitXY(bit_group_x, bit_y)),
                        cv.FONT_HERSHEY_SIMPLEX,
                        self.config.font_size,
                        textcolor,
                        thickness=2)

        return img

    def add_bit_column(self, img_x):
        if img_x in self._grid_points_x:
            return False

        for i, x in enumerate(self._grid_points_x):
            if img_x < x:
                self._grid_points_x.insert(i, img_x)
                break
        else:
            i = len(self._grid_points_x)
            self._grid_points_x.append(img_x)

        self.__data = numpy.insert(self.__data, i, False, axis = 1)
        self.read_data(((i, tmp_y) for tmp_y in range(self.bit_height)))
        return True

    def add_bit_row(self, img_y):
        if img_y in self._grid_points_y:
            return False

        for i, y in enumerate(self._grid_points_y):
            if img_y < y:
                self._grid_points_y.insert(i, img_y)
                break
        else:
            i = len(self._grid_points_y)
            self._grid_points_y.append(img_y)

        self.__data = numpy.insert(self.__data, i, False, axis = 0)
        self.read_data(((tmp_x, i) for tmp_x in range(self.bit_width)))
        return True

    def del_bit_column(self, bit_x):
        if bit_x >= self.bit_width:
            return False

        del self._grid_points_x[bit_x]
        self.__data = numpy.delete(self.__data, bit_x, axis = 1)
        return True


    def del_bit_row(self, bit_y):
        if bit_y >= self.bit_height:
            return False

        del self._grid_points_y[bit_y]
        self.__data = numpy.delete(self.__data, bit_y, axis = 0)
        return True

    def move_bit_column(self, bit_x, new_img_x, relative=False):
        curr_img_x = self.bitx_to_imgx(bit_x)
        if relative:
            new_img_x += curr_img_x
        if new_img_x == curr_img_x or \
           new_img_x in self._grid_points_x:
            return False
        if self.del_bit_column(bit_x):
            self.add_bit_column(new_img_x)
            return True

    def move_bit_row(self, bit_y, new_img_y, relative=False):
        curr_img_y = self.bity_to_imgy(bit_y)
        if relative:
            new_img_y += curr_img_y
        if new_img_y == curr_img_y or \
           new_img_y in self._grid_points_y:
            return False
        if self.del_bit_row(bit_y):
            self.add_bit_row(new_img_y)
            return True

    def grid_add_vertical_line(self, img_xy, do_autocenter=True):
        if do_autocenter and not self.get_pixel(img_xy):
            print ('autocenter: miss!')
            return

        if do_autocenter:
            img_xy = self.auto_center(img_xy)

        img_x, img_y = img_xy
        if img_x in self._grid_points_x:
            return

        # only draw a single line if this is the first one
        if self.bit_width == 0 or self.group_cols == 1:
            self.add_bit_column(img_x)
        else:
            # set up auto draw
            start_i = 0
            if self.bit_width == 1:
                # use a float to reduce rounding errors
                self.step_x = (img_x - self._grid_points_x[0]) / \
                              (self.group_cols - 1)
                img_x = self._grid_points_x[0]
                start_i = 1
                self.update_radius()
            # draw a full set of self.group_cols
            for x in range(start_i, self.group_cols):
                draw_x = int(img_x + x * self.step_x)
                if draw_x > self.img_width:
                    break
                self.add_bit_column(draw_x)

    def grid_add_horizontal_line(self, img_xy, do_autocenter=True):
        if do_autocenter and not self.get_pixel(img_xy):
            print ('autocenter: miss!')
            return

        if do_autocenter:
            img_xy = self.auto_center(img_xy)

        img_x, img_y = img_xy
        if img_y in self._grid_points_y:
            return

        # only draw a single line if this is the first one
        if self.bit_height == 0 or self.group_rows == 1:
            self.add_bit_row(img_y)
        else:
            # set up auto draw
            start_i = 0
            if self.bit_height == 1:
                # use a float to reduce rounding errors
                self.step_y = (img_y - self._grid_points_y[0]) / \
                              (self.group_rows - 1)
                img_y = self._grid_points_y[0]
                start_i = 1
                self.update_radius()
            # draw a full set of self.group_rows
            for y in range(start_i, self.group_rows):
                draw_y = int(img_y + y * self.step_y)
                # only draw up to the edge of the image
                if draw_y > self.img_height:
                    break
                self.add_bit_row(draw_y)

    @property
    def img_width(self):
        return self.img_shape[1]
    @property
    def img_height(self):
        return self.img_shape[0]
    @property
    def img_channels(self):
        return self.img_shape[2]
    @property
    def img_shape(self):
        return self.img_original.shape

    @property
    def bit_width(self):
        return len(self._grid_points_x)
    @property
    def bit_height(self):
        return len(self._grid_points_y)

    def iter_grid_intersections(self):
        for img_x in self._grid_points_x:
            for img_y in self._grid_points_y:
                yield ImgXY(img_x, img_y)

    def iter_bitxy(self):
        for bit_x in range(self.bit_width):
            for bit_y in range(self.bit_height):
                yield BitXY(bit_x, bit_y)
