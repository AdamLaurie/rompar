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

from data import *
#from cmd import *
import sys

K_RIGHT = 65363
K_DOWN = 65362
K_LEFT = 65361
K_UP = 65364

#self = None

def on_mouse_left(img_x, img_y, flags, param):
    self = param

    # Edit data
    if self.data_read:
        # find nearest intersection and toggle its value
        for x in self.grid_points_x:
            if img_x >= x - self.config.radius / 2 and img_x <= x + self.config.radius / 2:
                for y in self.grid_points_y:
                    if img_y >= y - self.config.radius / 2 and img_y <= y + self.config.radius / 2:
                        value = toggle_data(self, x, y)
                        #print self.img_target[x, y]
                        #print 'value', value
                        if value == '0':
                            cv.Circle(
                                self.img_grid, (x, y),
                                self.config.radius,
                                cv.Scalar(0xff, 0x00, 0x00),
                                thickness=2)
                        else:
                            cv.Circle(
                                self.img_grid, (x, y),
                                self.config.radius,
                                cv.Scalar(0x00, 0xff, 0x00),
                                thickness=2)

                        show_image(self)
    # Edit grid
    else:
        #if not Target[img_y, img_x]:
        if flags != cv.CV_EVENT_FLAG_SHIFTKEY and not get_pixel(self,
                img_y, img_x):
            print 'autocenter: miss!'
            return

        if img_x in self.grid_points_x:
            return
        # only draw a single line if this is the first one
        if len(self.grid_points_x) == 0 or self.group_cols == 1:
            if flags != cv.CV_EVENT_FLAG_SHIFTKEY:
                img_x, img_y = auto_center(self, img_x, img_y)

            # don't try to auto-center if shift key pressed
            draw_line(self, img_x, img_y, 'V', False)
            self.grid_points_x.append(img_x)
            if self.group_rows == 1:
                draw_line(self, img_x, img_y, 'V', True)
        else:
            # set up auto draw
            if len(self.grid_points_x) == 1:
                # use a float to reduce rounding errors
                self.step_x = float(img_x - self.grid_points_x[0]) / (self.group_cols - 1)
                # reset stored self.data as main loop will add all entries
                img_x = self.grid_points_x[0]
                self.grid_points_x = []
                update_radius(self)
            # draw a full set of self.group_cols
            for x in range(self.group_cols):
                draw_x = int(img_x + x * self.step_x)
                self.grid_points_x.append(draw_x)
                draw_line(self, draw_x, img_y, 'V', True)

def on_mouse_right(img_x, img_y, flags, param):
    self = param

    # Edit data
    if self.data_read:
        # find row and select for editing
        for x in self.grid_points_x:
            for y in self.grid_points_y:
                if img_y >= y - self.config.radius / 2 and img_y <= y + self.config.radius / 2:
                    #print 'value', get_data(x,y)
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
                    read_data(self)
                    show_image(self)
                    return
    # Edit grid
    else:
        if flags != cv.CV_EVENT_FLAG_SHIFTKEY and not get_pixel(self,
                img_y, img_x):
            print 'autocenter: miss!'
            return
        if img_y in self.grid_points_y:
            return
        # only draw a single line if this is the first one
        if len(self.grid_points_y) == 0 or self.group_rows == 1:
            if flags != cv.CV_EVENT_FLAG_SHIFTKEY:
                img_x, img_y = auto_center(self, img_x, img_y)

            draw_line(self, img_x, img_y, 'H', False)
            self.grid_points_y.append(img_y)
            if self.group_rows == 1:
                draw_line(self, img_x, img_y, 'H', True)
        else:
            # set up auto draw
            if len(self.grid_points_y) == 1:
                # use a float to reduce rounding errors
                self.step_y = float(img_y - self.grid_points_y[0]) / (self.group_rows - 1)
                # reset stored self.data as main loop will add all entries
                img_y = self.grid_points_y[0]
                self.grid_points_y = []
                update_radius(self)
            # draw a full set of self.group_rows
            for y in range(self.group_rows):
                draw_y = int(img_y + y * self.step_y)
                # only draw up to the edge of the image
                if draw_y > self.img_original.height:
                    break
                self.grid_points_y.append(draw_y)
                draw_line(self, img_x, draw_y, 'H', True)


# mouse events
def on_mouse(event, mouse_x, mouse_y, flags, param):
    self = param

    img_x = mouse_x + self.config.view.x
    img_y = mouse_y + self.config.view.y

    # draw vertical grid lines
    if event == cv.CV_EVENT_LBUTTONDOWN:
        on_mouse_left(img_x, img_y, flags, param)
    # draw horizontal grid lines
    elif event == cv.CV_EVENT_RBUTTONDOWN:
        on_mouse_right(img_x, img_y, flags, param)


def show_image(self):
    if self.config.img_display_original:
        self.img_display = cv.CloneImage(self.img_original)
    else:
        self.img_display = cv.CloneImage(self.img_target)

    if self.config.img_display_blank_image:
        self.img_display = cv.CloneImage(self.img_blank)

    if self.config.img_display_grid:
        cv.Or(self.img_display, self.img_grid, self.img_display)

    if self.config.img_display_peephole:
        cv.And(self.img_display, self.img_peephole, self.img_display)

    if self.config.img_display_data:
        show_data(self)
        cv.Or(self.img_display, self.img_hex, self.img_display)

    self.img_display_viewport = self.img_display[self.config.view.y:self.config.view.y+self.config.view.h,
                                                 self.config.view.x:self.config.view.x+self.config.view.w]
    cv.ShowImage(self.title, self.img_display_viewport)

def auto_center(self, x, y):
    '''
    Auto center image global x/y coordinate on contiguous pixel x/y runs
    '''
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
    print 'draw_line', x, y, direction, intersections, len(self.grid_points_x), len(self.grid_points_y)

    if direction == 'H':
        print 'Draw H line', (0, y), (self.img_target.width, y)
        cv.Line(self.img_grid, (0, y), (self.img_target.width, y), cv.Scalar(0xff, 0x00, 0x00),
                1)
        for gridx in self.grid_points_x:
            print '*****self.grid_points_x circle', (gridx, y), self.config.radius
            cv.Circle(
                self.img_grid, (gridx, y),
                self.config.radius,
                cv.Scalar(0x00, 0x00, 0x00),
                thickness=-1)
            cv.Circle(self.img_grid, (gridx, y), self.config.radius, cv.Scalar(0xff, 0x00, 0x00))
            if intersections:
                self.grid_intersections.append((gridx, y))
    else:
        cv.Line(self.img_grid, (x, 0), (x, self.img_target.height), cv.Scalar(0xff, 0x00, 0x00),
                1)
        for gridy in self.grid_points_y:
            cv.Circle(
                self.img_grid, (x, gridy),
                self.config.radius,
                cv.Scalar(0x00, 0x00, 0x00),
                thickness=-1)
            cv.Circle(self.img_grid, (x, gridy), self.config.radius, cv.Scalar(0xff, 0x00, 0x00))
            if intersections:
                self.grid_intersections.append((x, gridy))
    show_image(self)
    print 'draw_line grid intersections:', len(self.grid_intersections)

def show_data(self):
    if not self.data_read:
        return

    cv.Set(self.img_hex, cv.Scalar(0, 0, 0))
    print
    dat = get_all_data(self)
    for row in range(len(self.grid_points_y)):
        out = ''
        outbin = ''
        for column in range(len(self.grid_points_x) / self.group_cols):
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
                    cv.PutText(self.img_hex, disp_data,
                               (self.grid_points_x[column * self.group_cols],
                                self.grid_points_y[row] + self.config.radius / 2 + 1), self.font,
                               cv.Scalar(0x00, 0xff, 0xff))
                else:
                    cv.PutText(self.img_hex, disp_data,
                               (self.grid_points_x[column * self.group_cols],
                                self.grid_points_y[row] + self.config.radius / 2 + 1), self.font,
                               cv.Scalar(0xff, 0xff, 0xff))
        #print outbin
        #print
        #print out
    print

def pan(self, x, y):
    #imgw = self.img_target.cols
    #imgh = self.img_target.rows
    #imgw, imgh, _channels = self.img_target.shape
    imgw, imgh = cv.GetSize(self.img_target)
    self.config.view.x = min(max(0, self.config.view.x + x), imgw - self.config.view.w)
    self.config.view.y = min(max(0, self.config.view.y + y), imgh - self.config.view.h)

