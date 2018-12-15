import PyQt5.QtCore
import PyQt5.QtGui
import PyQt5.QtWidgets
import PyQt5.uic

import os.path
basedir = os.path.dirname(os.path.abspath(__file__))
Ui, UiBase = PyQt5.uic.loadUiType(os.path.join(basedir, 'findhexdialog.ui'))

class HexValidator(PyQt5.QtGui.QRegExpValidator):
    validChanged = PyQt5.QtCore.pyqtSignal(bool, name='validChanged')

    reg_ex = PyQt5.QtCore.QRegExp(
        "^[\dA-Fa-f]{2,2}(:[\dA-Fa-f]{2,2})*")

    def __init__(self, qobj):
        super(HexValidator, self).__init__(HexValidator.reg_ex, qobj)

    def fixup(self, instr):
        ret = super().fixup(instr)
        print("Fixup(%s) => %s"%(instr, ret))
        return ret

    def validate(self, instr, inpos):
        print("validate(%s, %d)" % (instr, inpos))
        numhexchar = len(instr.replace(":",""))
        numbytes = numhexchar // 2
        halfbyte = bool(numhexchar % 2)

        byteindex = inpos // 3
        byteoffset = inpos % 3

        print("numhexchar:", numhexchar,
              "numbytes:", numbytes,
              "halfbyte:", halfbyte,
              "byteindex:", byteindex,
              "byteoffset:", byteoffset)

        #if len(instr) == inpos: # at end
        if halfbyte and byteoffset == 2:
            #numhexchar: 9 numbytes: 4 halfbyte: True byteindex: 3 byteoffset: 2
            #validate(aa:a0:a0:aa0, 11) => (0, 'aa:a0:a0:aa0', 12)
            instr = instr[:inpos] + instr[inpos+1:]
            inpos += 1
        elif halfbyte and byteoffset==0:
            #numhexchar: 3 numbytes: 1 halfbyte: True byteindex: 1 byteoffset: 0
            instr = instr[:-1]+":"+instr[-1]+"0"
            inpos += 1

        ret = super().validate(instr, inpos)
        print("validate(%s, %d) => %s" % (instr, inpos, ret))
        if ret[0] == PyQt5.QtGui.QValidator.Intermediate:
            self.validChanged.emit(False)
        elif ret[0] == PyQt5.QtGui.QValidator.Acceptable:
            self.validChanged.emit(True)
        return ret

class FindHexDialog(UiBase):
    def __init__(self, parent=None):
        super(FindHexDialog, self).__init__(parent)

        self.ui = Ui()
        self.ui.setupUi(self)

        self.hex_validator = HexValidator(self.ui.editData)
        self.ui.editData.setValidator(self.hex_validator)

        self.hex_validator.validChanged.connect(self.on_hex_validator_validChanged)

    @PyQt5.QtCore.pyqtSlot(bool)
    def on_hex_validator_validChanged(self, valid):
        self.ui.buttonBox.button(PyQt5.QtWidgets.QDialogButtonBox.Ok)\
                         .setEnabled(valid);

    @property
    def hexdata(self):
        return bytes.fromhex(self.ui.editData.text().replace(":", ""))
    @hexdata.setter
    def hexdata(self, data):
        if data is None:
            return
        self.ui.editData.setText(":".join((hex(b)[2:] for b in data)))

    @classmethod
    def getBytes(cls, parent, default=b''):
        dialog = cls(parent)
        dialog.setModal(True)
        dialog.hexdata = default
        okpressed = bool(dialog.exec_())
        if okpressed:
            return dialog.hexdata, True
        else:
            return None, False
