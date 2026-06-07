from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QListWidget,
    QTextEdit, QLabel, QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
import rompanel

h2i = lambda i: int(i, 16)

carry = 0

class DialoguePanel(rompanel.ROMPanel):

    frameTitle = "Dialogue/Text Editor"

    def init(self):

        self.curBankIdx = 0
        self.curLineIdx = 0
        self.broken = False

        # Lines group
        sbs1 = QGroupBox("Lines")
        sbs1_layout = QHBoxLayout(sbs1)

        self.lineList = QListWidget()
        self.lineList.setFixedSize(350, 300)
        self.lineList.setSelectionMode(QAbstractItemView.SingleSelection)
        sbs1_layout.addWidget(self.lineList)

        # Edit group
        sbs2 = QGroupBox("Edit")
        sbs2_layout = QVBoxLayout(sbs2)

        self.editBox = QTextEdit()
        self.editBox.setFixedSize(470, 60)
        self.editBox.setFont(QFont("Courier New", 12, QFont.Bold))
        self.editBox.setAcceptRichText(False)
        sbs2_layout.addWidget(self.editBox)

        self.symbolsBox = rompanel.HexBox(self, None)
        self.symbolsBox.setFixedSize(470, 42)
        sbs2_layout.addWidget(self.symbolsBox)

        # Layout
        self.sizer.addWidget(sbs1, 0, 0)
        self.sizer.addWidget(sbs2, 1, 0)

        self.editBox.setEnabled(False)

        # Connect signals
        self.lineList.currentRowChanged.connect(self.OnSelectLine)
        self.editBox.textChanged.connect(self.OnEditText)

    def OnSelectBank(self, idx):
        self.changeBank(idx)

    def changeBank(self, num):
        self.curBankIdx = num
        if not self.curBank.loaded:
            self.rom.getDialogue(num)

        self.lineList.clear()
        for i, line in enumerate(self.curBank.lines):
            self.lineList.addItem("%03x: %s" % (i + num * 64, line.text))

        self.editBox.setEnabled(False)

    def OnSelectLine(self, row):
        if row >= 0:
            self.curLineIdx = row
            self.changeLine(self.curLineIdx)

    def OnEditText(self):
        text = self.editBox.toPlainText()
        item = self.lineList.item(self.curLineIdx)
        if item:
            item.setText("%03x: %s" % (self.curLineIdx + self.curBankIdx * 64, text))

        line = self.curLine
        line.text = text
        self.broken = False

        symbols = line.hexlify(self.rom, check=True)
        self.broken = line.broken

        if text != line.originalText:
            self.curBank.modified = True
            self.modify()

        if self.broken:
            self.editBox.setStyleSheet("background-color: #FFB0B0;")
        else:
            self.editBox.setStyleSheet("background-color: #FFFFFF;")

        self.symbolsBox.setPlainText(symbols)

    def changeLine(self, num):
        line = self.curLine
        self.editBox.blockSignals(True)
        self.editBox.setPlainText(line.text)
        self.editBox.blockSignals(False)

        symbols = line.hexlify(self.rom)
        self.symbolsBox.setPlainText(symbols)

        if not self.editBox.isEnabled():
            self.editBox.setEnabled(True)

        self.updateModifiedIndicator(self.getCurrentData().modified)

    def getCurrentData(self):
        if self.curBank.loaded:
            return self.curLine
        return None

    changeSelection = changeBank

    curBank = property(lambda self: self.rom.data["dialogue"][self.curBankIdx])
    curLine = property(lambda self: self.curBank.lines[self.curLineIdx])