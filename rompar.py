#! /usr/bin/env python

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
#

import cv2.cv as cv
import sys
import pickle

class Rompar(object):
    def __init__(self):
        # Display options
        # Overlay bit position grid
        self.display_grid = True
        # Show source image (ie without thresholding)
        self.display_original = False
        # Remove image entirely, showing just decoded bits
        self.display_blank_image = False
        # Show image only in bit ROI
        self.display_peephole = False
        # Overlay hex data on image
        self.display_data = False
        # Overlay binary data on image
        self.display_binary = False
        self.thresh_div = 10
        # Pixel value >= to consider occupied
        self.thresh_min = 0xae

        # Image processing options
        self.dilate = 0
        self.erode = 0
        # Bit image radius as displayed on grid
        # Actual detection uses square around circle
        self.radius = 0
        # User supplied radius to be used in lieu of auto calculated
        self.default_radius = None
        self.Threshold = True
        self.Step_x = 0
        self.Step_y = 0

        self.LSB_Mode = False
        self.Search_HEX = None
        # Number of save commands issued
        # Used to create unique save file postfix per save
        self.saves = 0
        self.Edit_x = -1
        self.Edit_y = -1

        # Processed data
        self.Data = []
        self.Inverted = False
        self.Cols = 0
        self.Rows = 0
        self.Grid_Points_x = []
        self.Grid_Points_y = []
        self.Grid_Entries_x = 0
        self.Grid_Entries_y = 0
        self.Grid_Intersections = []
        # Have we attempted to decode bits?
        self.data_read = False

        # Misc
        # Process events while true
        self.running = True

def get_pixel(self, x, y):
    return self.Target[x, y][0] + self.Target[x, y][1] + self.Target[x, y][2]


# create binary printable string
def to_bin(x):
    return ''.join(x & (1 << i) and '1' or '0' for i in range(7, -1, -1))


def redraw_grid(self):
    cv.Set(self.Grid, cv.Scalar(0, 0, 0))
    cv.Set(self.Peephole, cv.Scalar(0, 0, 0))
    self.Grid_Intersections = []
    self.Grid_Points_x.sort()
    self.Grid_Points_y.sort()

    for x in self.Grid_Points_x:
        cv.Line(self.Grid, (x, 0), (x, self.Target.height), cv.Scalar(0xff, 0x00, 0x00),
                1)
        for y in self.Grid_Points_y:
            self.Grid_Intersections.append((x, y))
    self.Grid_Intersections.sort()
    for y in self.Grid_Points_y:
        cv.Line(self.Grid, (0, y), (self.Target.width, y), cv.Scalar(0xff, 0x00, 0x00),
                1)
    for x, y in self.Grid_Intersections:
        cv.Circle(
            self.Grid, (x, y), self.radius, cv.Scalar(0x00, 0x00, 0x00), thickness=-1)
        cv.Circle(
            self.Grid, (x, y), self.radius, cv.Scalar(0xff, 0x00, 0x00), thickness=1)
        cv.Circle(
            self.Peephole, (x, y),
            self.radius + 1,
            cv.Scalar(0xff, 0xff, 0xff),
            thickness=-1)

def update_radius(self):
    if self.radius:
        return

    if self.default_radius:
        self.radius = self.default_radius
    else:
        if self.Step_x:
            self.radius = int(self.Step_x / 3)
        elif self.Step_y:
            self.radius = int(self.Step_y / 3)

def on_mouse_left(event, mouse_x, mouse_y, flags, param):
    self = param

    # are we editing self.Data or grid?
    if self.data_read:
        # find nearest intersection and toggle its value
        for x in self.Grid_Points_x:
            if mouse_x >= x - self.radius / 2 and mouse_x <= x + self.radius / 2:
                for y in self.Grid_Points_y:
                    if mouse_y >= y - self.radius / 2 and mouse_y <= y + self.radius / 2:
                        value = toggle_data(x, y)
                        print self.Target[x, y]
                        #print 'value', value
                        if value == '0':
                            cv.Circle(
                                self.Grid, (x, y),
                                self.radius,
                                cv.Scalar(0xff, 0x00, 0x00),
                                thickness=2)
                        else:
                            cv.Circle(
                                self.Grid, (x, y),
                                self.radius,
                                cv.Scalar(0x00, 0xff, 0x00),
                                thickness=2)

                        show_image(self)
    else:
        #if not Target[mouse_y, mouse_x]:
        if not flags == cv.CV_EVENT_FLAG_SHIFTKEY and not get_pixel(self,
                mouse_y, mouse_x):
            print 'autocenter: miss!'
            return
    
        # only draw a single line if this is the first one
        if self.Grid_Entries_x == 0 or self.Cols == 1:
            if flags != cv.CV_EVENT_FLAG_SHIFTKEY:
                mouse_x, mouse_y = auto_center(self, mouse_x, mouse_y)

            self.Grid_Entries_x += 1
            # don't try to auto-center if shift key pressed
            draw_line(self, mouse_x, mouse_y, 'V', False)
            self.Grid_Points_x.append(mouse_x)
            if self.Rows == 1:
                draw_line(self, mouse_x, mouse_y, 'V', True)
        else:
            # set up auto draw
            if len(self.Grid_Points_x) == 1:
                # use a float to reduce rounding errors
                self.Step_x = float(mouse_x - self.Grid_Points_x[0]) / (self.Cols - 1)
                # reset stored self.Data as main loop will add all entries
                mouse_x = self.Grid_Points_x[0]
                self.Grid_Points_x = []
                self.Grid_Entries_x = 0
                update_radius()
            # draw a full set of self.Cols
            for x in range(self.Cols):
                self.Grid_Entries_x += 1
                draw_x = int(mouse_x + x * self.Step_x)
                self.Grid_Points_x.append(draw_x)
                draw_line(draw_x, mouse_y, 'V', True)

def on_mouse_right(event, mouse_x, mouse_y, flags, param):
    self = param

    # are we editing self.Data or grid?
    if self.data_read:
        # find row and select for editing
        for x in self.Grid_Points_x:
            for y in self.Grid_Points_y:
                if mouse_y >= y - self.radius / 2 and mouse_y <= y + self.radius / 2:
                    #print 'value', get_data(x,y)
                    # select the whole row
                    xcount = 0
                    for x in self.Grid_Points_x:
                        if mouse_x >= x - self.radius / 2 and mouse_x <= x + self.radius / 2:
                            self.Edit_x = xcount
                            break
                        else:
                            xcount += 1
                    # highlight the bit group we're in
                    sx = self.Edit_x - (self.Edit_x % self.Cols)
                    self.Edit_y = y
                    read_data(self)
                    show_image(self)
                    return
    else:
        if not flags == cv.CV_EVENT_FLAG_SHIFTKEY and not get_pixel(self,
                mouse_y, mouse_x):
            print 'autocenter: miss!'
            return
        # only draw a single line if this is the first one
        if self.Grid_Entries_y == 0 or self.Rows == 1:
            if flags != cv.CV_EVENT_FLAG_SHIFTKEY:
                mouse_x, mouse_y = auto_center(self, mouse_x, mouse_y)

            self.Grid_Entries_y += 1
            draw_line(self, mouse_x, mouse_y, 'H', False)
            self.Grid_Points_y.append(mouse_y)
            if self.Rows == 1:
                draw_line(self, mouse_x, mouse_y, 'H', True)
        else:
            # set up auto draw
            if len(self.Grid_Points_y) == 1:
                # use a float to reduce rounding errors
                self.Step_y = float(mouse_y - self.Grid_Points_y[0]) / (self.Rows - 1)
                # reset stored self.Data as main loop will add all entries
                mouse_y = self.Grid_Points_y[0]
                self.Grid_Points_y = []
                self.Grid_Entries_y = 0
                update_radius()
            # draw a full set of self.Rows
            for y in range(self.Rows):
                draw_y = int(mouse_y + y * self.Step_y)
                # only draw up to the edge of the image
                if draw_y > self.Img.height:
                    break
                self.Grid_Entries_y += 1
                self.Grid_Points_y.append(draw_y)
                draw_line(self, mouse_x, draw_y, 'H', True)


# mouse events
def on_mouse(event, mouse_x, mouse_y, flags, param):
    # draw vertical grid lines
    if event == cv.CV_EVENT_LBUTTONDOWN:
        on_mouse_left(event, mouse_x, mouse_y, flags, param)
    # draw horizontal grid lines
    elif event == cv.CV_EVENT_RBUTTONDOWN:
        on_mouse_right(event, mouse_x, mouse_y, flags, param)


def show_image(self):
    if self.display_original:
        self.Display = cv.CloneImage(self.Img)
    else:
        self.Display = cv.CloneImage(self.Target)

    if self.display_blank_image:
        self.Display = cv.CloneImage(self.Blank)

    if self.display_grid:
        cv.Or(self.Display, self.Grid, self.Display)

    if self.display_peephole:
        cv.And(self.Display, self.Peephole, self.Display)

    if self.display_data:
        show_data(self)
        cv.Or(self.Display, self.Hex, self.Display)

    cv.ShowImage(self.title, self.Display)

def auto_center(self, x, y):
    x_min = x
    while get_pixel(self, y, x_min) != 0.0:
        x_min -= 1
    x_max = x
    while get_pixel(self, y, x_max) != 0.0:
        x_max += 1
    x = x_min + ((x_max - x_min) / 2)
    y_min = y
    while get_pixel(self, y_min, x) != 0.0:
        y_min -= 1
    y_max = y
    while get_pixel(self, y_max, x) != 0.0:
        y_max += 1
    y = y_min + ((y_max - y_min) / 2)
    return x, y

# draw grid
def draw_line(self, x, y, direction, intersections):
    print 'draw_line', x, y, direction, intersections, len(self.Grid_Points_x), len(self.Grid_Points_y)

    if direction == 'H':
        print 'Draw H line', (0, y), (self.Target.width, y)
        cv.Line(self.Grid, (0, y), (self.Target.width, y), cv.Scalar(0xff, 0x00, 0x00),
                1)
        for gridx in self.Grid_Points_x:
            print '*****self.Grid_Points_x circle', (gridx, y), self.radius
            cv.Circle(
                self.Grid, (gridx, y),
                self.radius,
                cv.Scalar(0x00, 0x00, 0x00),
                thickness=-1)
            cv.Circle(self.Grid, (gridx, y), self.radius, cv.Scalar(0xff, 0x00, 0x00))
            if intersections:
                self.Grid_Intersections.append((gridx, y))
    else:
        cv.Line(self.Grid, (x, 0), (x, self.Target.height), cv.Scalar(0xff, 0x00, 0x00),
                1)
        for gridy in self.Grid_Points_y:
            cv.Circle(
                self.Grid, (x, gridy),
                self.radius,
                cv.Scalar(0x00, 0x00, 0x00),
                thickness=-1)
            cv.Circle(self.Grid, (x, gridy), self.radius, cv.Scalar(0xff, 0x00, 0x00))
            if intersections:
                self.Grid_Intersections.append((x, gridy))
    show_image(self)
    print 'draw_line grid intersections:', len(self.Grid_Intersections)


def read_data(self):
    redraw_grid(self)

    # maximum possible value if all pixels are set
    maxval = (self.radius * self.radius) * 255
    print 'read_data max aperture value:', maxval

    self.Data = []
    for x, y in self.Grid_Intersections:
        value = 0
        # FIXME: misleading
        # This isn't a radius but rather a bounding box
        for xx in range(x - (self.radius / 2), x + (self.radius / 2)):
            for yy in range(y - (self.radius / 2), y + (self.radius / 2)):
                value += get_pixel(self, yy, xx)
        if value > maxval / self.thresh_div:
            cv.Circle(
                self.Grid, (x, y), self.radius, cv.Scalar(0x00, 0xff, 0x00), thickness=2)
            # highlight if we're in edit mode
            if y == self.Edit_y:
                sx = self.Edit_x - (self.Edit_x % self.Cols)
                if self.Grid_Points_x.index(x) >= sx and self.Grid_Points_x.index(
                        x) < sx + self.Cols:
                    cv.Circle(
                        self.Grid, (x, y),
                        self.radius,
                        cv.Scalar(0xff, 0xff, 0xff),
                        thickness=2)
            self.Data.append('1')
        else:
            self.Data.append('0')
    self.data_read = True


def show_data(self):
    if not self.data_read:
        return

    cv.Set(self.Hex, cv.Scalar(0, 0, 0))
    print
    dat = get_all_data(self)
    for row in range(self.Grid_Entries_y):
        out = ''
        outbin = ''
        for column in range(self.Grid_Entries_x / self.Cols):
            thisbyte = ord(dat[column * self.Grid_Entries_y + row])
            hexbyte = '%02X ' % thisbyte
            out += hexbyte
            outbin += to_bin(thisbyte) + ' '
            if self.display_binary:
                disp_data = to_bin(thisbyte)
            else:
                disp_data = hexbyte
            if self.display_data:
                if self.Search_HEX and self.Search_HEX.count(thisbyte):
                    cv.PutText(self.Hex, disp_data,
                               (self.Grid_Points_x[column * self.Cols],
                                self.Grid_Points_y[row] + self.radius / 2 + 1), self.Font,
                               cv.Scalar(0x00, 0xff, 0xff))
                else:
                    cv.PutText(self.Hex, disp_data,
                               (self.Grid_Points_x[column * self.Cols],
                                self.Grid_Points_y[row] + self.radius / 2 + 1), self.Font,
                               cv.Scalar(0xff, 0xff, 0xff))
        print outbin
        print
        print out
    print


def get_all_data(self):
    out = ''
    for column in range(self.Grid_Entries_x / self.Cols):
        for row in range(self.Grid_Entries_y):
            thischunk = ''
            for x in range(self.Cols):
                thisbit = self.Data[x * self.Grid_Entries_y + row +
                               column * self.Cols * self.Grid_Entries_y]
                if self.Inverted:
                    if thisbit == '0':
                        thisbit = '1'
                    else:
                        thisbit = '0'
                thischunk += thisbit
            for x in range(self.Cols / 8):
                thisbyte = thischunk[x * 8:x * 8 + 8]
                # reverse self.Cols if we want LSB
                if self.LSB_Mode:
                    thisbyte = thisbyte[::-1]
                out += chr(int(thisbyte, 2))
    return out


# call with exact values for intersection
def get_data(self, x, y):
    return self.Data[self.Grid_Intersections.index((x, y))]

def toggle_data(self, x, y):
    if self.Data[self.Grid_Intersections.index((x, y))] == '0':
        self.Data[self.Grid_Intersections.index((x, y))] = '1'
    else:
        self.Data[self.Grid_Intersections.index((x, y))] = '0'
    return get_data(self, x, y)

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

def save_grid(self):
    gridout = open(self.basename + '.grid.%d' % self.saves, 'wb')
    pickle.dump(self.Grid_Intersections, gridout)
    print 'grid saved to %s' % (self.basename + '.grid.%d' % self.saves)

# self.Data packed into column based bytes
def save_dat(self):
    out = get_all_data(self)
    columns = self.Grid_Entries_x / self.Cols
    chunk = len(out) / columns
    for x in range(columns):
        outfile = open(self.basename + '.dat%d.set%d' % (x, self.saves), 'wb')
        outfile.write(out[x * chunk:x * chunk + chunk])
        print '%d bytes written to %s' % (chunk,
                                          self.basename + '.dat%d.set%d' %
                                          (x, self.saves))
        outfile.close()

# FIXME: want an as shown XY grid
def save_txt(self):
    with open(self.basename + '.txt%d' % self.saves, 'w') as outfile: 
        pass

def cmd_save(self):
    print 'saving...'

    save_grid(self)

    if not self.data_read:
        print 'No bits to save'
    else:
        save_dat(self)
        save_txt(self)

    self.saves += 1

def cmd_help():
    print 'a/A  decrease/increase radius of read aperture'
    print 'b    blank image (to view template)'
    print 'd/D  decrease/increase dilation'
    print 'e/E  decrease/increase erosion'
    print 'f/F  decrease font size'
    print 'g    toggle grid display'
    print 'h    print help'
    print 'H    toggle binary / hex data display'
    print 'i    toggle invert data 0/1'
    print 'l    toggle LSB data order (default MSB)'
    print 'm/M  decrease/increase bit threshold divisor'
    print 'o   toggle original image display'
    print 'p   toggle peephole view'
    print 'q   quit'
    print 'r   read cols (end enter bit/grid editing mode)'
    print 'R   reset cols (and exit bit/grid editing mode)'
    print 's   show data values (HEX)'
    print 'S   save data and grid'
    print 't   apply threshold filter'
    print '-/+ decrease/increase threshold filter minimum'
    print '/   search for HEX (highlight when HEX shown)'
    print '?   print help'
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

def do_loop(self):
    # image processing
    if self.dilate:
        cv.self.dilate(self.Target, self.Target, iterations=self.dilate)
        self.dilate = 0
    if self.erode:
        cv.self.erode(self.Target, self.Target, iterations=self.erode)
        self.erode = 0
    if self.Threshold:
        cv.Threshold(self.Img, self.Target, self.thresh_min, 0xff, cv.CV_THRESH_BINARY)
        cv.And(self.Target, self.Mask, self.Target)

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

    if k == 65288 and self.Edit_x >= 0:
        # BS
        print 'deleting column'
        self.Grid_Points_x.remove(self.Grid_Points_x[self.Edit_x])
        self.Edit_x = -1
        self.Grid_Entries_x -= 1
        read_data(self)
    elif k == 65362 and self.Edit_y >= 0:
        # up arrow
        print 'editing line', self.Edit_y
        self.Grid_Points_y[self.Grid_Points_y.index(self.Edit_y)] -= 1
        self.Edit_y -= 1
        read_data(self)
    elif k == 65364 and self.Edit_y >= 0:
        # down arrow
        print 'editing line', self.Edit_y
        self.Grid_Points_y[self.Grid_Points_y.index(self.Edit_y)] += 1
        self.Edit_y += 1
        read_data(self)
    elif k == 65363 and self.Edit_x >= 0:
        # right arrow - edit entrie column group
        print 'editing column', self.Edit_x
        sx = self.Edit_x - (self.Edit_x % self.Cols)
        for x in range(sx, sx + self.Cols):
            self.Grid_Points_x[x] += 1
        read_data(self)
    elif k == 65432 and self.Edit_x >= 0:
        # right arrow on numpad - edit single column
        print 'editing column', self.Edit_x
        self.Grid_Points_x[self.Edit_x] += 1
        read_data(self)
    elif k == 65361 and self.Edit_x >= 0:
        # left arrow
        print 'editing column', self.Edit_x
        sx = self.Edit_x - (self.Edit_x % self.Cols)
        for x in range(sx, sx + self.Cols):
            self.Grid_Points_x[x] -= 1
        read_data(self)
    elif k == 65430 and self.Edit_x >= 0:
        # left arrow on numpad - edit single column
        print 'editing column', self.Edit_x
        self.Grid_Points_x[self.Edit_x] -= 1
        read_data(self)
    elif (k == 65439 or k == 65535) and self.Edit_y >= 0:
        # delete
        print 'deleting row', self.Edit_y
        self.Grid_Points_y.remove(self.Edit_y)
        self.Grid_Entries_y -= 1
        self.Edit_y = -1
        read_data(self)
    elif k == chr(10):
        # enter
        self.Edit_x = -1
        self.Edit_y = -1
        print 'done editing'
        read_data(self)
    elif k == 'a':
        if self.radius:
            self.radius -= 1
            read_data(self)
        print 'Radius:', self.radius
    elif k == 'A':
        self.radius += 1
        read_data(self)
        print 'Radius:', self.radius
    elif k == 'b':
        self.display_blank_image = not self.display_blank_image
    elif k == 'd':
        self.dilate = max(self.dilate - 1, 0)
    elif k == 'D':
        self.dilate += 1
    elif k == 'e':
        self.erode = max(self.erase - 1, 0)
    elif k == 'E':
        self.erode += 1
    elif k == 'f':
        if self.FontSize > 0.1:
            self.FontSize -= 0.1
            self.Font = cv.InitFont(
                cv.CV_FONT_HERSHEY_SIMPLEX,
                hscale=self.FontSize,
                vscale=1.0,
                shear=0,
                thickness=1,
                lineType=8)
        print 'fontsize:', self.FontSize
    elif k == 'F':
        self.FontSize += 0.1
        self.Font = cv.InitFont(
            cv.CV_FONT_HERSHEY_SIMPLEX,
            hscale=self.FontSize,
            vscale=1.0,
            shear=0,
            thickness=1,
            lineType=8)
        print 'fontsize:', self.FontSize
    elif k == 'g':
        self.display_grid = not self.display_grid
        print 'display grid:', self.display_grid
    elif k == 'h' or k == '?':
        cmd_help()
    elif k == 'H':
        self.display_binary = not self.display_binary
        print 'display binary:', self.display_binary
    elif k == 'i':
        self.Inverted = not self.Inverted
        print 'Inverted:', self.Inverted
    elif k == 'l':
        self.LSB_Mode = not self.LSB_Mode
        print 'LSB self.Data mode:', self.LSB_Mode
    elif k == 'm':
        self.thresh_div -= 1
        print 'thresh_div:', self.thresh_div
        if self.data_read:
            read_data(self)
    elif k == 'M':
        self.thresh_div += 1
        print 'thresh_div:', self.thresh_div
        if self.data_read:
            read_data(self)
    elif k == 'o':
        self.display_original = not self.display_original
        print 'display original:', self.display_original
    elif k == 'p':
        self.display_peephole = not self.display_peephole
        print 'display peephole:', self.display_peephole
    elif k == 'r':
        print 'reading %d points...' % len(self.Grid_Intersections)
        read_data(self)
    elif k == 'R':
        redraw_grid(self)
        self.data_read = False
    elif k == 's':
        self.display_data = not self.display_data
        print 'show data:', self.display_data
    elif k == 'S':
        cmd_save(self)
    elif k == 'q':
        print "Exiting on q"
        self.running = False
    elif k == 't':
        self.Threshold = True
        print 'Threshold:', self.Threshold
    elif k == '-':
        self.thresh_min = max(self.thresh_min - 1, 0x01)
        print 'Threshold filter %02x' % self.thresh_min
        if self.data_read:
            read_data(self)
    elif k == '+':
        self.thresh_min = min(self.thresh_min + 1, 0xFF)
        print 'Threshold filter %02x' % self.thresh_min
        if self.data_read:
            read_data(self)
    elif k == '/':
        cmd_find(self, k)

def run(image_fn, cols_per_group, rows_per_group,
        grid_file=None, radius=None):
    self = Rompar()
    self.Cols = cols_per_group
    self.Rows = rows_per_group
    if radius:
        self.default_radius = radius
        self.radius = radius

    #self.Img= cv.LoadImage(image_fn, iscolor=cv.CV_LOAD_IMAGE_GRAYSCALE)
    #self.Img= cv.LoadImage(image_fn, iscolor=cv.CV_LOAD_IMAGE_COLOR)
    self.Img = cv.LoadImage(image_fn)
    print 'Image is %dx%d' % (self.Img.width, self.Img.height)

    self.basename = image_fn[:image_fn.find('.')]

    # image buffers
    self.Target = cv.CreateImage(cv.GetSize(self.Img), cv.IPL_DEPTH_8U, 3)
    self.Grid = cv.CreateImage(cv.GetSize(self.Img), cv.IPL_DEPTH_8U, 3)
    self.Mask = cv.CreateImage(cv.GetSize(self.Img), cv.IPL_DEPTH_8U, 3)
    self.Peephole = cv.CreateImage(cv.GetSize(self.Img), cv.IPL_DEPTH_8U, 3)
    cv.Set(self.Mask, cv.Scalar(0x00, 0x00, 0xff))
    self.Display = cv.CreateImage(cv.GetSize(self.Img), cv.IPL_DEPTH_8U, 3)
    cv.Set(self.Grid, cv.Scalar(0, 0, 0))
    self.Blank = cv.CreateImage(cv.GetSize(self.Img), cv.IPL_DEPTH_8U, 3)
    cv.Set(self.Blank, cv.Scalar(0, 0, 0))
    self.Hex = cv.CreateImage(cv.GetSize(self.Img), cv.IPL_DEPTH_8U, 3)
    cv.Set(self.Hex, cv.Scalar(0, 0, 0))

    self.FontSize = 1.0
    self.Font = cv.InitFont(
        cv.CV_FONT_HERSHEY_SIMPLEX,
        hscale=self.FontSize,
        vscale=1.0,
        shear=0,
        thickness=1,
        lineType=8)

    if grid_file:
        gridfile = open(grid_file, 'rb')
        self.Grid_Intersections = pickle.load(gridfile)
        gridfile.close()
        for x, y in self.Grid_Intersections:
            try:
                self.Grid_Points_x.index(x)
            except:
                self.Grid_Points_x.append(x)
                self.Grid_Entries_x += 1
            try:
                self.Grid_Points_y.index(y)
            except:
                self.Grid_Points_y.append(y)
                self.Grid_Entries_y += 1
        self.Step_x = 0.0
        if len(self.Grid_Points_x) > 1:
            self.Step_x = self.Grid_Points_x[1] - self.Grid_Points_x[0]
        self.Step_y = 0.0
        if len(self.Grid_Points_y) > 1:
            self.Step_y = self.Grid_Points_y[1] - self.Grid_Points_y[0]
        if not radius:
            if self.Step_x:
                self.radius = self.Step_x / 3
            else:
                self.radius = self.Step_y / 3
        redraw_grid(self)

    self.title = "rompar %s" % image_fn
    cv.NamedWindow(self.title, 1)
    cv.SetMouseCallback(self.title, on_mouse, self)

    cmd_help()
    cmd_help2()

    # main loop
    self.Target = cv.CloneImage(self.Img)
    while self.running:
        do_loop(self)
    
    print 'Exiting'

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Extract mask ROM image')
    parser.add_argument('--radius', type=int, help='Use given radius')
    parser.add_argument('image', help='Input image')
    parser.add_argument('cols_per_group', type=int, help='')
    parser.add_argument('rows_per_group', type=int, help='')
    parser.add_argument('grid_file', nargs='?', help='Load saved grid file')
    args = parser.parse_args()

    run(args.image, args.cols_per_group, args.rows_per_group, grid_file=args.grid_file, radius=args.radius)
