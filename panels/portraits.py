import binascii
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QComboBox, QFileDialog, QMessageBox,
    QDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage, QColor
import data
from PIL import Image
import rompanel
import shiboken6

h2i = lambda i: int(i, 16)

class PortraitPanel(rompanel.ROMPanel):

    frameTitle = "Portrait Editor"

    def init(self):
        if self.rom is None:
            return

        self.palette = self.rom.getDataByName("palettes", "Sprite & UI Palette")
        self.side = 0
        self.frame = 0
        self.mode = 0

        self.color_left = 0
        self.color_right = 0

        self.curFrameIdx = 0
        self.curPaletteIdx = 0

        # ---------- Выбор портрета ----------
        sbs1 = QGroupBox("1. Select a portrait.")
        sbs1_layout = QVBoxLayout(sbs1)
        self.portraitList = QComboBox()
        self.portraitList.addItems([bs.name for bs in self.rom.data["portraits"]])
        self.portraitList.setCurrentIndex(0)
        self.portraitList.currentIndexChanged.connect(self.OnSelectPortrait)
        sbs1_layout.addWidget(self.portraitList)

        # ---------- Edit ----------
        sbs4_widget = QWidget()
        sbs4 = QHBoxLayout()               # В оригинале wx.HORIZONTAL
        sbs4_widget.setLayout(sbs4)
        sbs4_widget.setStyleSheet("border: 1px solid black;")

        # Левая часть: цвета и кнопки импорта/экспорта
        sbs4left = QVBoxLayout()
        text1 = QLabel("Colors")
        self.colorPanels = []
        for p in range(16):
            cp = rompanel.ColorPanel2(self, None, "#000000", num=p)
            self.colorPanels.append(cp)
        self.changeColors()
        self.importButton = QPushButton("Import")
        self.importButton.setFixedSize(40, 20)
        self.exportButton = QPushButton("Export")
        self.exportButton.setFixedSize(40, 20)

        colorSizer = QGridLayout()
        for i, cp in enumerate(self.colorPanels):
            colorSizer.addWidget(cp, i // 2, i % 2)
        sbs4left.addWidget(text1, 0, Qt.AlignCenter)
        sbs4left.addLayout(colorSizer)
        sbs4left.addWidget(self.importButton, 0, Qt.AlignCenter)
        sbs4left.addWidget(self.exportButton, 0, Qt.AlignCenter)

        # Центральная часть: спрайт
        sbs4mid = QVBoxLayout()
        text2 = QLabel("Sprite (Color 0 = trans)")
        self.editPanel = rompanel.SpritePanel(sbs4_widget, None, 64, 64, self.palette, scale=3, bg=16)
        sbs4mid.addWidget(text2, 0, Qt.AlignCenter)
        sbs4mid.addWidget(self.editPanel, 0, Qt.AlignCenter)

        # Правая панель в оригинале полностью закомментирована — не добавляем

        sbs4.addLayout(sbs4left, 0)
        sbs4.addLayout(sbs4mid, 1)

        # ---------- Главный лейаут ----------
        self.sizer.addWidget(sbs1, 0, 0, 1, 2)
        self.sizer.addWidget(sbs4_widget, 1, 0, 1, 2)

        # Инициализация
        self.changePortrait(0)

        # Сигналы
        self.importButton.clicked.connect(self.OnImportImage)
        self.exportButton.clicked.connect(self.OnExportImage)

        self.printed = False

    # ====== Методы ======
    def OnImportImage(self):
        if not shiboken6.isValid(self.editPanel) or self.rom is None:
            return
        size = self.editPanel.bmp.size()
        width, height = size.width(), size.height()
        dlg = QFileDialog(self, f"Import 16-color {width}x{height} GIF", "", "GIF files (*.gif)")
        dlg.setFileMode(QFileDialog.ExistingFile)
        if dlg.exec() == QDialog.Accepted:
            fn = dlg.selectedFiles()[0]
            try:
                img = Image.open(fn)
                imgw, imgh = img.size
                imgpal = img.getpalette()
                if img.size != (width, height):
                    QMessageBox.warning(self, f"{fn} is {imgw}x{imgh} and should be {width}x{height}.",
                                        self.parent.baseTitle + " -- Error")
                elif img.format != "GIF" or imgpal is None:
                    QMessageBox.warning(self, f"{fn} is not a GIF or is improperly formatted.",
                                        self.parent.baseTitle + " -- Error")
                else:
                    cols = ["#%02x%02x%02x" % (imgpal[i]//16*17, imgpal[i+1]//16*17, imgpal[i+2]//16*17) for i in range(0, 48, 3)]
                    pal = data.Palette()
                    pal.init(cols)
                    self.editPanel.palette = pal
                    self.palette = pal
                    self.portrait.palette = pal
                    imgdata = list(img.getdata())
                    pixels = "".join(["%x" % d for d in imgdata])
                    pixels = [pixels[i:i+width] for i in range(0, width*height, width)]
                    self.curFrame.convertFromPixelRows(pixels)
                    newtiles = [None]*len(self.curFrame.tiles)
                    order = self.curFrame.getTileOrder(imgw//8, imgh//8)
                    for i in range(len(newtiles)):
                        newtiles[order[i]] = self.curFrame.tiles[i]
                    self.curFrame.tiles = newtiles
                    self.changePortrait()
                    self.changeColors()
                    self.modify()
                del img
            except IOError:
                QMessageBox.warning(self, f"{fn} is not a GIF or is improperly formatted.",
                                    self.parent.baseTitle + " -- Error")

    def OnExportImage(self):
        if not shiboken6.isValid(self.editPanel):
            return
        size = self.editPanel.bmp.size()
        width, height = size.width(), size.height()
        dlg = QFileDialog(self, f"Export 16-color {width}x{height} GIF", "", "GIF files (*.gif)")
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        if dlg.exec() == QDialog.Accepted:
            fn = dlg.selectedFiles()[0]
            img = Image.new("P", (width, height))
            img.putdata([int(a, 16) for pr in self.editPanel.pixels for a in pr])
            p = [v for rt in self.editPanel.palette.rgbaTuples() for v in rt[:3]]
            p += [0] * (768 - len(p))
            img.putpalette(p)
            img.save(fn, "GIF")

    def OnShow(self, event=None):
        if self.rom is None:
            return
        for p in range(16):
            if shiboken6.isValid(self.colorPanels[p]):
                self.colorPanels[p].setStyleSheet(f"background-color: {self.palette.colors[p]};")
                self.colorPanels[p].update()

    def changeColors(self):
        palette = self.palette
        for c in range(len(self.colorPanels)):
            if shiboken6.isValid(self.colorPanels[c]):
                self.colorPanels[c].setStyleSheet(f"background-color: {palette.colors[c]};")
                self.colorPanels[c].update()

    def OnSelectPalette(self, idx):
        self.curPaletteIdx = idx
        self.changePortrait()

    def OnSelectFrame(self, idx):
        self.curFrameIdx = idx
        self.changePortrait()

    def changeEditColor(self, button, num):
        # В оригинале метод оставлен пустым
        pass

    def refreshPixels(self):
        # Заглушка, как в оригинале
        pass

    def OnChangeAnim(self, button_id):
        pass

    def OnSelectMode(self, checked):
        # Режим всегда пиксельный, как в оригинале без радиокнопок
        self.mode = 0

    def OnSelectPortrait(self, idx):
        self.changePortrait(idx)

    def OnSwitchFrame(self):
        self.frame ^= 1
        self.changePortrait(self.portraitList.currentIndex())

    def changePortrait(self, num=None):
        if num is not None:
            if not self.rom.data["portraits"][num].loaded:
                self.rom.getPortraits(num, num)
            self.curPaletteIdx = 0
            self.curFrameIdx = 0
            self.portrait = self.rom.data["portraits"][num]
            self.editPanel.width = 64
            self.editPanel.height = 64
        self.palette = self.curPalette
        self.editPanel.palette = self.palette
        self.changeColors()
        # Получаем пиксели для отображения
        tw = self.editPanel.width // 8
        th = self.editPanel.height // 8
        order = self.curFrame.getTileOrder(tw, th)
        tiles = [self.curFrame.tiles[t] for t in order]
        pixels = []
        for tRow in range(th):
            for pRow in range(8):
                row = "".join([tiles[tRow*tw+to].pixels[pRow] for to in range(tw)])
                pixels.append(row)
        self.editPanel.refreshSprite(pixels, force=True)
        self.updateModifiedIndicator(self.portrait.modified)
        self.editPanel.update()
        self.refreshPixels()

    def getCurrentSpriteObject(self):
        return self.portrait

    def getCurrentData(self):
        return self.portrait

    changeSelection = changePortrait

    curFrame = property(lambda self: self.portrait.frame)
    curPalette = property(lambda self: self.portrait.palette)