import PyQt5.QtWidgets
import PyQt5.uic

import os.path
basedir = os.path.dirname(os.path.abspath(__file__))
Ui, UiBase = PyQt5.uic.loadUiType(os.path.join(basedir, 'about.ui'))

class RomparAboutDialog(UiBase):
    def __init__(self, parent=None):
        super(RomparAboutDialog, self).__init__(parent)

        self.ui = Ui()
        self.ui.setupUi(self)

        with open(os.path.join(basedir, "about_rompar.html"), 'r') as f:
            self.ui.textEditAbout.setHtml(f.read())

        with open(os.path.join(basedir, "about_manual.html"), 'r') as f:
            self.ui.textEditManual.setHtml(f.read());

        with open(os.path.join(basedir, "about_authors.txt"), 'r') as f:
            self.ui.textEditAuthors.setText(f.read());

        with open(os.path.join(basedir, "about_license.txt"), 'r') as f:
            self.ui.textEditLicense.setText(f.read());

    @classmethod
    def showNamedTab(cls, parent, tabname):
        dialog = cls(parent)
        tabWidget = dialog.ui.tabWidget
        page = dialog.ui.tabWidget.findChild(PyQt5.QtWidgets.QWidget, tabname)
        dialog.ui.tabWidget.setCurrentWidget(page)
        dialog.show()

    @classmethod
    def showAboutRompar(cls, parent):
        cls.showNamedTab(parent, "tabRompar")

    @classmethod
    def showAboutManual(cls, parent):
        cls.showNamedTab(parent, "tabManual")

    @classmethod
    def showAboutAuthors(cls, parent):
        cls.showNamedTab(parent, "tabAuthors")

    @classmethod
    def showAboutLicense(cls, parent):
        cls.showNamedTab(parent, "tabLicense")
