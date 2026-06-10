from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QTextEdit
)
from PySide6.QtCore import Qt
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

        # Инструкция
        inst = QLabel("Edit font graphics.")
        inst.setWordWrap(True)

        # Левая колонка (выбор шрифта + редактор буквы)
        leftSizer = QVBoxLayout()
        leftSizer.setSpacing(8)

        # 1. Select font
        sbs1 = QGroupBox("1. Select a font.")
        sbs1_layout = QVBoxLayout(sbs1)
        self.fontList = QComboBox()
        self.fontList.addItems([f.name for f in self.rom.data["fonts"]])
        self.fontList.setCurrentIndex(0)
        sbs1_layout.addWidget(self.fontList)
        leftSizer.addWidget(sbs1)

        # 3. Edit the letter
        sbs3 = QGroupBox("3. Edit the letter.")
        sbs3_layout = QVBoxLayout(sbs3)
        text1 = QLabel("Left-Click to set, Right-Click to clear.")
        text1.setAlignment(Qt.AlignCenter)
        self.editPanel = rompanel.SpritePanel(
            self, None, 16, 15, self.palette,
            scale=12, func="edit"
        )
        sbs3_layout.addWidget(text1)
        sbs3_layout.addWidget(self.editPanel, stretch=1, alignment=Qt.AlignCenter)
        leftSizer.addWidget(sbs3)

        # 2. Select a letter
        sbs2 = QGroupBox("2. Select a letter.")
        sbs2_layout = QGridLayout(sbs2)
        sbs2_layout.setSpacing(2)
        sbs2_layout.setContentsMargins(8, 8, 8, 8)

        self.glyphPanels = []
        col = row = 0
        for g in self.rom.fontOrder:
            sp = rompanel.SpritePanel(
                self, None, 16, 15, self.palette,
                scale=2
            )
            sp.glyph = g
            # Подключаем клик через атрибут func, который ожидает rompanel.SpritePanel
            sp.func = lambda event, p=sp: self.OnChooseGlyph(p)
            self.glyphPanels.append(sp)
            sbs2_layout.addWidget(sp, row, col)
            col += 1
            if col >= 9:
                col = 0
                row += 1

        # Code box
        sbs4 = QGroupBox("Code")
        sbs4_layout = QVBoxLayout(sbs4)
        self.symbolsBox = QTextEdit()
        self.symbolsBox.setFixedHeight(70)
        self.symbolsBox.setReadOnly(True)
        self.symbolsBox.setStyleSheet(
            "color: #B0B0B0; background-color: #1E1E1E; font-family: Courier New;"
        )
        sbs4_layout.addWidget(self.symbolsBox)

        self.sizer.addWidget(inst, 0, 0, 1, 2, Qt.AlignLeft)
        self.sizer.addLayout(leftSizer, 1, 0)
        self.sizer.addWidget(sbs2, 1, 1)
        self.sizer.addWidget(sbs4, 2, 0, 1, 2)

        self.changeFont(0)
        if self.rom.fontOrder:
            self.changeEditGlyph(self.rom.fontOrder[0])

        self.fontList.currentIndexChanged.connect(self.OnSelectFont)

    # === Обработчики ===
    def OnSelectFont(self, idx):
        self.changeFont(idx)

    def OnChooseGlyph(self, panel):
        """Принимает объект SpritePanel"""
        self.changeEditGlyph(panel.glyph)

    def refreshPixels(self):
        """Вызывается при изменении пикселей редактируемого глифа"""
        if not self.font or self.letter not in self.font.glyphs:
            return
        try:
            idx = self.rom.fontOrder.index(self.letter)
            self.glyphPanels[idx].refreshSprite(self.font.glyphs[self.letter].pixels)
            self.glyphPanels[idx].update()
            self.font.glyphs[self.letter].recalculateWidth()
            self.symbolsBox.setPlainText(self.font.glyphs[self.letter].hexlify())
        except Exception as e:
            print("refreshPixels error:", e)

    def changeFont(self, key):
        self.font = self.rom.data["fonts"][key]
        for i, g in enumerate(self.rom.fontOrder):
            if i < len(self.glyphPanels):
                self.glyphPanels[i].refreshSprite(self.font.glyphs[g].pixels)
                self.glyphPanels[i].update()

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