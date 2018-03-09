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

import subprocess

import sys
import cv2.cv as cv
import traceback

def screen_wh():
    cmd = ['xrandr']
    cmd2 = ['grep', '*']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    p2 = subprocess.Popen(cmd2, stdin=p.stdout, stdout=subprocess.PIPE)
    p.stdout.close()

    resolution_string, _junk = p2.communicate()
    resolution = resolution_string.split()[0]
    width, height = resolution.split('x')
    return int(width), int(height)

class View(object):
    def __init__(self):
        # Display objects
        # Crop / viewport
        self.x = 0
        self.y = 0
        screenw, screenh = screen_wh()
        # Displayed coordinates
        self.w = screenw - 100
        self.h = screenh - 100
        # Step increment
        self.incx = screenw // 3
        self.incy = screenh // 3

class Config(object):
    def __init__(self):
        # Display options
        # Overlay bit position grid
        self.img_display_grid = True
        # Show source image (ie without thresholding)
        self.img_display_original = False
        # Remove image entirely, showing just decoded bits
        self.img_display_blank_image = False
        # Show image only in bit ROI
        self.img_display_peephole = False
        # Overlay hex data on image
        self.img_display_data = False
        # Overlay binary data on image
        self.img_display_binary = False
        # Bit is 1 if sum of pixels in area > (max possible value / thresh_div)
        # ie 10 => set if average value at least 1/10 max brightness
        # Feel this is sort of a weird way to do this
        self.bit_thresh_div = 10
        # Pixel value >= to consider occupied
        self.pix_thresh_min = 0xae

        # Image processing options
        self.dilate = 0
        self.erode = 0
        # Bit image radius as displayed on grid
        # Actual detection uses square around circle
        self.radius = 0
        # User supplied radius to be used in lieu of auto calculated
        self.default_radius = None
        self.threshold = True

        self.LSB_Mode = False

        self.font_size = None

        self.view = View()

        self.save_dat = False
