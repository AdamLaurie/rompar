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

MODE_EDIT_GRID = 0
MODE_EDIT_DATA = 1

class RomparUiQt(QtWidgets.QMainWindow):
    def __init__(self, config, *, img_fn=None, grid_fn=None,
                 group_cols=0, group_rows=0, txt=None, annotate=None):
        super(RomparUiQt, self).__init__()
        self.ui = RomparUi()
        self.ui.setupUi(self)

        self.config = config
        self.grid_fn = pathlib.Path(grid_fn).expanduser().absolute() \
                       if grid_fn else None
        grid_json = None
        grid_dir_path = None

        if self.grid_fn:
            self.mode = MODE_EDIT_DATA
            with self.grid_fn.open('r') as gridfile:
                print("loading", self.grid_fn)
                grid_json = json.load(gridfile)
            grid_dir_path = self.grid_fn.parent
        else:
            self.mode = MODE_EDIT_GRID
            self.ui.actionSave.setEnabled(False)
            self.ui.actionBackupSave.setEnabled(False)

        self.romp = Rompar(config,
                           img_fn=img_fn, grid_json=grid_json,
                           group_cols=group_cols, group_rows=group_rows,
                           grid_dir_path=grid_dir_path,
                           annotate=annotate)
        self.saven = 0

        # QT Designer doesn't support adding buttons to the taskbar.
        # This moves a button at the botton of the window to the taskbar,
        self.statusBar().addPermanentWidget(self.ui.buttonToggleMode)

        # Make the edit mode exclusive.
        self.mode_selection = QtWidgets.QActionGroup(self)
        self.mode_selection.addAction(self.ui.actionGridEditMode)
        self.mode_selection.addAction(self.ui.actionDataEditMode)
        self.mode_selection.exclusive = True
        if self.mode == MODE_EDIT_GRID:
            self.ui.actionGridEditMode.setChecked(True)
        else:
            self.ui.actionDataEditMode.setChecked(True)


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

        # Must be loaded before initial draw
        if txt:
            self.romp.load_txt_data(open(txt, "r"))

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
                json.dump(self.romp.dump_grid_configuration(self.grid_fn.parent),
                          f, indent=4, sort_keys=True)

            # Enable the save options once a save succeeded
            self.ui.actionSave.setEnabled(True)
            self.ui.actionBackupSave.setEnabled(True)

            self.showTempStatus('Saved Grid %s (%s)' % \
                                (str(self.grid_fn),
                                 ("Backed Up: %s" % str(backup_fn)) if backup
                                 else "No Back Up"))
        except Exception as e:
            if backup_fn:
                backup_fn.rename(self.grid_fn) # Restore backup
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

    def shift_xy(self, dx, dy):
        self.romp.shift_xy(dx, dy)
        self.romp.redraw_grid()
        self.display_image()

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
        default_fn = self.grid_fn if self.grid_fn else self.romp.img_fn.parent
        name, filter = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save Grid (json) File', str(default_fn), "Grid (*.json)")
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
        if self.grid_fn is not None:
            defname = str(self.grid_fn.with_suffix('.txt'))
        else:
            defname = ''
        fname, filter = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save Data as txt file', defname , "Text (*.txt)")
        if (fname, filter) == ('', ''):
            return
        filepath = pathlib.Path(fname).expanduser().absolute()
        if self.save_data_as_text(filepath):
            self.showTempStatus('Exported data to', str(filepath))

    @QtCore.pyqtSlot()
    def on_actionRedrawGrid_triggered(self):
        self.romp.redraw_grid()
        self.display_image()
        self.showTempStatus('Grid Redrawn')

    @QtCore.pyqtSlot()
    def on_actionRereadData_triggered(self):
        button = QtWidgets.QMessageBox.question(
            self, 'Re-read Data?',
            "Are you sure you want to reread the data? "
            "Any manual edits will be lost.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No)
        if button == QtWidgets.QMessageBox.Yes:
            self.romp.read_data()
            self.display_image()
            self.showTempStatus('Re-read data.')

    @QtCore.pyqtSlot()
    def on_actionToggleMode_triggered(self):
        self.ui.buttonToggleMode.setChecked(not self.ui.buttonToggleMode.isChecked())

    @QtCore.pyqtSlot(bool)
    def on_buttonToggleMode_toggled(self, checked):
        print("Changing Edit mode")
        if checked:
            self.mode = MODE_EDIT_GRID
            self.ui.actionGridEditMode.setChecked(True)
        else:
            self.mode = MODE_EDIT_DATA
            self.ui.actionDataEditMode.setChecked(True)

    @QtCore.pyqtSlot()
    def on_actionGridEditMode_triggered(self):
        self.ui.buttonToggleMode.setChecked(True)

    @QtCore.pyqtSlot()
    def on_actionDataEditMode_triggered(self):
        self.ui.buttonToggleMode.setChecked(False)

    # Increment/Decrement values
    @QtCore.pyqtSlot()
    def on_actionRadiusIncrease_triggered(self):
        self.config.radius += 1
        self.showTempStatus('Radius %d' % self.config.radius)
        self.romp.read_data()
        self.display_image()
    @QtCore.pyqtSlot()
    def on_actionRadiusDecrease_triggered(self):
        self.config.radius = max(self.config.radius-1, 1)
        self.showTempStatus('Radius %d' % self.config.radius)
        self.romp.read_data()
        self.display_image()

    @QtCore.pyqtSlot()
    def on_actionDilateIncrease_triggered(self):
        self.config.dilate += 1
        self.showTempStatus('Dilate %d' % self.config.dilate)
        self.romp.read_data()
        self.display_image()
    @QtCore.pyqtSlot()
    def on_actionDilateDecrease_triggered(self):
        self.config.dilate = max(self.config.dilate - 1, 0)
        self.showTempStatus('Dilate %d' % self.config.dilate)
        self.romp.read_data()
        self.display_image()

    @QtCore.pyqtSlot()
    def on_actionErodeIncrease_triggered(self):
        self.config.erode += 1
        self.showTempStatus('Erode %f' % self.config.erode)
        self.romp.read_data()
        self.display_image()
    @QtCore.pyqtSlot()
    def on_actionErodeDecrease_triggered(self):
        self.config.font_size = max(self.config.font_size - 0.1, 0)
        self.showTempStatus('Erode %f' % self.config.erode)
        self.romp.read_data()
        self.display_image()

    @QtCore.pyqtSlot()
    def on_actionFontIncrease_triggered(self):
        self.config.font_size += 0.1
        self.showTempStatus('Font Size %f' % self.config.font_size)
        self.romp.read_data()
        self.display_image()
    @QtCore.pyqtSlot()
    def on_actionFontDecrease_triggered(self):
        self.config.font_size = max(self.config.font_size - 0.1, 0)
        self.showTempStatus('Font Size %f' % self.config.font_size)
        self.romp.read_data()
        self.display_image()

    @QtCore.pyqtSlot()
    def on_actionBitThresholdDivisorIncrease_triggered(self):
        self.config.bit_thresh_div += 1
        self.showTempStatus('Threshold div %d' % self.config.bit_thresh_div)
        self.romp.read_data()
        self.display_image()
    @QtCore.pyqtSlot()
    def on_actionBitThresholdDivisorDecrease_triggered(self):
        self.config.bit_thresh_div -= 1
        self.showTempStatus('Threshold div %d' % self.config.bit_thresh_div)
        self.romp.read_data()
        self.display_image()

    @QtCore.pyqtSlot()
    def on_actionPixelThresholdMinimumIncrease_triggered(self):
        self.config.pix_thresh_min = min(self.config.pix_thresh_min + 1, 0xFF)
        self.showTempStatus('Threshold filter %d' % self.config.pix_thresh_min)
        self.romp.read_data()
        self.display_image()
    @QtCore.pyqtSlot()
    def on_actionPixelThresholdMinimumDecrease_triggered(self):
        self.config.pix_thresh_min = max(self.config.pix_thresh_min - 1, 0x01)
        self.showTempStatus('Threshold filter %d' % self.config.pix_thresh_min)
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

    # Edit Grid Buttons
    @QtCore.pyqtSlot()
    def on_actionDeleteColumn_triggered(self):
        if self.romp.Edit_x >= 0:
            if self.romp.del_bit_column(self.romp.Edit_x):
                self.romp.Edit_x, self.romp.Edit_y = -1, -1
                self.display_image()
                self.showTempStatus('Deleted Column')

    @QtCore.pyqtSlot()
    def on_actionDeleteRow_triggered(self):
        if self.romp.Edit_y >= 0:
            if self.romp.del_bit_row(self.romp.Edit_y):
                self.romp.Edit_x, self.romp.Edit_y = -1, -1
                self.display_image()
                self.showTempStatus('Deleted Row')

    @QtCore.pyqtSlot()
    def on_actionMoveColumnLeft_triggered(self):
        if self.romp.Edit_x >= 0:
            if self.romp.move_bit_column(self.romp.Edit_x, -1, relative=True):
                self.display_image()

    @QtCore.pyqtSlot()
    def on_actionMoveColumnRight_triggered(self):
        if self.romp.Edit_x >= 0:
            if self.romp.move_bit_column(self.romp.Edit_x, 1, relative=True):
                self.display_image()

    @QtCore.pyqtSlot()
    def on_actionMoveRowDown_triggered(self):
        if self.romp.Edit_y >= 0:
            if self.romp.move_bit_row(self.romp.Edit_y, 1, relative=True):
                self.display_image()

    @QtCore.pyqtSlot()
    def on_actionMoveRowUp_triggered(self):
        if self.romp.Edit_y >= 0:
            if self.romp.move_bit_row(self.romp.Edit_y, -1, relative=True):
                self.display_image()


    ############################################
    # Slots for Mouse Events from Graphicsview #
    ############################################

    @QtCore.pyqtSlot(QtCore.QPointF, int)
    def on_graphicsView_sceneLeftClicked(self, qimg_xy, keymods):
        img_xy = ImgXY(int(qimg_xy.x()), int(qimg_xy.y()))
        if self.mode == MODE_EDIT_DATA: # Data Edit Mode
            try:
                self.romp.toggle_data(self.romp.imgxy_to_bitxy(img_xy))
                self.display_image()
            except IndexError as e:
                print("No bit toggled")
        elif self.mode == MODE_EDIT_GRID: # Grid Edit Mode
            do_autocenter = keymods & QtCore.Qt.ShiftModifier
            self.romp.grid_add_vertical_line(img_xy, do_autocenter)
            self.display_image()

    @QtCore.pyqtSlot(QtCore.QPointF, int)
    def on_graphicsView_sceneRightClicked(self, qimg_xy, keymods):
        img_xy = ImgXY(int(qimg_xy.x()), int(qimg_xy.y()))
        if self.mode == MODE_EDIT_DATA: # Data Edit Mode
            self.select_bit_group(img_xy)
        elif self.mode == MODE_EDIT_GRID: # Grid Edit Mode
            do_autocenter = keymods & QtCore.Qt.ShiftModifier
            self.romp.grid_add_horizontal_line(img_xy, do_autocenter)
            self.display_image()

    def select_bit_group(self, img_xy):
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

def load_anotate(fn):
    """
    Really this is a set of (row, col): how, but that type of key doesn't map well to json
    So instead re-process the keys
    In: "1,2"
    Out: (1, 2)

    Ex: annotate col=1, row=2 red
    {
        "1,2": {"color": [255, 0, 0]}
    }
    """
    j = json.load(open(fn, "r"))

    ret = {}
    for k, v in j.items():
        c,r = k.split(",")
        ret[(int(c), int(r))] = v
    return ret

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
    parser.add_argument('--txt', help='Load given .txt instead of .json binary')
    parser.add_argument('--dx', type=int, help='Shift data relative to image x pixels')
    parser.add_argument('--dy', type=int, help='Shift data relative to image y pixels')
    parser.add_argument('--annotate', help='Annotation .json')
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
    annotate = None
    if args.annotate:
        annotate = load_anotate(args.annotate)

    window = RomparUiQt(config,
                        img_fn=args.image, grid_fn=args.load,
                        group_cols=args.cols_per_group,
                        group_rows=args.rows_per_group,
                        txt=args.txt, annotate=annotate)
    if args.dx or args.dy:
        window.shift_xy(args.dx, args.dy)
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
