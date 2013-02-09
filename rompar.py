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

# globals
Display_Grid= True
Data_Read= False
Display_Original= False
Blank_Image= False
Display_Peephole= False
Threshold= True
LSB_Mode= False
Display_Data= False
Display_Binary= False
Search_HEX= None
ReadVal= 10
Dilate= 0
Erode= 0
Threshold_Min= 0xae
Saveset= 0
Grid_Points_x= []
Grid_Points_y= []
Grid_Entries_x= 0
Grid_Entries_y= 0
Grid_Intersections= []
Grid_Start_x= 1
Grid_Start_y= 1
Edit_x= -1
Edit_y= -1
Step_x= 0
Step_y= 0
Radius= 0
Data= []
Inverted= False
Bits= 0
Rows= 0
Filters= {
	'Blue':(0xff,0x00,0x00),
	'Green':(0x00,0xff,0x00),
	'Red':(0x00,0x00,0xff),
	}

if len(sys.argv) > 1:
	#Img= cv.LoadImage(sys.argv[1], iscolor=cv.CV_LOAD_IMAGE_GRAYSCALE)
	#Img= cv.LoadImage(sys.argv[1], iscolor=cv.CV_LOAD_IMAGE_COLOR)
	Img= cv.LoadImage(sys.argv[1])
	print 'Image is %dx%d' % (Img.width, Img.height)
else:
	print 'usage: %s <IMAGE> <BITS PER GROUP> <ROWS PER GROUP> [GRID FILE]' % sys.argv[0]
	print
	print "  hit 'h' when image has focus to print help text"
	print
	exit()

# image buffers
Target = cv.CreateImage(cv.GetSize(Img), cv.IPL_DEPTH_8U, 3)
Grid= cv.CreateImage(cv.GetSize(Img), cv.IPL_DEPTH_8U, 3)
Mask= cv.CreateImage(cv.GetSize(Img), cv.IPL_DEPTH_8U, 3)
Peephole= cv.CreateImage(cv.GetSize(Img), cv.IPL_DEPTH_8U, 3)
cv.Set(Mask, cv.Scalar(0x00,0x00,0xff))
Display= cv.CreateImage(cv.GetSize(Img), cv.IPL_DEPTH_8U, 3)
cv.Set(Grid, cv.Scalar(0,0,0))
Blank= cv.CreateImage(cv.GetSize(Img), cv.IPL_DEPTH_8U, 3)
cv.Set(Blank, cv.Scalar(0,0,0))
Hex= cv.CreateImage(cv.GetSize(Img), cv.IPL_DEPTH_8U, 3)
cv.Set(Hex, cv.Scalar(0,0,0))

FontSize= 1.0
Font= cv.InitFont(cv.CV_FONT_HERSHEY_SIMPLEX, hscale= FontSize, vscale= 1.0, shear=0, thickness=1, lineType=8)

def get_pixel(x, y):
	return Target[x,y][0]+Target[x,y][1]+Target[x,y][2]

# create binary printable string
def to_bin(x):
	return ''.join(x & (1 << i) and '1' or '0' for i in range(7,-1,-1)) 

def redraw_grid():
	global Grid
	global Peephole
	global Radius
	global Grid_Points_x
	global Grid_Points_y
	global Grid_Intersections

	cv.Set(Grid, cv.Scalar(0,0,0))
	cv.Set(Peephole, cv.Scalar(0,0,0))
	Grid_Intersections= []
	Grid_Points_x.sort()
	Grid_Points_y.sort()

	for x in Grid_Points_x:
		cv.Line(Grid, (x, 0), (x, Target.height), cv.Scalar(0xff,0x00,0x00),1)
		for y in Grid_Points_y:
			Grid_Intersections.append((x,y))
	Grid_Intersections.sort()
	for y in Grid_Points_y:
		cv.Line(Grid, (0, y), (Target.width, y), cv.Scalar(0xff,0x00,0x00),1)
	for x,y in Grid_Intersections:
		cv.Circle(Grid, (x,y), Radius, cv.Scalar(0x00,0x00,0x00), thickness= -1)
		cv.Circle(Grid, (x,y), Radius, cv.Scalar(0xff,0x00,0x00), thickness= 1)
		cv.Circle(Peephole, (x,y), Radius + 1, cv.Scalar(0xff,0xff,0xff), thickness= -1)
	
basename= sys.argv[1][:sys.argv[1].find('.')]
Bits= int(sys.argv[2])
Rows= int(sys.argv[3])

if len(sys.argv) == 5:
	gridfile= open(sys.argv[4],'rb')
	Grid_Intersections= pickle.load(gridfile)
	gridfile.close()
	for x,y in Grid_Intersections:
		try:
			Grid_Points_x.index(x)
		except:
			Grid_Points_x.append(x)
			Grid_Entries_x += 1
		try:
			Grid_Points_y.index(y)
		except:
			Grid_Points_y.append(y)
			Grid_Entries_y += 1
	Step_x= Grid_Points_x[1] - Grid_Points_x[0]
	Step_y= Grid_Points_y[1] - Grid_Points_y[0]
	Radius= Step_x / 3
	redraw_grid()

cv.NamedWindow("rompar %s" % sys.argv[1], 1)


# mouse events
def on_mouse(event, mouse_x, mouse_y, flags, param):
	global Target
	global Bits
	global Grid_Points_x
	global Grid_Points_y
	global Grid_Entries_x
	global Grid_Entries_y
	global Grid_Start_x
	global Grid_Start_y
	global Step_x
	global Step_y
	global Radius
	global Data_Read
	global Grid
	global Edit_y
	global Edit_x

	# draw vertical grid lines
	if event == cv.CV_EVENT_LBUTTONDOWN:
		# are we editing data or grid?
		if Data_Read:
			# find nearest intersection and toggle its value
			for x in Grid_Points_x:
				if mouse_x >= x - Radius / 2 and mouse_x <= x + Radius / 2:
					for y in Grid_Points_y:
						if mouse_y >= y - Radius / 2 and mouse_y <= y + Radius / 2:
							value= toggle_data(x,y)
							print Target[x,y]
							#print 'value', value
							if value == '0':
								cv.Circle(Grid, (x,y), Radius, cv.Scalar(0xff,0x00,0x00), thickness= 2)
							else:
								cv.Circle(Grid, (x,y), Radius, cv.Scalar(0x00,0xff,0x00), thickness= 2)
						
							show_image()
			return

		#if not Target[mouse_y, mouse_x]:
		if not flags == cv.CV_EVENT_FLAG_SHIFTKEY and not get_pixel(mouse_y, mouse_x):
			print 'miss!'
			return

		# only draw a single line if this is the first one
		if Grid_Entries_x == 0:
			Grid_Entries_x += 1
			# don't try to auto-center if shift key pressed
			if flags == cv.CV_EVENT_FLAG_SHIFTKEY:
				mouse_x, mouse_y= draw_line(mouse_x, mouse_y, False, 'V', False)
			else:
				mouse_x, mouse_y= draw_line(mouse_x, mouse_y, True, 'V', False)
			Grid_Points_x.append(mouse_x)
			return
		# set up auto draw
		if Grid_Entries_x == 1:
			# use a float to reduce rounding errors
			Step_x= float (mouse_x - Grid_Points_x[0]) / (Bits - 1)
			Radius= int(Step_x / 3)
			# reset stored data as main loop will add all entries
			mouse_x= Grid_Points_x[0]
			Grid_Points_x= []
			Grid_Entries_x= 0
		# draw a full set of bits
		for x in range(Bits):
			Grid_Entries_x += 1
			draw_x=  int(mouse_x + x * Step_x)
			Grid_Points_x.append(draw_x)
			draw_line(draw_x, mouse_y, False, 'V', True)

	# draw horizontal grid lines	
	if event == cv.CV_EVENT_RBUTTONDOWN:
		# are we editing data or grid?
		if Data_Read:
			# find row and select for editing
			for x in Grid_Points_x:
				for y in Grid_Points_y:
					if mouse_y >= y - Radius / 2 and mouse_y <= y + Radius / 2:
						#print 'value', get_data(x,y)
						# select the whole row
						xcount= 0
						for x in Grid_Points_x:
							if mouse_x >= x - Radius / 2 and mouse_x <= x + Radius / 2:
								Edit_x= xcount
								break
							else:
								xcount += 1
						# highlight the bit group we're in
						sx= Edit_x - (Edit_x % Bits)
						Edit_y= y
						read_data()
						show_image()
						return
			return

		if not flags == cv.CV_EVENT_FLAG_SHIFTKEY and not get_pixel(mouse_y, mouse_x):
			print 'miss!'
			return
		# only draw a single line if this is the first one
		if Grid_Entries_y == 0:
			Grid_Entries_y += 1
			if flags == cv.CV_EVENT_FLAG_SHIFTKEY:
				mouse_x, mouse_y= draw_line(mouse_x, mouse_y, False, 'H', False)
			else:
				mouse_x, mouse_y= draw_line(mouse_x, mouse_y, True, 'H', False)
			Grid_Points_y.append(mouse_y)
			return
		# set up auto draw
		if Grid_Entries_y == 1:
			# use a float to reduce rounding errors
			Step_y= float (mouse_y - Grid_Points_y[0]) / (Rows - 1)
			# reset stored data as main loop will add all entries
			mouse_y= Grid_Points_y[0]
			Grid_Points_y= []
			Grid_Entries_y= 0
		# draw a full set of rows
		for x in range(Rows):
			draw_y=  int(mouse_y + x * Step_y)
			# only draw up to the edge of the image
			if draw_y > Img.height:
				break
			Grid_Entries_y += 1
			Grid_Points_y.append(draw_y)
			draw_line(mouse_x, draw_y, False, 'H', True)

cv.SetMouseCallback("rompar %s" % sys.argv[1], on_mouse, None) 

def show_image():
	global Target
	global Grid
	global Display_Grid
	global Display_Original
	global Img
	global Display
	global Display_Data

	if Display_Original:
		Display= cv.CloneImage(Img)	
	else:
		Display= cv.CloneImage(Target)

	if Blank_Image:
		Display= cv.CloneImage(Blank)	

	if Display_Grid:
		cv.Or(Display, Grid, Display)

	if Display_Peephole:
		cv.And(Display, Peephole, Display)

	if Display_Data:
		show_data()
		cv.Or(Display, Hex, Display)

	cv.ShowImage("rompar %s" % sys.argv[1], Display)

# draw grid
def draw_line(x, y, auto, direction, intersections):
	global Grid
	global Grid_Points_x
	global Grid_Points_y
	global Grid_Intersections

	# auto-center
	if auto:
		x_min= x
		while get_pixel(y, x_min) != 0.0:
			x_min -= 1
		x_max= x
		while get_pixel(y, x_max) != 0.0:
			x_max += 1
		x= x_min + ((x_max - x_min) / 2)
		y_min= y
		while get_pixel(y_min, x) != 0.0:
			y_min -= 1
		y_max= y
		while get_pixel(y_max, x) != 0.0:
			y_max += 1
		y= y_min + ((y_max - y_min) / 2)

	if direction == 'H':
		cv.Line(Grid, (0, y), (Target.width, y), cv.Scalar(0xff,0x00,0x00),1)
		for gridx in Grid_Points_x:
			cv.Circle(Grid, (gridx,y), Radius, cv.Scalar(0x00,0x00,0x00), thickness= -1)
			cv.Circle(Grid, (gridx,y), Radius, cv.Scalar(0xff,0x00,0x00))
			if intersections:
				Grid_Intersections.append((gridx,y))
	else:
		cv.Line(Grid, (x, 0), (x, Target.height), cv.Scalar(0xff,0x00,0x00),1)
		for gridy in Grid_Points_y:
			cv.Circle(Grid, (x,gridy), Radius, cv.Scalar(0x00,0x00,0x00), thickness= -1)
			cv.Circle(Grid, (x,gridy), Radius, cv.Scalar(0xff,0x00,0x00))
			if intersections:
				Grid_Intersections.append((x,gridy))
	show_image()
	print 'points:', len(Grid_Intersections)
	return x, y

def read_data():
	global Grid_Intersections
	global Grid_Entries_x
	global Grid_Entries_y
	global Radius
	global Target
	global Bits
	global Data_Read
	global Data
	global Inverted

	redraw_grid()

	# maximum possible value if all pixels are set
	maxval= (Radius * Radius) * 255
	print 'max:', maxval

	Data= []
	for x, y in Grid_Intersections:
		value= 0
		for xx in range(x - (Radius / 2), x + (Radius / 2)):
			for yy in range(y - (Radius / 2), y + (Radius / 2)):
				value += get_pixel(yy,xx)
		if value > maxval / ReadVal:
			cv.Circle(Grid, (x,y), Radius, cv.Scalar(0x00,0xff,0x00), thickness= 2)
			# highlight if we're in edit mode
			if y == Edit_y:
				sx= Edit_x - (Edit_x % Bits)
				if Grid_Points_x.index(x) >= sx and Grid_Points_x.index(x) < sx + Bits:
					cv.Circle(Grid, (x,y), Radius, cv.Scalar(0xff,0xff,0xff), thickness= 2)
			Data.append('1')
		else:
			Data.append('0')
	Data_Read= True

def show_data():
	global Hex
	global Display_Data
	global Display_Binary
	global Search_HEX
	global Grid_Points_x
	global Grid_Points_y
	global Font
	global Data_Read
	global Radius

	if not Data_Read:
		return

	cv.Set(Hex, cv.Scalar(0,0,0))
	print
	dat= get_all_data()
	for row in range(Grid_Entries_y):
		out= ''
		outbin= ''
		for column in range(Grid_Entries_x / Bits):
			thisbyte= ord(dat[column * Grid_Entries_y + row])
			hexbyte= '%02X ' % thisbyte
			out += hexbyte
			outbin += to_bin(thisbyte) + ' '
			if Display_Binary:
				dispdata= to_bin(thisbyte)
			else:
				dispdata= hexbyte
			if Display_Data:
				if Search_HEX and Search_HEX.count(thisbyte):
					cv.PutText(Hex, dispdata, (Grid_Points_x[column * Bits], Grid_Points_y[row] + Radius / 2 + 1), Font, cv.Scalar(0x00,0xff,0xff))
				else:
					cv.PutText(Hex, dispdata, (Grid_Points_x[column * Bits], Grid_Points_y[row] + Radius / 2 + 1), Font, cv.Scalar(0xff,0xff,0xff))
		print outbin
		print
		print out
	print

def get_all_data():
	global Data
	global Grid_Intersections
	global Bits
	global Inverted
	global LSB_Mode
	global Grid_Entries_x
	global Grid_Entries_y

	out= ''
	for column in range(Grid_Entries_x / Bits):
		for row in range(Grid_Entries_y):
			thischunk= ''
			for x in range(Bits):
				thisbit= Data[x * Grid_Entries_y + row + column * Bits * Grid_Entries_y]
				if Inverted:
					if thisbit == '0':
						thisbit= '1'
					else:
						thisbit= '0'
				thischunk += thisbit
			for x in range(Bits / 8):
				thisbyte= thischunk[x * 8:x * 8 + 8]
				# reverse bits if we want LSB
				if LSB_Mode:
					thisbyte= thisbyte[::-1]
				out += chr(int(thisbyte,2))
	return out

# call with exact values for intersection
def get_data(x, y):
	global Data
	global Grid_Intersections

	return Data[Grid_Intersections.index((x,y))]

def toggle_data(x, y):
	global Data
	global Grid_Intersections

	if Data[Grid_Intersections.index((x,y))] == '0':
		Data[Grid_Intersections.index((x,y))]= '1'
	else:
		Data[Grid_Intersections.index((x,y))]= '0'
	return get_data(x, y)

# main loop
Target= cv.CloneImage(Img)
while True:
	# image processing
	if Dilate:
		cv.Dilate(Target,Target,iterations= Dilate)
		Dilate= 0
	if Erode:
		cv.Erode(Target,Target,iterations= Erode)
		Erode= 0
	if Threshold:
		cv.Threshold(Img, Target, Threshold_Min, 0xff, cv.CV_THRESH_BINARY)
		cv.And(Target, Mask, Target)
		
	show_image()
	# keystroke processing
	k = cv.WaitKey(0)
	print k
	if k > 66000:
		continue
	if k < 256:
		k= chr(k)
	else:
		if k > 65506 and k != 65535:
			k -= 65506
			k= chr(k - 30)
	if k == 65288 and Edit_x >= 0:
		# BS
		print 'deleting column'
		Grid_Points_x.remove(Grid_Points_x[Edit_x])
		Edit_x= -1
		Grid_Entries_x -= 1
		read_data()
	if k == 65362 and Edit_y >= 0:
		# up arrow
		print 'editing line', Edit_y
		Grid_Points_y[Grid_Points_y.index(Edit_y)] -= 1
		Edit_y -= 1
		read_data()
	if k == 65364 and Edit_y >= 0:
		# down arrow
		print 'editing line', Edit_y
		Grid_Points_y[Grid_Points_y.index(Edit_y)] += 1
		Edit_y += 1
		read_data()
	if k == 65363 and Edit_x >= 0:
		# right arrow - edit entrie column group
		print 'editing column', Edit_x
		sx= Edit_x - (Edit_x % Bits)
		for x in range(sx, sx + Bits):
			Grid_Points_x[x] += 1
		read_data()
	if k == 65432 and Edit_x >= 0:
		# right arrow on numpad - edit single column
		print 'editing column', Edit_x
		Grid_Points_x[Edit_x] += 1
		read_data()
	if k == 65361 and Edit_x >= 0:
		# left arrow
		print 'editing column', Edit_x
		sx= Edit_x - (Edit_x % Bits)
		for x in range(sx, sx + Bits):
			Grid_Points_x[x] -= 1
		read_data()
	if k == 65430 and Edit_x >= 0:
		# left arrow on numpad - edit single column
		print 'editing column', Edit_x
		Grid_Points_x[Edit_x] -= 1
		read_data()
	if (k == 65439 or k == 65535) and Edit_y >= 0:
		# delete
		print 'deleting row', Edit_y
		Grid_Points_y.remove(Edit_y)
		Grid_Entries_y -= 1
		Edit_y= -1
		read_data()
	if k == chr(10):
		# enter
		Edit_x= -1
		Edit_y= -1
		print 'done editing'
		read_data()
	if k == 'a':
		if Radius:
			Radius -= 1
			read_data()
		print 'radius:', Radius
	if k == 'A':
		Radius += 1
		read_data()
		print 'radius:', Radius
	if k == 'b':
		Blank_Image= not Blank_Image
	if k == 'd':
		if Dilate:
			Dilate -= 1
	if k == 'D':
		Dilate += 1
	if k == 'e':
		if Erode:
			Erode -= 1
	if k == 'E':
		Erode += 1
	if k == 'f':
		if FontSize > 0.1:
			FontSize -= 0.1
			Font= cv.InitFont(cv.CV_FONT_HERSHEY_SIMPLEX, hscale= FontSize, vscale= 1.0, shear=0, thickness=1, lineType=8)
		print 'fontsize:', FontSize
	if k == 'F':
		FontSize += 0.1
		Font= cv.InitFont(cv.CV_FONT_HERSHEY_SIMPLEX, hscale= FontSize, vscale= 1.0, shear=0, thickness=1, lineType=8)
		print 'fontsize:', FontSize
	if k == 'g':
		Display_Grid= not Display_Grid
		print 'display grid:', Display_Grid
	if k == 'h':
		print 'a : decrease radius of read aperture'
		print 'A : increase radius of read aperture'
		print 'b : blank image (to view template)'
		print 'd : decrease dilation'
		print 'D : increase dilation'
		print 'e : decrease erosion'
		print 'E : increase erosion'
		print 'f : decrease font size'
		print 'F : increase font size'
		print 'g : toggle grid display'
		print 'h : print help'
		print 'H : toggle binary / hex data display'
		print 'i : toggle invert data 0/1'
		print 'l : toggle LSB data order (default MSB)'
		print 'm : decrease bit threshold divisor'
		print 'M : decrease bit threshold divisor'
		print 'o : toggle original image display'
		print 'p : toggle peephole view'
		print 'q : quit'
		print 'r : read bits (end enter bit/grid editing mode)'
		print 'R : reset bits (and exit bit/grid editing mode)'
		print 's : show data values (HEX)'
		print 'S : save data and grid'
		print 't : apply threshold filter'
		print '+ : increase threshold filter minimum'
		print '- : decrease threshold filter minimum'
		print '? : search for HEX (highlight when HEX shown)' 
		print 
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
	if k == 'H':
		Display_Binary= not Display_Binary
		print 'display binary:', Display_Binary
	if k == 'i':
		Inverted= not Inverted
		print 'inverted:', Inverted
	if k == 'l':
		LSB_Mode= not LSB_Mode
		print 'LSB data mode:', LSB_Mode
	if k == 'm':
		ReadVal -= 1
		print 'readval:', ReadVal
		if Data_Read:
			read_data()
	if k == 'M':
		ReadVal += 1
		print 'readval:', ReadVal
		if Data_Read:
			read_data()
	if k == 'o':
		Display_Original= not Display_Original
		print 'display original:', Display_Original
	if k == 'p':
		Display_Peephole= not Display_Peephole
		print 'display peephole:', Display_Peephole
	if k == 'r':
		print 'reading %d points...' % len(Grid_Intersections)
		read_data()
	if k == 'R':
		redraw_grid()
		Data_Read= False
	if k == 's':
		Display_Data= not Display_Data
		print 'show data:', Display_Data
	if k == 'S':
		print 'saving...'
		if not Data_Read:
			print 'no data to save!'
			continue
		out= get_all_data()
		columns= Grid_Entries_x / Bits
		chunk= len(out) / columns
		for x in range(columns):
			outfile= open(basename + '.dat%d.set%d' % (x, Saveset),'w')
			outfile.write(out[x*chunk:x*chunk+chunk])
			print '%d bytes written to %s' % (chunk, basename + '.dat%d.set%d' % (x, Saveset))
			outfile.close()
		gridout= open(basename + '.grid.%d' % Saveset, 'wb')
		pickle.dump(Grid_Intersections, gridout)
		print 'grid saved to %s' % (basename + '.grid.%d' % Saveset)
		Saveset += 1
	if k == 'q':
		break
	if k == 't':
		Threshold= True
		print 'threshold:', Threshold, Filters
	if k == '-':
		if Threshold_Min >= 2:
			Threshold_Min -= 1
		print 'threshold filter %02x' % Threshold_Min
		if Data_Read:
			read_data()
	if k == '+':
		Threshold_Min += 1
		print 'threshold filter %02x' % Threshold_Min
		if Data_Read:
			read_data()
	if k == '?':
		print 'Enter space delimeted HEX (in image window), e.g. 10 A1 EF: ',
		sys.stdout.flush()
		shx= ''
		while 42:
			c= cv.WaitKey(0)
			# BS or DEL
			if c == 65288 or c == 65535 or k == 65439:
				c= 0x08
			if c > 255:
				continue
			if c == 0x0d or c == 0x0a:
				print
				break
			if c == 0x08:
				if not shx:
					sys.stdout.write('\a')
					sys.stdout.flush()
					continue
				sys.stdout.write('\b \b')
				sys.stdout.flush()
				shx= shx[:-1]
				continue
			c= chr(c)
			sys.stdout.write(c)
			sys.stdout.flush()
			shx += c
		Search_HEX= [int(h, 16) for h in shx.strip().split(' ')]
		print 'searching for', shx.upper()
