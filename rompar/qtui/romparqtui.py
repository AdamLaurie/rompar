#! /usr/bin/env python3
import traceback
import pathlib
import json

from .. import Rompar, Config, ImgXY

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

from .about import RomparAboutDialog
from .findhexdialog import FindHexDialog

# Parse the ui file once.
import sys, os.path
from PyQt5 import uic
thisdir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(thisdir) # Needed to load ui
RomparUi, RomparUiBase = uic.loadUiType(os.path.join(thisdir, 'main.ui'))
del sys.path[-1] # Remove the now unnecessary path entry

class RomparUiQt(QtWidgets.QMainWindow):
    def __init__(self, config, *, img_fn=None, grid_fn=None,
                 group_cols=0, group_rows=0):
        super(RomparUiQt, self).__init__()
        self.ui = RomparUi()
        self.ui.setupUi(self)

        self.config = config
        self.grid_fn = pathlib.Path(grid_fn).expanduser().absolute() \
                       if grid_fn else None
        grid_json = None
        if self.grid_fn:
            with self.grid_fn.open('r') as gridfile:
                print("loading", self.grid_fn)
                grid_json = json.load(gridfile)

        self.romp = Rompar(config,
                           img_fn=img_fn, grid_json=grid_json,
                           group_cols=group_cols, group_rows=group_rows)
        self.saven = 0

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
        self.qImg = QtGui.QImage(self.img.data,
                                 self.romp.img_width, self.romp.img_height,
                                 self.romp.img_channels * self.romp.img_width,
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
            fn = self.grid_fn.with_suffix(".s%d.json" % self.saven)
            if not fn.is_file():
                return fn
            self.saven += 1

    def save_grid(self, backup=False):
        backup_fn = None
        if backup:
            backup_fn = self.next_save()
            self.grid_fn.rename(backup_fn)

        try:
            with self.grid_fn.open('w') as f:
                json.dump(self.romp.dump_grid_configuration(),
                          f, indent=4, sort_keys=True)
            self.showTempStatus('Saved Grid %s (%s)' % \
                                (str(self.grid_fn),
                                 ("Backed Up: %s" % str(backup_fn)) if backup
                                 else "No Back Up"))
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error Saving '%s'"%(self.grid_fn),
                                          traceback.format_exc())
            return False
        return True

    def save_data_as_text(self, filepath):
        try:
            with filepath.open('w') as f:
                self.romp.write_data_as_txt(f)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self,"Error Saving '%s'"%(filepath),
                                          traceback.format_exc())
            return False
        return True

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
        data, okpressed = FindHexDialog.getBytes(self, self.romp.Search_HEX)
        if okpressed:
            self.showTempStatus('searching for',":".join((hex(b)[2:] for b in data)))
            if data == self.romp.Search_HEX:
                return
            self.romp.Search_HEX = data
            self.display_image()

    @QtCore.pyqtSlot()
    def on_actionSave_triggered(self):
        self.save_grid(backup=False)

    @QtCore.pyqtSlot()
    def on_actionBackupSave_triggered(self):
        self.save_grid(backup=True)

    @QtCore.pyqtSlot()
    def on_actionSaveAs_triggered(self):
        name, filter = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save Grid (json) File', str(self.grid_fn), "Grid (*.json)")
        if (name, filter) == ('', ''):
            return
        old_grid_fn = self.grid_fn
        self.grid_fn = pathlib.Path(name).expanduser().absolute()
        if self.save_grid(backup=False):
            self.saven = 0
        else:
            self.grid_fn = old_grid_fn # Restore old value if save as failed.

    @QtCore.pyqtSlot()
    def on_actionSaveDataAsText_triggered(self):
        fname, filter = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save Data as txt file',
            str(self.grid_fn.with_suffix('.txt')), "Text (*.txt)")
        if (fname, filter) == ('', ''):
            return
        filepath = pathlib.Path(fname).expanduser().absolute()
        if self.save_data_as_text(filepath):
            self.showTempStatus('Exported data to', str(filepath))


    # Increment/Decrement values
    @QtCore.pyqtSlot()
    def on_actionRadiusIncrease_triggered(self):
        self.config.radius += 1
        self.showTempStatus('Radius %02x' % self.config.radius)
        self.romp.read_data()
        self.display_image()
    @QtCore.pyqtSlot()
    def on_actionRadiusDecrease_triggered(self):
        self.config.radius = max(self.config.radius-1, 1)
        self.showTempStatus('Radius %02x' % self.config.radius)
        self.romp.read_data()
        self.display_image()

    @QtCore.pyqtSlot()
    def on_actionDilateIncrease_triggered(self):
        self.config.dilate += 1
        self.showTempStatus('Dilate %02x' % self.config.dilate)
        self.romp.read_data()
        self.display_image()
    @QtCore.pyqtSlot()
    def on_actionDilateDecrease_triggered(self):
        self.config.dilate = max(self.config.dilate - 1, 0)
        self.showTempStatus('Dilate %02x' % self.config.dilate)
        self.romp.read_data()
        self.display_image()

    @QtCore.pyqtSlot()
    def on_actionErodeIncrease_triggered(self):
        self.config.erode += 1
        self.showTempStatus('Erode %02x' % self.config.erode)
        self.romp.read_data()
        self.display_image()
    @QtCore.pyqtSlot()
    def on_actionErodeDecrease_triggered(self):
        self.config.font_size = max(self.config.font_size - 0.1, 0)
        self.showTempStatus('Erode %02x' % self.config.erode)
        self.romp.read_data()
        self.display_image()

    @QtCore.pyqtSlot()
    def on_actionFontIncrease_triggered(self):
        self.config.font_size += 0.1
        self.showTempStatus('Font Size %02x' % self.config.font_size)
        self.romp.read_data()
        self.display_image()
    @QtCore.pyqtSlot()
    def on_actionFontDecrease_triggered(self):
        self.config.font_size = max(self.config.font_size - 0.1, 0)
        self.showTempStatus('Font Size %02x' % self.config.font_size)
        self.romp.read_data()
        self.display_image()

    @QtCore.pyqtSlot()
    def on_actionBitThresholdDivisorIncrease_triggered(self):
        self.config.bit_thresh_div += 1
        self.showTempStatus('Threshold div %02x' % self.config.bit_thresh_div)
        self.romp.read_data()
        self.display_image()
    @QtCore.pyqtSlot()
    def on_actionBitThresholdDivisorDecrease_triggered(self):
        self.config.bit_thresh_div -= 1
        self.showTempStatus('Threshold div %02x' % self.config.bit_thresh_div)
        self.romp.read_data()
        self.display_image()

    @QtCore.pyqtSlot()
    def on_actionPixelThresholdMinimumIncrease_triggered(self):
        self.config.pix_thresh_min = min(self.config.pix_thresh_min + 1, 0xFF)
        self.showTempStatus('Threshold filter %02x' % self.config.pix_thresh_min)
        self.romp.read_data()
        self.display_image()
    @QtCore.pyqtSlot()
    def on_actionPixelThresholdMinimumDecrease_triggered(self):
        self.config.pix_thresh_min = max(self.config.pix_thresh_min - 1, 0x01)
        self.showTempStatus('Threshold filter %02x' % self.config.pix_thresh_min)
        self.romp.read_data()
        self.display_image()

    # Change the base image of the display.
    @QtCore.pyqtSlot()
    def on_actionImgBGBlank_triggered(self):
        self.showTempStatus('BG Image: Blank')
        self.config.img_display_blank_image = True
        self.config.img_display_original = False
        self.display_image()
    @QtCore.pyqtSlot()
    def on_actionImgBGOriginal_triggered(self):
        self.showTempStatus('BG Image: Original')
        self.config.img_display_blank_image = False
        self.config.img_display_original = True
        self.display_image()
    @QtCore.pyqtSlot()
    def on_actionImgBGTarget_triggered(self):
        self.showTempStatus('BG Image: Target')
        self.config.img_display_blank_image = False
        self.config.img_display_original = False
        self.display_image()

    # Toggle Options
    @QtCore.pyqtSlot(bool)
    def on_actionShowGrid_triggered(self, checked):
        self.showTempStatus('Display Grid', "on" if checked else "off")
        self.config.img_display_grid = checked
        self.display_image()

    @QtCore.pyqtSlot(bool)
    def on_actionShowDataBinary_triggered(self, checked):
        self.showTempStatus('Display Data in', "BIN" if checked else "HEX")
        self.config.img_display_binary = checked
        self.display_image()

    @QtCore.pyqtSlot(bool)
    def on_actionShowPeephole_triggered(self, checked):
        self.showTempStatus('Peephole Mask', "on" if checked else "off")
        self.config.img_display_peephole = checked
        self.display_image()

    @QtCore.pyqtSlot(bool)
    def on_actionShowData_triggered(self, checked):
        self.showTempStatus('Display Data', "on" if checked else "off")
        self.config.img_display_data = checked
        self.display_image()

    @QtCore.pyqtSlot(bool)
    def on_actionDataInverted_triggered(self, checked):
        self.showTempStatus('Display %sinverted' % ("" if checked else "NOT "))
        self.config.inverted = checked
        self.display_image()

    @QtCore.pyqtSlot(bool)
    def on_actionDataLSBitMode_triggered(self, checked):
        self.showTempStatus('Data', "LSB" if checked else "MSB")
        self.config.LSB_Mode = checked
        if self.config.img_display_data:
            self.display_image()

    #@QtCore.pyqtSlot()
    #def on__triggered(self): # Shift + R
    #    self.romp.read_data()
    #    self.display_image()
    #    self.showTempStatus("Data re-read from image...")

    #@QtCore.pyqtSlot()
    #def on__triggered(self): # r
    #    self.romp.read_data()
    #    self.display_image()
    #    self.showTempStatus("Data re-read from image...")


    ############################################
    # Slots for Mouse Events from Graphicsview #
    ############################################

    @QtCore.pyqtSlot(QtCore.QPointF, int)
    def on_graphicsView_sceneLeftClicked(self, qimg_xy, keymods):
        img_xy = ImgXY(qimg_xy.x(), qimg_xy.y())
        if True: # Data Edit Mode
            try:
                self.romp.toggle_data(self.romp.imgxy_to_bitxy(img_xy))
                self.display_image()
            except IndexError as e:
                print("No bit toggled")
        else: # Grid Edit Mode
            do_autocenter = keymods & QtCore.Qt.ShiftModifier
            self.romp.grid_add_vertical_line(img_xy, do_autocenter)
            self.display_image()

    @QtCore.pyqtSlot(QtCore.QPointF, int)
    def on_graphicsView_sceneRightClicked(self, qimg_xy, keymods):
        img_xy = ImgXY(qimg_xy.x(), qimg_xy.y())
        if True: # Data Edit Mode
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
        else: # Grid Edit Mode
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

    window = RomparUiQt(config,
                        img_fn=args.image, grid_fn=args.load,
                        group_cols=args.cols_per_group,
                        group_rows=args.rows_per_group)
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
