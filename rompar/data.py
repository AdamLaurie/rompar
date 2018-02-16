# Modifications by John McMaster <JohnDMcMaster@gmail.com>
# Original copyright below
#
#  rompar.py - semi-auto read masked rom
#
#  Adam Laurie <adam@aperturelabs.com>
#  http://www.aperturelabs.com
#
#  This code is copyright (c) Aperture Labs Ltd., 2013, All rights reserved.
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

import cv2.cv as cv
import os
import json

def redraw_grid(self):
    if not self.gui:
        return
    cv.Set(self.img_grid, cv.Scalar(0, 0, 0))
    cv.Set(self.img_peephole, cv.Scalar(0, 0, 0))
    self.grid_intersections = []
    self.grid_points_x.sort()
    self.grid_points_y.sort()

    for x in self.grid_points_x:
        cv.Line(self.img_grid, (x, 0), (x, self.img_target.height), cv.Scalar(0xff, 0x00, 0x00),
                1)
        for y in self.grid_points_y:
            self.grid_intersections.append((x, y))
    self.grid_intersections.sort()
    for y in self.grid_points_y:
        cv.Line(self.img_grid, (0, y), (self.img_target.width, y), cv.Scalar(0xff, 0x00, 0x00),
                1)
    for x, y in self.grid_intersections:
        cv.Circle(
            self.img_grid, (x, y), self.config.radius, cv.Scalar(0x00, 0x00, 0x00), thickness=-1)
        cv.Circle(
            self.img_grid, (x, y), self.config.radius, cv.Scalar(0xff, 0x00, 0x00), thickness=1)
        cv.Circle(
            self.img_peephole, (x, y),
            self.config.radius + 1,
            cv.Scalar(0xff, 0xff, 0xff),
            thickness=-1)

def get_pixel(self, x, y):
    return self.img_target[x, y][0] + self.img_target[x, y][1] + self.img_target[x, y][2]

# create binary printable string
def to_bin(x):
    return ''.join(x & (1 << i) and '1' or '0' for i in range(7, -1, -1))

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

def read_data(self, data_ref=None, force=False):
    if not force and not self.data_read:
        return

    redraw_grid(self)

    # maximum possible value if all pixels are set
    maxval = (self.config.radius * self.config.radius) * 255
    print 'read_data max aperture value:', maxval

    if data_ref:
        print 'read_data: loading reference data (%d entries)' % len(data_ref)
        print 'Grid intersections: %d' % len(self.grid_intersections)
        self.data = data_ref
    else:
        print 'read_data: computing'
        # Compute
        self.data = []
        for x, y in self.grid_intersections:
            value = 0
            # FIXME: misleading
            # This isn't a radius but rather a bounding box
            for xx in range(x - (self.config.radius / 2), x + (self.config.radius / 2)):
                for yy in range(y - (self.config.radius / 2), y + (self.config.radius / 2)):
                    value += get_pixel(self, yy, xx)
            if value > maxval / self.config.bit_thresh_div:
                self.data.append('1')
            else:
                self.data.append('0')

    # Render
    for i, (x, y) in enumerate(self.grid_intersections):
        if self.data[i] == '1':
            cv.Circle(
                self.img_grid, (x, y), self.config.radius, cv.Scalar(0x00, 0xff, 0x00), thickness=2)
            # highlight if we're in edit mode
            if y == self.Edit_y:
                sx = self.Edit_x - (self.Edit_x % self.group_cols)
                if self.grid_points_x.index(x) >= sx and self.grid_points_x.index(
                        x) < sx + self.group_cols:
                    cv.Circle(
                        self.img_grid, (x, y),
                        self.config.radius,
                        cv.Scalar(0xff, 0xff, 0xff),
                        thickness=2)
        else:
            pass
    self.data_read = True


def get_all_data(self):
    '''Return data as bytes'''
    out = ''
    for column in range(len(self.grid_points_x) / self.group_cols):
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
            for x in range(self.group_cols / 8):
                thisbyte = thischunk[x * 8:x * 8 + 8]
                # reverse self.group_cols if we want LSB
                if self.config.LSB_Mode:
                    thisbyte = thisbyte[::-1]
                out += chr(int(thisbyte, 2))
    return out

def data_as_xy(self):
    '''Return data as binary chars in ret[(x, y)] map'''
    ret = {}
    for d, (x, y) in zip(self.data, self.grid_intersections):
        ret[(x, y)] = d
    return ret

def data_as_cr(self):
    '''Return data as binary chars in ret[(column, row)] map'''
    ret = {}
    xys = data_as_xy(self)
    for xi, x in enumerate(self.grid_points_x):
        for yi, y in enumerate(self.grid_points_y):
            ret[(xi, yi)] = xys[(x, y)]
    return ret

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

def symlinka(target, alias):
    '''Atomic symlink'''
    tmp = alias + '_'
    if os.path.exists(tmp):
        os.unlink(tmp)
    os.symlink(target, alias + '_')
    os.rename(tmp, alias)

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
    print 'Saved %s' % fn

def load_grid(self, grid_json=None, gui=True):
    self.gui = gui

    self.grid_intersections = grid_json['grid_intersections']
    data = grid_json['data']
    self.grid_points_x = grid_json['grid_points_x']
    self.grid_points_y = grid_json['grid_points_y']
    # self.config = grid_json['config']
    for k, v in grid_json['config'].iteritems():
        if k == 'view':
            for kv, vv in v.iteritems():
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

    print 'Grid points: %d x, %d y' % (len(self.grid_points_x), len(self.grid_points_y))
    squared = len(self.grid_points_x) * len(self.grid_points_y)
    if len(self.grid_intersections) != squared:
        print self.grid_points_x
        print self.grid_points_y
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
    redraw_grid(self)

    if data:
        print 'Initializing data'
        if len(data) != len(self.grid_intersections):
            raise Exception("%d != %d" % (len(data), len(self.grid_intersections)))    
        read_data(self, data_ref=data, force=True)

# self.data packed into column based bytes
def save_dat(self):
    out = get_all_data(self)
    columns = len(self.grid_points_x) / self.group_cols
    chunk = len(out) / columns
    for x in range(columns):
        fn = self.basename + '_s%d-%d.dat' % (self.saven, x)
        symlinka(fn, self.basename + '_%d.dat' % x)
        with open(fn, 'wb') as outfile:
            outfile.write(out[x * chunk:x * chunk + chunk])
            print '%s: %d bytes' % (fn, chunk)

def save_txt(self):
    '''Write text file like bits sown in GUI. Space between row/cols'''
    fn = self.basename + '_s%d.txt' % self.saven
    symlinka(fn, self.basename + '.txt')
    crs = data_as_cr(self)
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
    print 'Saved %s' % fn

def next_save(self):
    '''Look for next unused save slot by checking grid files'''
    while True:
        fn = self.basename + '_s%d.grid' % self.saven
        if not os.path.exists(fn):
            break
        self.saven += 1
