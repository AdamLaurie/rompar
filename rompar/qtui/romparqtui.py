#! /usr/bin/env python
from __future__ import print_function
from __future__ import division

from .. import Rompar, Config, ImgXY

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

from .about import RomparAboutDialog

# Parse the ui file once.
import sys, os.path
from PyQt5 import uic
thisdir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(thisdir) # Needed to load ui
RomparUi, RomparUiBase = uic.loadUiType(os.path.join(thisdir, 'main.ui'))
del sys.path[-1] # Remove the now unnecessary path entry

def symlinka(target, alias):
    '''Atomic symlink'''
    tmp = alias + '_'
    import os
    if os.path.exists(tmp):
        os.unlink(tmp)
    os.symlink(target, alias + '_')
    os.rename(tmp, alias)

class RomparUiQt(QtWidgets.QMainWindow):
    def __init__(self, romp):
        super(RomparUiQt, self).__init__()
        self.ui = RomparUi()
        self.ui.setupUi(self)

        self.romp = romp
        self.config = self.romp.config
        self.saven = 0
        self.basename = os.path.splitext(self.romp.img_fn)[0]

        # Make the Image BG selection exclusive.
        self.baseimage_selection = QtWidgets.QActionGroup(self)
        self.baseimage_selection.addAction(self.ui.actionImgBGBlank)
        self.baseimage_selection.addAction(self.ui.actionImgBGOriginal)
        self.baseimage_selection.addAction(self.ui.actionImgBGTarget)
        self.baseimage_selection.exclusive = True

        # Note: This depends on the img_display selection order in
        # rommpar.render_image.
        if self.config.img_display_blank_image:
            self.ui.actionImgBGBlank.setChecked(True)
        elif self.config.img_display_original:
            self.ui.actionImgBGOriginal.setChecked(True)
        else:
            self.ui.actionImgBGTarget.setChecked(True)

        # Set initial state for the various check boxes.
        self.ui.actionShowGrid.setChecked(self.config.img_display_grid)
        self.ui.actionShowDataBinary.setChecked(self.config.img_display_binary)
        self.ui.actionShowPeephole.setChecked(self.config.img_display_peephole)
        self.ui.actionShowData.setChecked(self.config.img_display_data)
        self.ui.actionDataInverted.setChecked(self.config.inverted)
        self.ui.actionDataLSBitMode.setChecked(self.config.LSB_Mode)

        # Create buffers to show Rompar image in UI.
        self.pixmapitem = QtWidgets.QGraphicsPixmapItem()
        self.scene = QtWidgets.QGraphicsScene()
        self.scene.addItem(self.pixmapitem)

        self.ui.graphicsView.setScene(self.scene)
        self.ui.graphicsView.setAlignment(QtCore.Qt.AlignTop|QtCore.Qt.AlignLeft)

        # Do initial draw
        self.img = self.romp.render_image(rgb=True)
        self.qImg = QtGui.QImage(self.img.data, romp.width, romp.height,
                            self.romp.numchannels * self.romp.width,
                            QtGui.QImage.Format_RGB888)
        self.pixmapitem.setPixmap(QtGui.QPixmap(self.qImg))

    def display_image(self):
        self.romp.render_image(img_display=self.img, rgb=True)
        self.pixmapitem.setPixmap(QtGui.QPixmap(self.qImg))

    def showTempStatus(self, *msg):
        full_msg = " ".join((str(part) for part in msg))
        print("Status:", repr(full_msg))
        self.statusBar().showMessage(full_msg, 4000)

    def next_save(self):
        '''Look for next unused save slot by checking grid files'''
        while True:
            fn = self.basename + '_s%d.grid' % self.saven
            if not os.path.exists(fn):
                break
            self.saven += 1

    def save_grid(self, backup=False):
        if backup:
            self.next_save()
            fn = self.basename + '_s%d.json' % self.saven
            symlinka(fn, self.basename + '.json')
        else:
            fn = self.basename + '.json'

        with open(fn, 'w') as f:
            self.romp.write_grid(f)
        self.showTempStatus('Saved Grid %s (%s)' % \
                            (fn, "Backed Up" if backup else "No Back Up"))

    def save_data_as_text(self):
        if self.romp.data_read:
            '''Write text file like bits sown in GUI. Space between row/cols'''
            fn = self.basename + '_s%d.txt' % self.saven
            symlinka(fn, self.basename + '.txt')
            with open(fn, 'w') as f:
                self.romp.write_data_as_txt(f)
            print ('Saved %s' % fn)
        else:
            print ('No bits to save')

    ########################################
    # Slots for QActions from the UI       #
    ########################################

    @QtCore.pyqtSlot()
    def on_actionAbout_triggered(self):
        RomparAboutDialog.showAboutRompar(self)

    @QtCore.pyqtSlot()
    def on_actionManual_triggered(self):
        RomparAboutDialog.showAboutManual(self)

    @QtCore.pyqtSlot()
    def on_actionAuthors_triggered(self):
        RomparAboutDialog.showAboutAuthors(self)

    @QtCore.pyqtSlot()
    def on_actionLicense_triggered(self):
        RomparAboutDialog.showAboutLicense(self)

    @QtCore.pyqtSlot()
    def on_actionFindHex_triggered(self):
        FindHexDialog.getDouble(
            self, "QInputDialog::getDouble()", "Amount:", 37.56, -10000, 10000, 2)
        #self.romp.Search_HEX = [int(h, 16) for h in shx.strip().split(' ')]
        #print ('searching for', shx.upper())

    @QtCore.pyqtSlot()
    def on_actionSave_triggered(self):
        self.save_grid(backup=False)

    @QtCore.pyqtSlot()
    def on_actionBackupSave_triggered(self):
        self.save_grid(backup=True)

    @QtCore.pyqtSlot()
    def on_actionSaveAs_triggered(self):
        name, filter = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save Grid (json) File', self.romp.img_fn, "Grid (*.json)")
        if (name, filter) == ('', ''):
            return
        self.romp.img_fn = name
        self.basename = os.path.splitext(self.romp.img_fn)[0]
        self.save_grid(backup=False)

    # Increment/Decrement values
    @QtCore.pyqtSlot()
    def on_actionRadiusIncrease_triggered(self):
        self.config.radius += 1
        self.romp.read_data(force=True)
        self.display_image()
    @QtCore.pyqtSlot()
    def on_actionRadiusDecrease_triggered(self):
        self.config.radius = max(config.radius-1, 1)
        self.romp.read_data(force=True)
        self.display_image()

    @QtCore.pyqtSlot()
    def on_actionRadiusIncrease_triggered(self):
        self.config.dilate += 1
        self.romp.read_data(force=True)
        self.display_image()
    @QtCore.pyqtSlot()
    def on_actionRadiusDecrease_triggered(self):
        self.config.dilate = max(config.dilate - 1, 0)
        self.romp.read_data(force=True)
        self.display_image()

    @QtCore.pyqtSlot()
    def on_actionErodeIncrease_triggered(self):
        self.config.erode += 1
        self.romp.read_data(force=True)
        self.display_image()
    @QtCore.pyqtSlot()
    def on_actionErodeDecrease_triggered(self):
        self.config.font_size = max(config.font_size - 0.1, 0)
        self.romp.read_data(force=True)
        self.display_image()

    @QtCore.pyqtSlot()
    def on_actionFontIncrease_triggered(self):
        self.config.font_size += 0.1
        self.romp.read_data(force=True)
        self.display_image()
    @QtCore.pyqtSlot()
    def on_actionFontDecrease_triggered(self):
        self.config.font_size = max(config.font_size - 0.1, 0)
        self.romp.read_data(force=True)
        self.display_image()

    @QtCore.pyqtSlot()
    def on_actionBitThresholdDivisorIncrease_triggered(self):
        self.config.bit_thresh_div += 1
        self.romp.read_data(force=True)
        self.display_image()
    @QtCore.pyqtSlot()
    def on_actionBitThresholdDivisorDecrease_triggered(self):
        self.config.bit_thresh_div -= 1
        self.romp.read_data(force=True)
        self.display_image()

    @QtCore.pyqtSlot()
    def on_actionPixelThresholdMinimumIncrease_triggered(self):
        self.config.pix_thresh_min = min(self.config.pix_thresh_min + 1, 0xFF)
        self.showTempStatus('Threshold filter %02x' % self.config.pix_thresh_min)
        import time
        t = time.time()
        self.romp.read_data(force=True)
        self.display_image()
        print("REDRAW TIME", time.time()-t)
    @QtCore.pyqtSlot()
    def on_actionPixelThresholdMinimumDecrease_triggered(self):
        self.config.pix_thresh_min = max(self.config.pix_thresh_min - 1, 0x01)
        self.showTempStatus('Threshold filter %02x' % self.config.pix_thresh_min)
        self.romp.read_data(force=True)
        self.display_image()

    # Change the base image of the display.
    @QtCore.pyqtSlot()
    def on_actionImgBGBlank_triggered(self):
        self.config.img_display_blank_image = True
        self.config.img_display_original = False
        self.display_image()
    @QtCore.pyqtSlot()
    def on_actionImgBGOriginal_triggered(self):
        self.config.img_display_blank_image = False
        self.config.img_display_original = True
        self.display_image()
    @QtCore.pyqtSlot()
    def on_actionImgBGTarget_triggered(self):
        self.config.img_display_blank_image = False
        self.config.img_display_original = False
        self.display_image()

    # Toggle Options
    @QtCore.pyqtSlot(bool)
    def on_actionShowGrid_triggered(self, checked):
        self.config.img_display_grid = checked
        self.display_image()

    @QtCore.pyqtSlot(bool)
    def on_actionShowDataBinary_triggered(self, checked):
        self.config.img_display_binary = checked
        self.display_image()

    @QtCore.pyqtSlot(bool)
    def on_actionShowPeephole_triggered(self, checked):
        self.config.img_display_peephole = checked
        self.display_image()

    @QtCore.pyqtSlot(bool)
    def on_actionShowData_triggered(self, checked):
        self.config.img_display_data = checked
        self.display_image()

    @QtCore.pyqtSlot(bool)
    def on_actionDataInverted_triggered(self, checked):
        self.config.inverted = checked
        if self.config.img_display_data:
            self.display_image()
        self.showTempStatus('Inverted:', self.config.inverted)

    @QtCore.pyqtSlot(bool)
    def on_actionDataLSBitMode_triggered(self, checked):
        self.config.LSB_Mode = checked
        if self.config.img_display_data:
            self.display_image()
        self.showTempStatus('LSB self.romp.data mode:', self.config.LSB_Mode)

    #@QtCore.pyqtSlot()
    #def on__triggered(self): # Shift + R
    #    self.romp.read_data(force=True)
    #    self.display_image()
    #    self.showTempStatus("Data re-read from image...")

    #@QtCore.pyqtSlot()
    #def on__triggered(self): # r
    #    self.romp.read_data(force=True)
    #    self.display_image()
    #    self.showTempStatus("Data re-read from image...")


    ############################################
    # Slots for Mouse Events from Graphicsview #
    ############################################

    @QtCore.pyqtSlot(QtCore.QPointF, int)
    def on_graphicsView_sceneLeftClicked(self, qimg_xy, keymods):
        img_xy = ImgXY(qimg_xy.x(), qimg_xy.y())
        if self.romp.data_read:
            try:
                self.romp.toggle_data(self.romp.imgxy_to_bitxy(img_xy))
                self.display_image()
            except IndexError as e:
                print("No bit toggled")
        else:
            do_autocenter = keymods & QtCore.Qt.ShiftModifier
            self.romp.grid_add_vertical_line(img_xy, do_autocenter)
            self.display_image()

    @QtCore.pyqtSlot(QtCore.QPointF, int)
    def on_graphicsView_sceneRightClicked(self, qimg_xy, keymods):
        img_xy = ImgXY(qimg_xy.x(), qimg_xy.y())
        if self.romp.data_read:
            try:
                bit_xy = self.romp.imgxy_to_bitxy(img_xy)
                if bit_xy == (self.romp.Edit_x, self.romp.Edit_y):
                    self.romp.Edit_x, self.romp.Edit_y = -1, -1
                else:
                    self.romp.Edit_x, self.romp.Edit_y = bit_xy
                self.display_image()
                self.showTempStatus("Edit x,y:",
                                    self.romp.Edit_x, self.romp.Edit_y)
            except IndexError as e:
                self.showTempStatus("No bit group selected")
        else:
            do_autocenter = keymods & QtCore.Qt.ShiftModifier
            self.romp.grid_add_horizontal_line(img_xy, do_autocenter)
            self.display_image()


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

    window = RomparUiQt(romp)
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
