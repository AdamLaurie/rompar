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
