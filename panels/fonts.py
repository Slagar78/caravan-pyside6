from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QTextEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import rompanel

h2i = lambda i: int(i, 16)

class FontPanel(rompanel.ROMPanel):

    frameTitle = "Font Editor"

    def init(self):

        self.font = None
        self.letter = " "
        self.palette = self.rom.getDataByName("palettes", "Sprite & UI Palette")
        self.mode = 0

        self.color_left = 1
        self.color_right = 0

        inst = QLabel("Edit font graphics.")
        inst.setWordWrap(True)

        leftSizer = QVBoxLayout()

        sbs1 = QGroupBox("1. Select a font.")
        sbs1_layout = QVBoxLayout(sbs1)

        self.fontList = QComboBox()
        self.fontList.addItems([f.name for f in self.rom.data["fonts"]])
        self.fontList.setCurrentIndex(0)
        sbs1_layout.addWidget(self.fontList)
        leftSizer.addWidget(sbs1)

        sbs2 = QGroupBox("2. Select a letter.")
        sbs2_layout = QGridLayout(sbs2)

        self.glyphPanels = []
        col = 0
        row = 0
        for g in self.rom.fontOrder:
            sp = rompanel.SpritePanel(self, None, 16, 15, self.palette, scale=2, func=self.OnChooseGlyph)
            sp.glyph = g
            self.glyphPanels.append(sp)
            sbs2_layout.addWidget(sp, row, col)
            col += 1
            if col >= 9:
                col = 0
                row += 1

        sbs3 = QGroupBox("3. Edit the letter.")
        sbs3_layout = QVBoxLayout(sbs3)

        text1 = QLabel("Left-Click to set, Right-Click to clear.")
        self.editPanel = rompanel.SpritePanel(self, None, 16, 15, self.palette, scale=12, func="edit")

        sbs3_layout.addWidget(text1, 0, Qt.AlignCenter)
        sbs3_layout.addWidget(self.editPanel, 1, Qt.AlignCenter)

        sbs4 = QGroupBox("Code")
        sbs4_layout = QVBoxLayout(sbs4)

        self.symbolsBox = QTextEdit()
        self.symbolsBox.setFixedHeight(42)
        self.symbolsBox.setReadOnly(True)
        self.symbolsBox.setStyleSheet("color: #B0B0B0;")
        sbs4_layout.addWidget(self.symbolsBox)

        # Layout
        self.sizer.addWidget(inst, 0, 0)
        self.sizer.addLayout(leftSizer, 1, 0)
        self.sizer.addWidget(sbs2, 1, 1)
        self.sizer.addWidget(sbs4, 2, 0, 1, 2)

        self.changeFont(0)
        self.changeEditGlyph(self.rom.fontOrder[0])

        self.fontList.currentIndexChanged.connect(self.OnSelectFont)

    def OnSelectFont(self, idx):
        self.changeFont(idx)

    def OnChooseGlyph(self, obj):
        self.changeEditGlyph(obj.glyph)

    def refreshPixels(self):
        idx = self.rom.fontOrder.index(self.letter)
        self.glyphPanels[idx].refreshSprite(self.font.glyphs[self.letter].pixels)
        self.glyphPanels[idx].update()
        self.font.glyphs[self.letter].recalculateWidth()
        self.symbolsBox.setPlainText(self.font.glyphs[self.letter].hexlify())

    def changeFont(self, key):
        self.font = self.rom.data["fonts"][key]
        for i, g in enumerate(self.rom.fontOrder):
            self.glyphPanels[i].refreshSprite(self.font.glyphs[g].pixels)

    def changeEditGlyph(self, glyph):
        self.letter = glyph
        realGlyph = self.font.glyphs[self.letter]
        self.editPanel.refreshSprite(realGlyph.pixels)
        self.editPanel.update()
        self.symbolsBox.setPlainText(realGlyph.hexlify())

    def getCurrentData(self):
        return self.font

    def getCurrentSpriteObject(self):
        return self.font.glyphs[self.letter]