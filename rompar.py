#! /usr/bin/env python

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

from rompar.config import Rompar
from rompar.cmd import run

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Extract mask ROM image')
    parser.add_argument('--radius', type=int, help='Use given radius for display, bounded square for detection')
    parser.add_argument('--bit-thresh-div', type=str, help='Bit set area threshold divisor')
    # Only care about min
    parser.add_argument('--pix-thresh', type=str, help='Pixel is set threshold minimum')
    parser.add_argument('--dilate', type=str, help='Dilation')
    parser.add_argument('--erode', type=str, help='Erosion')
    parser.add_argument('--debug', action='store_true', help='')
    parser.add_argument('image', help='Input image')
    parser.add_argument('cols_per_group', type=int, help='')
    parser.add_argument('rows_per_group', type=int, help='')
    parser.add_argument('grid_file', nargs='?', help='Load saved grid file')
    args = parser.parse_args()

    self = Rompar()
    self.debug = args.debug
    self.group_cols = args.cols_per_group
    self.group_rows = args.rows_per_group
    if args.radius:
        self.config.default_radius = args.radius
        self.config.radius = args.radius
    if args.bit_thresh_div:
        self.config.bit_thresh_div = int(args.bit_thresh_div, 0)
    if args.pix_thresh:
        self.config.pix_thresh_min = int(args.pix_thresh, 0)
    if args.dilate:
        self.config.dilate = int(args.dilate, 0)
    if args.erode:
        self.config.erode = int(args.erode, 0)

    run(self, args.image, grid_file=args.grid_file)

if __name__ == "__main__":
    main()
