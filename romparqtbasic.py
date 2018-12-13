#! /usr/bin/env python

from __future__ import print_function
from __future__ import division

from rompar import Rompar, Config
from rompar.romparuiopencv import RomparUIOpenCV

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5 import uic

class RomparQtBasic(QtWidgets.QMainWindow):
    def __init__(self, romp):
        super(RomparQtBasic, self).__init__()
        uic.loadUi('rompar/main_basic.ui', self)
        self.setWindowTitle("Rompar")

        self.romp = romp
        self.config = self.romp.config

        self.pixmapitem = QtWidgets.QGraphicsPixmapItem()
        self.scene = QtWidgets.QGraphicsScene()
        self.scene.addItem(self.pixmapitem)

        self.statusBar().showMessage("DERP")

        self.graphicsView.setScene(self.scene)
        self.graphicsView.setAlignment(QtCore.Qt.AlignTop|QtCore.Qt.AlignLeft)

        # Do initial draw
        self.img = self.romp.render_image(rgb=True)
        self.qImg = QtGui.QImage(self.img.data, romp.width, romp.height,
                            self.romp.numchannels * self.romp.width,
                            QtGui.QImage.Format_RGB888)
        self.pixmapitem.setPixmap(QtGui.QPixmap(self.qImg))

    def display_image(self):
        self.romp.render_image(img_display=self.img, rgb=True)
        self.pixmapitem.setPixmap(QtGui.QPixmap(self.qImg))

    def keyPressEvent(self, event):
        config = self.config
        key = event.key()
        shift = event.modifiers() & QtCore.Qt.ShiftModifier

        if key == QtCore.Qt.Key_A:
            if shift: # 'A'
                config.radius += 1
            else: # 'a'
                config.radius = max(config.radius-1, 1)
            self.romp.read_data(force=True)
            self.display_image()

        elif key == QtCore.Qt.Key_D:
            if shift: # 'D':
                config.dilate += 1
            else: # 'd'
                config.dilate = max(config.dilate - 1, 0)
            self.romp.read_data(force=True)
            self.display_image()

        elif key == QtCore.Qt.Key_E:
            if shift: # 'E':
                config.erode += 1
            else: # 'e'
                config.erode = max(config.erode - 1, 0)
            self.romp.read_data(force=True)
            self.display_image()

        elif key == QtCore.Qt.Key_F:
            if shift: # 'F'
                config.font_size += 0.1
            else: # 'f'
                config.font_size = max(config.font_size - 0.1, 0)
            self.romp.read_data(force=True)
            self.display_image()

        elif key == QtCore.Qt.Key_M:
            if shift: # 'M'
                config.bit_thresh_div += 1
            else: # 'm'
                config.bit_thresh_div -= 1
            self.romp.read_data(force=True)
            self.display_image()

        elif key == QtCore.Qt.Key_Minus:
            config.pix_thresh_min = max(config.pix_thresh_min - 1, 0x01)
            self.showTempStatus('Threshold filter %02x' % config.pix_thresh_min)
            self.romp.read_data(force=True)
            self.display_image()
        elif key == QtCore.Qt.Key_Plus:
            config.pix_thresh_min = min(config.pix_thresh_min + 1, 0xFF)
            self.showTempStatus('Threshold filter %02x' % config.pix_thresh_min)
            self.romp.read_data(force=True)
            self.display_image()


        #elif event.key() == QtCore.Qt.Key_Escape:
        #    self.close()

        elif key == QtCore.Qt.Key_B and not shift:
            config.img_display_blank_image = not config.img_display_blank_image
            self.display_image()

        elif key == QtCore.Qt.Key_G and not shift:
            config.img_display_grid = not config.img_display_grid
            self.showTempStatus('Display grid:', config.img_display_grid)

        elif key == QtCore.Qt.Key_H and shift:
            config.img_display_binary = not config.img_display_binary
            self.showTempStatus('Display binary:', config.img_display_binary)

        elif key == QtCore.Qt.Key_I and not shift:
            config.inverted = not config.inverted
            if config.img_display_data:
                self.display_image()
            self.showTempStatus('Inverted:', config.inverted)

        elif key == QtCore.Qt.Key_L and not shift:
            config.LSB_Mode = not config.LSB_Mode
            if config.img_display_data:
                self.display_image()
            self.showTempStatus('LSB self.romp.data mode:', config.LSB_Mode)

        elif key == QtCore.Qt.Key_O and not shift:
            config.img_display_original = not config.img_display_original
            self.display_image()
            self.showTempStatus('display original:', config.img_display_original)

        elif key == QtCore.Qt.Key_P and not shift:
            config.img_display_peephole = not config.img_display_peephole
            self.display_image()
            self.showTempStatus('display peephole:', config.img_display_peephole)

        #elif key == QtCore.Qt.Key_R and shift:
        #    self.romp.read_data(force=True)
        #    self.display_image()
        #    self.statusBar().showMessage("Data re-read from image...", 4000)

        elif key == QtCore.Qt.Key_R and not shift:
            self.romp.read_data(force=True)
            self.display_image()
            self.statusBar().showMessage("Data re-read from image...", 4000)

        elif key == QtCore.Qt.Key_S and not shift:
            config.img_display_data = not config.img_display_data
            self.display_image()

        else:
            super(RomparQtBasic, self).keyPressEvent(event)

    def mousePressEvent(self, event):
        origin = self.graphicsView.mapFromParent(event.pos())
        scene = self.graphicsView.mapToScene(origin)
        img_xy = (scene.x(), scene.y())
        #self.statusBar().showMessage(
        #    "event:%d,%d; view:%d,%d; scene: %d,%d" %
        #    (event.x(), event.y(), origin.x(), origin.y(), scene.x(), scene.y())
        #)

        if event.button() == QtCore.Qt.LeftButton:
            if self.romp.data_read:
                try:
                    self.romp.toggle_data(self.romp.imgxy_to_bitxy(img_xy))
                    self.display_image()
                except IndexError as e:
                    print("No bit toggled")
            else:
                do_autocenter = event.modifiers() & QtCore.Qt.ShiftModifier
                self.romp.grid_add_vertical_line(img_xy, do_autocenter)
                self.display_image()

        elif event.button() == QtCore.Qt.RightButton:
            if self.romp.data_read:
                try:
                    tempx, tempy = self.romp.imgxy_to_bitxy(img_xy)
                    if (tempx, tempy) == (self.romp.Edit_x, self.romp.Edit_y):
                        self.romp.Edit_x, self.romp.Edit_y = -1, -1
                    else:
                        self.romp.Edit_x, self.romp.Edit_y = tempx, tempy
                    self.display_image()
                    self.showTempStatus("Edit x,y:",
                                        self.romp.Edit_x, self.romp.Edit_y)
                except IndexError as e:
                    self.showTempStatus("No bit group selected")
            else:
                do_autocenter = event.modifiers() & QtCore.Qt.ShiftModifier
                self.romp.grid_add_horizontal_line(img_xy, do_autocenter)
                self.display_image()

        else:
            super(RomparQtBasic, self).mousePressEvent(event)

    def showTempStatus(self, *msg):
        full_msg = " ".join((str(part) for part in msg))
        print("Status:", repr(full_msg))
        self.statusBar().showMessage(full_msg, 4000)

def run(app):
    import argparse
    parser = argparse.ArgumentParser(description='Extract mask ROM image')
    parser.add_argument('--radius', type=int,
                        help='Use given radius for display, '
                        'bounded square for detection')
    parser.add_argument('--bit-thresh-div', type=str,
                        help='Bit set area threshold divisor')
    # Only care about min
    parser.add_argument('--pix-thresh', type=str,
                        help='Pixel is set threshold minimum')
    parser.add_argument('--dilate', type=str, help='Dilation')
    parser.add_argument('--erode', type=str, help='Erosion')
    parser.add_argument('--debug', action='store_true', help='')
    parser.add_argument('--load', help='Load saved grid file')
    parser.add_argument('image', nargs='?', help='Input image')
    parser.add_argument('cols_per_group', nargs='?', type=int, help='')
    parser.add_argument('rows_per_group', nargs='?', type=int, help='')
    args = parser.parse_args()

    config = Config()
    if args.radius:
        config.default_radius = args.radius
        config.radius = args.radius
    if args.bit_thresh_div:
        config.bit_thresh_div = int(args.bit_thresh_div, 0)
    if args.pix_thresh:
        config.pix_thresh_min = int(args.pix_thresh, 0)
    if args.dilate:
        config.dilate = int(args.dilate, 0)
    if args.erode:
        config.erode = int(args.erode, 0)

    romp = Rompar(config,
                  img_fn=args.image, grid_file=args.load,
                  group_cols=args.cols_per_group,
                  group_rows=args.rows_per_group)

    window = RomparQtBasic(romp)
    window.show()

    return app.exec_() # Start the event loop.

def main():
    import sys

    # Initialize the QApplication object, and free it last.
    # Not having this in a different function than other QT
    # objects can cause segmentation faults as app is freed
    # before the QEidgets.
    app = QtWidgets.QApplication(sys.argv)

    # Allow Ctrl-C to interrupt QT by scheduling GIL unlocks.
    timer = QtCore.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None) # Let the interpreter run.

    sys.exit(run(app))

if __name__ == "__main__":
    main()
