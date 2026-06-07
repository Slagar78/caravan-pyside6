import os, pickle
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem,
    QTextEdit, QLineEdit, QListWidget, QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
import rompanel
import layout

h2i = lambda i: int(i, 16)

class ROMViewerPanel(rompanel.ROMPanel):

    def init(self):

        inst = QLabel("Edit ROM layout.")
        inst.setWordWrap(True)

        self.curSectionIdx = 0

        sbs1 = QGroupBox("Sections")
        sbs1_layout = QVBoxLayout(sbs1)

        sbs2 = QGroupBox("Section Content")
        sbs2_layout = QVBoxLayout(sbs2)

        sbs3 = QGroupBox("Data Properties")
        sbs3_layout = QVBoxLayout(sbs3)

        sbs4 = QGroupBox("Misc")
        sbs4_layout = QVBoxLayout(sbs4)

        # ---------- section grid ----------
        self.sectionGrid = QTableWidget(10, 4)
        self.sectionGrid.setFixedSize(340, 200)
        self.sectionGrid.setHorizontalHeaderLabels(["Segment", "Type", "Start", "End"])
        self.sectionGrid.horizontalHeader().setDefaultSectionSize(50)
        self.sectionGrid.verticalHeader().setDefaultSectionSize(20)
        self.sectionGrid.setColumnWidth(0, 120)
        self.sectionGrid.setColumnWidth(1, 60)
        self.sectionGrid.setColumnWidth(2, 50)
        self.sectionGrid.setColumnWidth(3, 50)
        self.sectionGrid.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sectionGrid.setSelectionMode(QAbstractItemView.SingleSelection)
        font = self.sectionGrid.horizontalHeader().font()
        font.setBold(True)
        self.sectionGrid.horizontalHeader().setFont(font)

        # ---------- buttons ----------
        self.tempInsertButton = QPushButton("Insert Section")
        self.tempDeleteButton = QPushButton("Delete Section")
        self.tempShortenButton = QPushButton("Shorten Section")
        self.tempExpandButton = QPushButton("Expand Section")
        self.tempAddrCtrl = QLineEdit()
        self.tempAddrButton = QPushButton("Set Address")
        self.parseButton = QPushButton("Parse Step")
        self.tempLoadButton = QPushButton("Load")
        self.tempSaveButton = QPushButton("Save")

        sbs1_layout.addWidget(self.sectionGrid)
        sbs1_layout.addWidget(self.tempInsertButton)
        sbs1_layout.addWidget(self.tempDeleteButton)
        sbs1_layout.addWidget(self.tempShortenButton)
        sbs1_layout.addWidget(self.tempExpandButton)
        sbs1_layout.addWidget(self.tempLoadButton)
        sbs1_layout.addWidget(self.tempSaveButton)
        sbs1_layout.addWidget(self.tempAddrCtrl)
        sbs1_layout.addWidget(self.tempAddrButton)
        sbs1_layout.addWidget(self.parseButton)

        # ---------- content box ----------
        self.sectionContentCtrl = rompanel.HexListBox(self, None)
        self.sectionContentCtrl.setFixedSize(440, 200)
        sbs2_layout.addWidget(self.sectionContentCtrl)

        # ---------- data size ----------
        sizeText = QLabel("Data Size")
        self.sizeCtrl = QSpinBox()
        self.sizeCtrl.setRange(1, 8)
        sbs3propSizer = QHBoxLayout()
        sbs3propSizer.addWidget(sizeText)
        sbs3propSizer.addWidget(self.sizeCtrl)
        sbs3_layout.addLayout(sbs3propSizer)

        # ---------- description ----------
        self.descCtrl = QTextEdit()
        self.descCtrl.setFixedSize(440, 200)
        sbs4_layout.addWidget(self.descCtrl)

        # ---------- main layout ----------
        self.sizer.addWidget(inst, 0, 0)
        self.sizer.addWidget(sbs1, 1, 0, 2, 1)
        self.sizer.addWidget(sbs2, 1, 1)
        self.sizer.addWidget(sbs4, 1, 2)
        self.sizer.addWidget(sbs3, 2, 1)
        # self.sizer.addWidget(sbs4, 3, 0, 1, 2)

        self.updateSectionGrid()

        # ---------- connect signals ----------
        self.tempInsertButton.clicked.connect(self.OnTempInsert)
        self.tempDeleteButton.clicked.connect(self.OnTempDelete)
        self.tempShortenButton.clicked.connect(self.OnTempShorten)
        self.tempExpandButton.clicked.connect(self.OnTempExpand)
        self.parseButton.clicked.connect(self.OnStep)
        self.tempAddrButton.clicked.connect(self.OnTempAddrSet)
        self.tempLoadButton.clicked.connect(self.OnTempLoad)
        self.tempSaveButton.clicked.connect(self.OnTempSave)
        self.sizeCtrl.valueChanged.connect(self.OnChangeDataSize)
        self.sectionGrid.currentCellChanged.connect(self.OnCellChange)
        self.sectionGrid.cellChanged.connect(self.OnCellEdit)

        self.TempLoad()

    def OnCellChange(self, currentRow, currentColumn, previousRow, previousColumn):
        if currentRow >= 0:
            self.curSectionIdx = currentRow
            self.updateSectionContents()

    def OnCellEdit(self, row, column):
        if row < 0 or column < 0:
            return
        item = self.sectionGrid.item(row, column)
        if not item:
            return
        val = item.text()
        sect = self.rom.currentLayout.sections[row]

        if column == 0:
            sect.name = val
        elif column == 1:
            sect.type = val
        elif column == 2:
            bank = int(val[:2], 16) * 0x10000
            addr = int(val[3:], 16)
            sect.start = bank + addr
            self.rom.currentLayout.sortSections()
        elif column == 3:
            bank = int(val[:2], 16) * 0x10000
            addr = int(val[3:], 16)
            sect.end = bank + addr
            self.rom.currentLayout.sortSections()

        self.updateSectionGrid()

    def OnStep(self):
        try:
            next(self.rom.currentLayout.parseGen)
        except StopIteration:
            pass
        self.updateSectionGrid()

    def OnTempInsert(self):
        self.rom.currentLayout.addNewSection(None, None)
        self.updateSectionGrid()

    def OnTempDelete(self):
        if 0 <= self.curSectionIdx < len(self.rom.currentLayout.sections):
            self.rom.currentLayout.sections.pop(self.curSectionIdx)
        self.updateSectionGrid()

    def OnTempExpand(self):
        if self.curSectionIdx + 1 >= len(self.rom.currentLayout.sections):
            return
        sect = self.rom.currentLayout.sections[self.curSectionIdx]
        after = self.rom.currentLayout.sections[self.curSectionIdx + 1]
        size = sect.params.get("size", 1)
        sect.end += size
        after.start += size
        self.updateSectionGrid()
        self.sectionContentCtrl.scrollToBottom()

    def OnTempShorten(self):
        if self.curSectionIdx + 1 >= len(self.rom.currentLayout.sections):
            return
        sect = self.rom.currentLayout.sections[self.curSectionIdx]
        after = self.rom.currentLayout.sections[self.curSectionIdx + 1]
        size = sect.params.get("size", 1)
        sect.end -= size
        after.start -= size
        self.updateSectionGrid()
        self.sectionContentCtrl.scrollToBottom()

    def OnTempAddrSet(self):
        try:
            addr = int(self.tempAddrCtrl.text(), 16)
            self.rom.currentLayout.addrOff = addr
        except ValueError:
            pass
        self.OnStep()

    def OnTempLoad(self):
        self.TempLoad()

    def TempLoad(self):
        self.rom.currentLayout.clearContent()
        # pickle version
        with open("layout_pickled.dat", "rb") as f:
            self.rom.currentLayout = pickle.load(f)
        self.rom.currentLayout.updatePickledObj(self.rom)

        self.updateSectionGrid()
        if hasattr(self.rom.currentLayout, "lastSelected"):
            self.curSectionIdx = self.rom.currentLayout.lastSelected
            self.sectionGrid.setCurrentCell(self.curSectionIdx, 0)

    def OnTempSave(self):
        self.rom.currentLayout.clearContent()
        self.rom.currentLayout.lastSelected = self.curSectionIdx

        # non-pickle version
        lines = []
        for s in self.rom.currentLayout.sections:
            lines.append(f"{s.name}, {s.type}, {s.start}, {s.end}")
        with open("layout.dat", "w") as f:
            f.write("\n".join(lines))

        # pickle version
        with open("layout_pickled_temp.dat", "wb") as f:
            pickle.dump(self.rom.currentLayout, f, -1)
        try:
            os.remove("layout_pickled.dat")
        except OSError:
            pass
        os.rename("layout_pickled_temp.dat", "layout_pickled.dat")

    def OnChangeDataSize(self, val):
        if 0 <= self.curSectionIdx < len(self.rom.currentLayout.sections):
            self.curSection.setParam("size", val)
            self.updateSectionGrid()

    def updateSectionGrid(self):
        sections = self.rom.currentLayout.sections
        self.sectionGrid.setRowCount(len(sections))
        for i, s in enumerate(sections):
            self.sectionGrid.setItem(i, 0, QTableWidgetItem(s.name))
            self.sectionGrid.setItem(i, 1, QTableWidgetItem(s.type))
            self.sectionGrid.setItem(i, 2, QTableWidgetItem(f"{s.start//0x10000:02x}:{s.start%0x10000:04x}"))
            self.sectionGrid.setItem(i, 3, QTableWidgetItem(f"{s.end//0x10000:02x}:{s.end%0x10000:04x}"))
        self.sectionGrid.resizeRowsToContents()
        self.updateSectionContents()

    def updateSectionContents(self):
        if 0 <= self.curSectionIdx < len(self.rom.currentLayout.sections):
            sect = self.curSection
            text = "\n".join(sect.getContentRepr(self.rom))
            self.sectionContentCtrl.SetContents(text)
            self.sizeCtrl.setValue(sect.params.get("size", 1))
            self.descCtrl.clear()
            desc = ""
            self.descCtrl.setPlainText(desc)

    curSection = property(lambda self: self.rom.currentLayout.sections[self.curSectionIdx])