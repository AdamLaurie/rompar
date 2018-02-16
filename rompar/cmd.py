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

import sys
import cv2.cv as cv
import traceback

from data import *
from gui import *
from config import *

def cmd_find(self, k):
    print 'Enter space delimeted HEX (in image window), e.g. 10 A1 EF: ',
    sys.stdout.flush()
    shx = ''
    while 42:
        c = cv.WaitKey(0)
        # BS or DEL
        if c == 65288 or c == 65535 or k == 65439:
            c = 0x08
        if c > 255:
            continue

        # Newline
        if c == 0x0d or c == 0x0a:
            print
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
        print 'Invalid hex value'
        return
    print 'searching for', shx.upper()


def cmd_save(self):
    print 'saving...'

    next_save(self)
    save_grid(self)

    if not self.data_read:
        print 'No bits to save'
    else:
        if 0 and self.save_dat:
            save_dat(self)
        save_txt(self)

def cmd_help():
    print 'a/A  decrease/increase radius of read aperture'
    print 'b    blank image (to view template)'
    print 'c    print status (ie configuration)'
    print 'd/D  decrease/increase dilation'
    print 'e/E  decrease/increase erosion'
    print 'f/F  decrease font size'
    print 'g    toggle grid display'
    print 'h    print help'
    print 'H    toggle binary / hex data display'
    print 'i    toggle invert data 0/1'
    print 'l    toggle LSB data order (default MSB)'
    print 'm/M  decrease/increase bit threshold divisor'
    print 'o    toggle original image display'
    print 'p    toggle peephole view'
    print 'q    quit'
    print 'r    read cols (end enter bit/grid editing mode)'
    print 'R    reset cols (and exit bit/grid editing mode)'
    print 's    show data values (HEX)'
    print 'S    save data and grid'
    print 't    apply threshold filter'
    print '-/+  decrease/increase threshold filter minimum'
    print '/    search for HEX (highlight when HEX shown)'
    print '?    print help'
    print

def cmd_help2():
    print 'to create template:'
    print
    print '  (note SHIFT will disable auto-centering)'
    print
    print '  columns:'
    print
    print '    left click on first bit in any row of any group'
    print '    left click on last bit in any row of that group'
    print '    left click on first bit in any row of each subsequent group'
    print
    print '  rows:'
    print
    print '    right click on any bit in first row of any group'
    print '    right click on any bit in last row of that group'
    print '    right click on any bit in each subsequent group'
    print
    print 'data/grid manipulation (after read command issued):'
    print
    print '  left click on any bit to toggle value'
    print '  right click to select row'
    print
    print '  in manipulation mode:'
    print
    print '  left-arrow to move entire column left'
    print '  right-arrow to move entire column right'
    print '  up-arrow to move entire row up'
    print '  down-arrow to move entire row down'
    print '  DEL to delete row'
    print '  BS to delete column'
    print

def on_key(self, k):
    if k == 65288 and self.Edit_x >= 0:
        # BS
        print 'deleting column'
        self.grid_points_x.remove(self.grid_points_x[self.Edit_x])
        self.Edit_x = -1
        read_data(self)
    elif k == K_LEFT:
        pan(self, -self.config.view.incx, 0)
    elif k == K_RIGHT:
        pan(self, self.config.view.incx, 0)
    elif k == K_UP:
        pan(self, 0, -self.config.view.incy)
    elif k == K_DOWN:
        pan(self, 0, self.config.view.incy)
        '''
    elif k == K_UP and self.Edit_y >= 0:
        # up arrow
        print 'editing line', self.Edit_y
        self.grid_points_y[self.grid_points_y.index(self.Edit_y)] -= 1
        self.Edit_y -= 1
        read_data(self)
    elif k == K_DOWN and self.Edit_y >= 0:
        # down arrow
        print 'editing line', self.Edit_y
        self.grid_points_y[self.grid_points_y.index(self.Edit_y)] += 1
        self.Edit_y += 1
        read_data(self)
    elif k == K_RIGHT and self.Edit_x >= 0:
        # right arrow - edit entrie column group
        print 'editing column', self.Edit_x
        sx = self.Edit_x - (self.Edit_x % self.group_cols)
        for x in range(sx, sx + self.group_cols):
            self.grid_points_x[x] += 1
        read_data(self)
    elif k == K_LEFT and self.Edit_x >= 0:
        # left arrow
        print 'editing column', self.Edit_x
        sx = self.Edit_x - (self.Edit_x % self.group_cols)
        for x in range(sx, sx + self.group_cols):
            self.grid_points_x[x] -= 1
        read_data(self)
        '''
    elif k == 65432 and self.Edit_x >= 0:
        # right arrow on numpad - edit single column
        print 'editing column', self.Edit_x
        self.grid_points_x[self.Edit_x] += 1
        read_data(self)
    elif k == 65430 and self.Edit_x >= 0:
        # left arrow on numpad - edit single column
        print 'editing column', self.Edit_x
        self.grid_points_x[self.Edit_x] -= 1
        read_data(self)
    elif (k == 65439 or k == 65535) and self.Edit_y >= 0:
        # delete
        print 'deleting row', self.Edit_y
        self.grid_points_y.remove(self.Edit_y)
        self.Edit_y = -1
        read_data(self)
    elif k == chr(10):
        # enter
        self.Edit_x = -1
        self.Edit_y = -1
        print 'Done editing'
        read_data(self)
    elif k == 'a':
        if self.config.radius:
            self.config.radius -= 1
            read_data(self)
        print 'Radius: %d' % self.config.radius
    elif k == 'A':
        self.config.radius += 1
        read_data(self)
        print 'Radius: %d' % self.config.radius
    elif k == 'b':
        self.config.img_display_blank_image = not self.config.img_display_blank_image
    elif k == 'c':
        print_config(self)
    elif k == 'd':
        self.config.dilate = max(self.config.dilate - 1, 0)
        print 'Dilate: %d' % self.config.dilate
        read_data(self)
    elif k == 'D':
        self.config.dilate += 1
        print 'Dilate: %d' % self.config.dilate
        read_data(self)
    elif k == 'e':
        self.config.erode = max(self.config.erode - 1, 0)
        print 'Erode: %d' % self.config.erode
        read_data(self)
    elif k == 'E':
        self.config.erode += 1
        print 'Erode: %d' % self.config.erode
        read_data(self)
    elif k == 'f':
        if self.config.font_size > 0.1:
            self.config.font_size -= 0.1
            self.font = cv.InitFont(
                cv.CV_FONT_HERSHEY_SIMPLEX,
                hscale=self.config.font_size,
                vscale=1.0,
                shear=0,
                thickness=1,
                lineType=8)
        print 'Font size: %d' % self.config.font_size
    elif k == 'F':
        self.config.font_size += 0.1
        self.font = cv.InitFont(
            cv.CV_FONT_HERSHEY_SIMPLEX,
            hscale=self.config.font_size,
            vscale=1.0,
            shear=0,
            thickness=1,
            lineType=8)
        print 'Font size: %d' % self.config.font_size
    elif k == 'g':
        self.config.img_display_grid = not self.config.img_display_grid
        print 'Display grid:', self.config.img_display_grid
    elif k == 'h' or k == '?':
        cmd_help()
    elif k == 'H':
        self.config.img_display_binary = not self.config.img_display_binary
        print 'Display binary:', self.config.img_display_binary
    elif k == 'i':
        self.inverted = not self.inverted
        print 'Inverted:', self.inverted
    elif k == 'l':
        self.config.LSB_Mode = not self.config.LSB_Mode
        print 'LSB self.data mode:', self.config.LSB_Mode
    elif k == 'm':
        self.config.bit_thresh_div -= 1
        print 'thresh_div:', self.config.bit_thresh_div
        read_data(self)
    elif k == 'M':
        self.config.bit_thresh_div += 1
        print 'thresh_div:', self.config.bit_thresh_div
        read_data(self)
    elif k == 'o':
        self.config.img_display_original = not self.config.img_display_original
        print 'display original:', self.config.img_display_original
    elif k == 'p':
        self.config.img_display_peephole = not self.config.img_display_peephole
        print 'display peephole:', self.config.img_display_peephole
    elif k == 'r':
        print 'reading %d points...' % len(self.grid_intersections)
        read_data(self, force=True)
    elif k == 'R':
        redraw_grid(self)
        self.data_read = False
    elif k == 's':
        self.config.img_display_data = not self.config.img_display_data
        print 'show data:', self.config.img_display_data
    elif k == 'S':
        cmd_save(self)
    elif k == 'q':
        print "Exiting on q"
        self.running = False
    elif k == 't':
        self.config.threshold = True
        print 'Threshold:', self.config.threshold
    elif k == '-':
        self.config.pix_thresh_min = max(self.config.pix_thresh_min - 1, 0x01)
        print 'Threshold filter %02x' % self.config.pix_thresh_min
        if self.data_read:
            read_data(self)
    elif k == '+':
        self.config.pix_thresh_min = min(self.config.pix_thresh_min + 1, 0xFF)
        print 'Threshold filter %02x' % self.config.pix_thresh_min
        if self.data_read:
            read_data(self)
    elif k == '/':
        cmd_find(self, k)
    #else:
    #    print 'Unknown command %s' % k

def do_loop(self):
    # image processing
    if self.config.threshold:
        cv.Threshold(self.img_original, self.img_target, self.config.pix_thresh_min, 0xff, cv.CV_THRESH_BINARY)
        cv.And(self.img_target, self.img_mask, self.img_target)
    if self.config.dilate:
        cv.Dilate(self.img_target, self.img_target, iterations=self.config.dilate)
    if self.config.erode:
        cv.Erode(self.img_target, self.img_target, iterations=self.config.erode)
    show_image(self)

    sys.stdout.write('> ')
    sys.stdout.flush()
    # keystroke processing
    ki = cv.WaitKey(0)

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
        print '%d (%s)\n' % (ki, kc)
    else:
        print '%d\n' % ki

    if ki > 66000:
        return
    if ki < 0:
        print "Exiting on closed window"
        self.running = False
        return
    on_key(self, k)


def run(selfl, img_fn=None, grid_file=None):
    global self
    self = selfl

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

    #self.img_original= cv.LoadImage(img_fn, iscolor=cv.CV_LOAD_IMAGE_GRAYSCALE)
    #self.img_original= cv.LoadImage(img_fn, iscolor=cv.CV_LOAD_IMAGE_COLOR)
    self.img_original = cv.LoadImage(self.img_fn)
    print 'Image is %dx%d' % (self.img_original.width, self.img_original.height)

    self.basename = self.img_fn[:self.img_fn.find('.')]

    # image buffers
    self.img_target = cv.CreateImage(cv.GetSize(self.img_original), cv.IPL_DEPTH_8U, 3)
    self.img_grid = cv.CreateImage(cv.GetSize(self.img_original), cv.IPL_DEPTH_8U, 3)
    self.img_mask = cv.CreateImage(cv.GetSize(self.img_original), cv.IPL_DEPTH_8U, 3)
    self.img_peephole = cv.CreateImage(cv.GetSize(self.img_original), cv.IPL_DEPTH_8U, 3)
    cv.Set(self.img_mask, cv.Scalar(0x00, 0x00, 0xff))
    self.img_display = cv.CreateImage(cv.GetSize(self.img_original), cv.IPL_DEPTH_8U, 3)
    cv.Set(self.img_grid, cv.Scalar(0, 0, 0))
    self.img_blank = cv.CreateImage(cv.GetSize(self.img_original), cv.IPL_DEPTH_8U, 3)
    cv.Set(self.img_blank, cv.Scalar(0, 0, 0))
    self.img_hex = cv.CreateImage(cv.GetSize(self.img_original), cv.IPL_DEPTH_8U, 3)
    cv.Set(self.img_hex, cv.Scalar(0, 0, 0))

    self.config.font_size = 1.0
    self.font = cv.InitFont(
        cv.CV_FONT_HERSHEY_SIMPLEX,
        hscale=self.config.font_size,
        vscale=1.0,
        shear=0,
        thickness=1,
        lineType=8)

    self.title = "rompar %s" % img_fn
    cv.NamedWindow(self.title, 1)
    cv.SetMouseCallback(self.title, on_mouse, self)

    self.img_target = cv.CloneImage(self.img_original)

    if grid_json:
        load_grid(self, grid_json)

    cmd_help()
    cmd_help2()

    # main loop
    while self.running:
        try:
            do_loop(self)
        except Exception:
            if self.debug:
                raise
            print 'WARNING: exception'
            traceback.print_exc()

    print 'Exiting'
