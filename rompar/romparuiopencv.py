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
from __future__ import print_function
from __future__ import division

import cv2
import os
import sys
import traceback

from .rompar import ImgXY

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

class RomparUIOpenCV(object):
    def __init__(self, romp, debug=False):
        self.romp = romp
        self.debug = debug
        self.config = self.romp.config
        self.title = "rompar %s" % self.romp.img_fn
        self.saven = 0
        self.basename = self.romp.img_fn[:self.romp.img_fn.find('.')]

        # Process events while true
        self.running = True

    def run(self):
        cv2.namedWindow(self.title, cv2.WINDOW_GUI_NORMAL)
        cv2.setMouseCallback(self.title, self.on_mouse, None)

        RomparUIOpenCV.cmd_help()
        RomparUIOpenCV.cmd_help2()

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

    def display_image(self):
        img = self.romp.render_image()
        img_display_viewport = img[
            self.config.view.y:self.config.view.y+self.config.view.h,
            self.config.view.x:self.config.view.x+self.config.view.w]
        cv2.imshow(self.title, img_display_viewport)

    def do_loop(self):
        self.romp.process_image()
        self.display_image()

        sys.stdout.write('> ')
        sys.stdout.flush()
        # keystroke processing
        ki = cv2.waitKeyEx(0)
        print("raw key", ki)

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

    def on_key(self, k):
        if k == 65288 and self.romp.Edit_x >= 0:
            # BS
            print ('deleting column')
            self.romp.grid_points_x.remove(self.romp.grid_points_x[self.romp.Edit_x])
            self.romp.Edit_x = -1
            self.romp.read_data()
        elif k == K_LEFT:
            self.pan(-self.config.view.incx, 0)
        elif k == K_RIGHT:
            self.pan(self.config.view.incx, 0)
        elif k == K_UP:
            self.pan(0, -self.config.view.incy)
        elif k == K_DOWN:
            self.pan(0, self.config.view.incy)
            '''
        elif k == K_UP and self.romp.Edit_y >= 0:
            # up arrow
            print ('editing line', self.romp.Edit_y)
            self.romp.grid_points_y[self.romp.grid_points_y.index(self.romp.Edit_y)] -= 1
            self.romp.Edit_y -= 1
            self.romp.read_data()
        elif k == K_DOWN and self.romp.Edit_y >= 0:
            # down arrow
            print ('editing line', self.romp.Edit_y)
            self.romp.grid_points_y[self.romp.grid_points_y.index(self.romp.Edit_y)] += 1
            self.romp.Edit_y += 1
            self.romp.read_data()
        elif k == K_RIGHT and self.romp.Edit_x >= 0:
            # right arrow - edit entrie column group
            print ('editing column', self.romp.Edit_x)
            sx = self.romp.Edit_x - (self.romp.Edit_x % self.romp.group_cols)
            for x in range(sx, sx + self.romp.group_cols):
                self.romp.grid_points_x[x] += 1
            self.romp.read_data()
        elif k == K_LEFT and self.romp.Edit_x >= 0:
            # left arrow
            print ('editing column', self.romp.Edit_x)
            sx = self.romp.Edit_x - (self.romp.Edit_x % self.romp.group_cols)
            for x in range(sx, sx + self.romp.group_cols):
                self.romp.grid_points_x[x] -= 1
            self.romp.read_data()
            '''
        elif k == 65432 and self.romp.Edit_x >= 0:
            # right arrow on numpad - edit single column
            print ('editing column', self.romp.Edit_x)
            self.romp.grid_points_x[self.romp.Edit_x] += 1
            self.romp.read_data()
        elif k == 65430 and self.romp.Edit_x >= 0:
            # left arrow on numpad - edit single column
            print ('editing column', self.romp.Edit_x)
            self.romp.grid_points_x[self.romp.Edit_x] -= 1
            self.romp.read_data()
        elif (k == 65439 or k == 65535) and self.romp.Edit_y >= 0:
            # delete
            print ('deleting row', self.romp.Edit_y)
            self.romp.grid_points_y.remove(self.romp.Edit_y)
            self.romp.Edit_y = -1
            self.romp.read_data()
        elif k == chr(10):
            # enter
            self.romp.Edit_x = -1
            self.romp.Edit_y = -1
            print ('Done editing')
            self.romp.read_data()
        elif k == 'a':
            if self.config.radius:
                self.config.radius -= 1
                self.romp.read_data()
            print ('Radius: %d' % self.config.radius)
        elif k == 'A':
            self.config.radius += 1
            self.romp.read_data()
            print ('Radius: %d' % self.config.radius)
        elif k == 'b':
            self.config.img_display_blank_image = not self.config.img_display_blank_image
        elif k == 'c':
            self.print_config()
        elif k == 'd':
            self.config.dilate = max(self.config.dilate - 1, 0)
            print ('Dilate: %d' % self.config.dilate)
            self.romp.read_data()
        elif k == 'D':
            self.config.dilate += 1
            print ('Dilate: %d' % self.config.dilate)
            self.romp.read_data()
        elif k == 'e':
            self.config.erode = max(self.config.erode - 1, 0)
            print ('Erode: %d' % self.config.erode)
            self.romp.read_data()
        elif k == 'E':
            self.config.erode += 1
            print ('Erode: %d' % self.config.erode)
            self.romp.read_data()
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
            self.config.inverted = not self.config.inverted
            print ('Inverted:', self.config.inverted)
        elif k == 'l':
            self.config.LSB_Mode = not self.config.LSB_Mode
            print ('LSB self.romp.data mode:', self.config.LSB_Mode)
        elif k == 'm':
            self.config.bit_thresh_div -= 1
            print ('thresh_div:', self.config.bit_thresh_div)
            self.romp.read_data()
        elif k == 'M':
            self.config.bit_thresh_div += 1
            print ('thresh_div:', self.config.bit_thresh_div)
            self.romp.read_data()
        elif k == 'o':
            self.config.img_display_original = not self.config.img_display_original
            print ('display original:', self.config.img_display_original)
        elif k == 'p':
            self.config.img_display_peephole = not self.config.img_display_peephole
            print ('display peephole:', self.config.img_display_peephole)
        elif k == 'r':
            print ('reading %d points...' % (len(self.romp.grid_points_y)*
                                             len(self.romp.grid_points_x)))
            self.romp.read_data(force=True)
        elif k == 'R':
            self.romp.redraw_grid()
            self.romp.data_read = False
        elif k == 's':
            self.config.img_display_data = not self.config.img_display_data
            print ('show data:', self.config.img_display_data)
        elif k == 'S':
            print ('saving...')
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
            self.romp.read_data()
        elif k == '+':
            self.config.pix_thresh_min = min(self.config.pix_thresh_min + 1, 0xFF)
            print ('Threshold filter %02x' % self.config.pix_thresh_min)
            self.romp.read_data()
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
            self.romp.Search_HEX = [int(h, 16) for h in shx.strip().split(' ')]
        except ValueError:
            print ('Invalid hex value')
            return
        print ('searching for', shx.upper())

        # mouse events
    def on_mouse(self, event, mouse_x, mouse_y, flags, param):
        img_xy = ImgXY(mouse_x + self.config.view.x,
                       mouse_y + self.config.view.y)

        # draw vertical grid lines
        if event == cv2.EVENT_LBUTTONDOWN:
            self.on_mouse_left(img_xy, flags)
        if event == cv2.EVENT_RBUTTONDOWN:
            self.on_mouse_right(img_xy, flags)

    def on_mouse_left(self, img_xy, flags):
        if self.romp.data_read:
            try:
                self.romp.toggle_data(self.romp.imgxy_to_bitxy(img_xy))
                self.display_image()
            except IndexError as e:
                print("No bit toggled")
        else:
            do_autocenter = flags != cv2.EVENT_FLAG_SHIFTKEY
            self.romp.grid_add_vertical_line(img_xy, do_autocenter)
            self.display_image()

    def on_mouse_right(self, img_xy, flags):
        if self.romp.data_read:
            try:
                self.romp.Edit_x, self.romp.Edit_y = self.romp.imgxy_to_bitxy(img_xy)
                self.romp.read_data()
                self.display_image()
                print("Edit x,y:", self.romp.Edit_x, self.romp.Edit_y)
            except IndexError as e:
                print("No bit group selected")
        else:
            do_autocenter = flags != cv2.EVENT_FLAG_SHIFTKEY
            self.romp.grid_add_horizontal_line(img_xy, do_autocenter)
            self.display_image()

    def next_save(self):
        '''Look for next unused save slot by checking grid files'''
        while True:
            fn = self.basename + '_s%d.grid' % self.saven
            if not os.path.exists(fn):
                break
            self.saven += 1

    def cmd_save(self):
        self.next_save()

        fn = self.basename + '_s%d.json' % self.saven
        symlinka(fn, self.basename + '.json')
        with open(fn, 'w') as f:
            self.romp.save_grid(f)
        print ('Saved %s' % fn)

        if self.romp.data_read:
            '''Write text file like bits sown in GUI. Space between row/cols'''
            fn = self.basename + '_s%d.txt' % self.saven
            symlinka(fn, self.basename + '.txt')
            with open(fn, 'w') as f:
                self.romp.write_data_as_txt(f)
            print ('Saved %s' % fn)
        else:
            print ('No bits to save')

    def pan(self, x, y):
        import ipdb
        ipdb.set_trace()
        self.config.view.x = min(max(0, self.config.view.x + x),
                                 self.romp.width - self.config.view.w)
        self.config.view.y = min(max(0, self.config.view.y + y),
                                 self.romp.height - self.config.view.h)

    def print_config(self):
        print ('Display')
        print ('  Grid      %s' % self.config.img_display_grid)
        print ('  Original  %s' % self.config.img_display_original)
        print ('  Peephole  %s' % self.config.img_display_peephole)
        print ('  Data      %s' % self.config.img_display_data)
        print ('    As binary %s' % self.config.img_display_binary)
        print ('Pixel processing')
        print ('  Bit threshold divisor   %s' % self.config.bit_thresh_div)
        print ('  Pixel threshold minimum %s (0x%02X)' % \
               (self.config.pix_thresh_min, self.config.pix_thresh_min))
        print ('  Dilate    %s' % self.config.dilate)
        print ('  Erode     %s' % self.config.erode)
        print ('  Radius    %s' % self.config.radius)
        print ('  Threshold %s' % self.config.threshold)
        print ('  Step')
        print ('    X       % 5.1f' % self.romp.step_x)
        print ('    Y       % 5.1f' % self.romp.step_y)
        print ('Bit state')
        print ('  Data read %d' % self.romp.data_read)
        print ('  Bits per group')
        print ('    X       %d cols' % self.romp.group_cols)
        print ('    Y       %d rows' % self.romp.group_rows)
        print ('  Bit points total')
        print ('    X       %d cols' % len(self.romp.grid_points_x))
        print ('    Y       %d rows' % len(self.romp.grid_points_y))
        print ('  Inverted  %d' % self.config.inverted)
        print ('  Intersections %d' % (len(self.romp.grid_points_x)*\
                                       len(self.romp.grid_points_y)))
        print ('  Viewport')
        print ('    X       %d' % self.config.view.x)
        print ('    Y       %d' % self.config.view.y)
        print ('    W       %d' % self.config.view.w)
        print ('    H       %d' % self.config.view.h)
        print ('    PanX    %d' % self.config.view.incx)
        print ('    PanY    %d' % self.config.view.incy)

    @staticmethod
    def cmd_help():
        print('a/A  decrease/increase radius of read aperture')
        print('b    blank image (to view template)')
        print('c    print status (ie configuration)')
        print('d/D  decrease/increase dilation')
        print('e/E  decrease/increase erosion')
        print('f/F  decrease font size')
        print('g    toggle grid display')
        print('h    print help')
        print('H    toggle binary / hex data display')
        print('i    toggle invert data 0/1')
        print('l    toggle LSB data order (default MSB)')
        print('m/M  decrease/increase bit threshold divisor')
        print('o    toggle original image display')
        print('p    toggle peephole view')
        print('q    quit')
        print('r    read cols (end enter bit/grid editing mode)')
        print('R    reset cols (and exit bit/grid editing mode)')
        print('s    show data values (HEX)')
        print('S    save data and grid')
        print('t    apply threshold filter')
        print('-/+  decrease/increase threshold filter minimum')
        print('/    search for HEX (highlight when HEX shown)')
        print('?    print help')
        print()

    @staticmethod
    def cmd_help2():
        print('to create template:')
        print()
        print('  (note SHIFT will disable auto-centering)')
        print()
        print('  columns:')
        print()
        print('    left click on first bit in any row of any group')
        print('    left click on last bit in any row of that group')
        print('    left click on first bit in any row of each subsequent group')
        print()
        print('  rows:')
        print()
        print('    right click on any bit in first row of any group')
        print('    right click on any bit in last row of that group')
        print('    right click on any bit in each subsequent group')
        print()
        print('data/grid manipulation (after read command issued):')
        print()
        print('  left click on any bit to toggle value')
        print('  right click to select row')
        print()
        print('  in manipulation mode:')
        print()
        print('  left-arrow to move entire column left')
        print('  right-arrow to move entire column right')
        print('  up-arrow to move entire row up')
        print('  down-arrow to move entire row down')
        print('  DEL to delete row')
        print('  BS to delete column')
        print()
