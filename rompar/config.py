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

def print_config(self):
    print 'Display'
    print '  Grid      %s' % self.config.img_display_grid
    print '  Original  %s' % self.config.img_display_original
    print '  Peephole  %s' % self.config.img_display_peephole
    print '  Data      %s' % self.config.img_display_data
    print '    As binary %s' % self.config.img_display_binary
    print 'Pixel processing'
    print '  Bit threshold divisor   %s' % self.config.bit_thresh_div
    print '  Pixel threshold minimum %s (0x%02X)' % (self.config.pix_thresh_min, self.config.pix_thresh_min)
    print '  Dilate    %s' % self.config.dilate
    print '  Erode     %s' % self.config.erode
    print '  Radius    %s' % self.config.radius
    print '  Threshold %s' % self.config.threshold
    print '  Step'
    print '    X       % 5.1f' % self.step_x
    print '    X       % 5.1f' % self.step_y
    print 'Bit state'
    print '  Data read %d' % self.data_read
    print '  Bits per group'
    print '    X       %d cols' % self.group_cols
    print '    Y       %d rows' % self.group_rows
    print '  Bit points total'
    print '    X       %d cols' % len(self.grid_points_x)
    print '    Y       %d rows' % len(self.grid_points_y)
    print '  Inverted  %d' % self.inverted
    print '  Intersections %d' % len(self.grid_intersections)
    print '  Viewport'
    print '    X       %d' % self.config.view.x
    print '    Y       %d' % self.config.view.y
    print '    W       %d' % self.config.view.w
    print '    H       %d' % self.config.view.h
    print '    PanX    %d' % self.config.view.incx
    print '    PanY    %d' % self.config.view.incy

