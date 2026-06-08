import binascii
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QComboBox, QRadioButton, QListWidget,
    QFileDialog, QMessageBox, QDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage, QColor
import data
from PIL import Image
import rompanel

h2i = lambda i: int(i, 16)

class TilePanel(rompanel.ROMPanel):

    frameTitle = "Tileset Editor"

    def init(self):

        self.palette = self.rom.data["palettes"][0]
        self.mode = 0

        self.color_left = 0
        self.color_right = 0

        self.tileset = None
        self.tile = None
        self.curTile = 0

        # ---------- Группы ----------
        sbs1 = QGroupBox("Tools")
        sbs1_layout = QVBoxLayout(sbs1)

        sbs2 = QGroupBox("Maps using this tileset")
        sbs2_layout = QVBoxLayout(sbs2)

        sbs3 = QGroupBox("Tile block editor")
        sbs3_layout = QVBoxLayout(sbs3)

        sbs4 = QGroupBox("Edit")
        sbs4_layout = QHBoxLayout(sbs4)

        sbs5 = QGroupBox("Tileset")
        sbs5_layout = QVBoxLayout(sbs5)

        # ---------- Выбор тайлсета ----------
        tilesetLabel = QLabel("Tileset:")
        self.tilesetList = QComboBox()
        self.tilesetList.addItems([ts.name for ts in self.rom.data["tilesets"]])
        self.tilesetList.setCurrentIndex(0)

        # ---------- Карты, использующие тайлсет ----------
        self.mapList = QListWidget()
        self.mapList.setFixedSize(150, 80)
        sbs2_layout.addWidget(self.mapList)

        # ---------- Редактор отдельного тайла ----------
        text2 = QLabel("Tile (Color 0 = transparent)")
        self.editPanel = rompanel.SpritePanel(
            self, None, 8, 8, self.palette, scale=20, bg=16, func="edit"
        )

        # ---------- Цветовая палитра ----------
        text1 = QLabel("Colors")
        text3 = QLabel("Left-Click")
        text4 = QLabel("Right-Click")
        text5 = QLabel("Mode")
        text6 = QLabel("Palette")

        self.colorPanels = []
        for p in range(16):
            cp = rompanel.ColorPanel2(self, None, "#000000", num=p)
            self.colorPanels.append(cp)

        self.paletteList = QComboBox()
        self.paletteList.addItems([s.name for s in self.rom.data["palettes"]])
        self.paletteList.setCurrentIndex(0)

        sbs4left = QVBoxLayout()
        colorSizer = QGridLayout()
        for i, cp in enumerate(self.colorPanels):
            colorSizer.addWidget(cp, i // 2, i % 2)

        sbs4left.addWidget(text1, alignment=Qt.AlignCenter)
        sbs4left.addLayout(colorSizer)
        sbs4left.addWidget(text6, alignment=Qt.AlignCenter)

        sbs4mid = QVBoxLayout()
        sbs4mid.addWidget(text2, alignment=Qt.AlignCenter)
        sbs4mid.addWidget(self.editPanel, alignment=Qt.AlignCenter)
        sbs4mid.addWidget(self.paletteList, alignment=Qt.AlignCenter)

        sbs4right = QVBoxLayout()
        self.selectedColorLeft = rompanel.ColorPanel(self, None, "#000000", size=(40,40), enable=False)
        self.selectedColorRight = rompanel.ColorPanel(self, None, "#000000", size=(40,40), enable=False)
        self.selectedColorLeft.color = 0
        self.selectedColorRight.color = 0

        self.modePixel = QRadioButton("Pixel")
        self.modeFill = QRadioButton("Floodfill")
        self.modeReplace = QRadioButton("Replace")
        self.modePixel.setChecked(True)

        sbs4right.addWidget(text3, alignment=Qt.AlignCenter)
        sbs4right.addWidget(self.selectedColorLeft, alignment=Qt.AlignCenter)
        sbs4right.addWidget(text4, alignment=Qt.AlignCenter)
        sbs4right.addWidget(self.selectedColorRight, alignment=Qt.AlignCenter)
        sbs4right.addWidget(text5, alignment=Qt.AlignCenter)
        sbs4right.addWidget(self.modePixel)
        sbs4right.addWidget(self.modeFill)
        sbs4right.addWidget(self.modeReplace)

        sbs4_layout.addLayout(sbs4left, 0)
        sbs4_layout.addLayout(sbs4mid, 1)
        sbs4_layout.addLayout(sbs4right, 0)

        # ---------- Блок 3x3 (предпросмотр) ----------
        tps = QGridLayout()
        self.tilePanels = []
        for p in range(9):
            tp = rompanel.SpritePanel(
                self, None, 8, 8, self.palette, scale=4, bg=16,
                func=self.OnChangeLayoutTile, edit=True
            )
            tp.num = 0
            self.tilePanels.append(tp)
            tps.addWidget(tp, p // 3, p % 3)

        sbs3_layout.addLayout(tps)

        # ---------- Импорт / Экспорт ----------
        self.importButton = QPushButton("Import")
        self.exportButton = QPushButton("Export")
        sbs1_layout.addWidget(self.importButton, alignment=Qt.AlignCenter)
        sbs1_layout.addWidget(self.exportButton, alignment=Qt.AlignCenter)

        # ---------- Панель всего тайлсета ----------
        self.tilesetPanel = rompanel.SpritePanel(
            self, None, 8*16, 8*8, self.palette, scale=3, bg=16,
            func=self.OnClickTilesetPanel, edit=True, grid=8
        )
        sbs5_layout.addWidget(self.tilesetPanel)

        # ---------- Главный layout ----------
        topSizer = QHBoxLayout()
        topLeftSizer = QVBoxLayout()
        tilesetSelectSizer = QHBoxLayout()
        tilesetSelectSizer.addWidget(tilesetLabel)
        tilesetSelectSizer.addWidget(self.tilesetList)
        topLeftSizer.addLayout(tilesetSelectSizer)
        topLeftSizer.addWidget(sbs2)

        topSizer.addLayout(topLeftSizer)
        topSizer.addWidget(sbs4)

        bottomSizer = QHBoxLayout()
        bottomSizer.addWidget(sbs3)
        bottomSizer.addWidget(sbs5)
        bottomSizer.addWidget(sbs1)

        self.sizer.addLayout(topSizer, 0, 0)
        self.sizer.addLayout(bottomSizer, 1, 0)

        # ---------- Сигналы ----------
        self.tilesetList.currentIndexChanged.connect(self.OnSelectTileset)
        self.paletteList.currentIndexChanged.connect(self.OnSelectPalette)
        self.importButton.clicked.connect(self.OnImportImage)
        self.exportButton.clicked.connect(self.OnExportImage)
        self.modePixel.toggled.connect(self.OnSelectMode)
        self.modeFill.toggled.connect(self.OnSelectMode)
        self.modeReplace.toggled.connect(self.OnSelectMode)

        # Начальная загрузка
        self.changeTileset(0)
        self.changeColors()

    def OnShow(self):
        for p in range(16):
            self.colorPanels[p].setStyleSheet(f"background-color: {self.palette.colors[p]};")
            self.colorPanels[p].update()
        self.selectedColorLeft.setStyleSheet(f"background-color: {self.palette.colors[self.color_left]};")
        self.selectedColorRight.setStyleSheet(f"background-color: {self.palette.colors[self.color_right]};")

    def OnImportImage(self):
        size = self.tilesetPanel.bmp.size()
        w, h = size.width(), size.height()
        dlg = QFileDialog(self, f"Import 16-color {w}x{h} GIF", "", "GIF files (*.gif)")
        dlg.setFileMode(QFileDialog.ExistingFile)
        if dlg.exec() == QDialog.Accepted:
            fn = dlg.selectedFiles()[0]
            try:
                img = Image.open(fn)
                imgw, imgh = img.size
                imgpal = img.getpalette()
                if img.size != (w, h):
                    QMessageBox.warning(self, f"{fn} is {imgw}x{imgh} and should be {w}x{h}.",
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
                    self.tileset.palette = pal
                    imgdata = list(img.getdata())
                    pixels = "".join(["%x" % d for d in imgdata])
                    pixels = [pixels[i:i+w] for i in range(0, w*h, w)]
                    self.tileset.convertFromPixelRows(pixels)
                    newtiles = [None]*len(self.tileset.tiles)
                    order = self.tileset.getTileOrder(imgw//8, imgh//8)
                    for i in range(len(newtiles)):
                        newtiles[order[i]] = self.tileset.tiles[i]
                    self.tileset.tiles = newtiles
                    self.changeTileset()
                    self.changeColors()
                    self.modify()
                del img
            except IOError:
                QMessageBox.warning(self, f"{fn} is not a GIF or is improperly formatted.",
                                    self.parent.baseTitle + " -- Error")

    def OnExportImage(self):
        size = self.tilesetPanel.bmp.size()
        w, h = size.width(), size.height()
        dlg = QFileDialog(self, f"Export 16-color {w}x{h} GIF", "", "GIF files (*.gif)")
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        if dlg.exec() == QDialog.Accepted:
            fn = dlg.selectedFiles()[0]
            img = Image.new("P", (w, h))
            img.putdata([int(a, 16) for pr in self.tilesetPanel.pixels for a in pr])
            p = [v for rt in self.editPanel.palette.rgbaTuples() for v in rt[:3]]
            p += [0] * (768 - len(p))
            img.putpalette(p)
            img.save(fn, "GIF")

    def changeColors(self):
        palette = self.palette
        for c in range(len(self.colorPanels)):
            self.colorPanels[c].setStyleSheet(f"background-color: {palette.colors[c]};")
            self.colorPanels[c].update()
        self.editPanel.palette = palette
        self.editPanel.update()
        for tp in self.tilePanels:
            tp.palette = palette
        self.tilesetPanel.palette = palette
        self.refreshPixels()

    def changeEditColor(self, button, num):
        if button == 0:
            self.color_left = num
            self.selectedColorLeft.color = num
            self.selectedColorLeft.setStyleSheet(f"background-color: {self.palette.colors[num]};")
        else:
            self.color_right = num
            self.selectedColorRight.color = num
            self.selectedColorRight.setStyleSheet(f"background-color: {self.palette.colors[num]};")

    def refreshPixels(self):
        for p in range(9):
            tp = self.tilePanels[p]
            tp.refreshSprite(self.tileset.tiles[tp.num].pixels)
            tp.update()

        self.tilesetPanel.pixels = []
        for tRow in range(8):
            for pRow in range(8):
                row = "".join([self.tileset.tiles[tRow*16+to].pixels[pRow] for to in range(16)])
                self.tilesetPanel.pixels.append(row)

        self.tilesetPanel.refreshSprite()
        self.tilesetPanel.update()

    def OnSelectPalette(self, idx):
        self.palette = self.rom.data["palettes"][idx]
        self.changeColors()
        self.changeEditColor(0, self.color_left)
        self.changeEditColor(1, self.color_right)
        self.refreshPixels()

    def OnClickTilesetPanel(self, obj):
        x = int(obj.mouseX // 8 // obj.scale)
        y = int(obj.mouseY // 8 // obj.scale)
        self.changeTile(y*16 + x)
        self.refreshPixels()

    def OnSelectMode(self, checked):
        if self.modePixel.isChecked():
            self.mode = 0
        elif self.modeFill.isChecked():
            self.mode = 1
        elif self.modeReplace.isChecked():
            self.mode = 2

    def OnSelectTileset(self, idx):
        self.changeTileset(idx)

    def OnChangeLayoutTile(self, obj):
        obj.refreshSprite(self.tile.pixels)
        obj.num = self.curTile
        obj.update()

    def changeTileset(self, num=None):
        if num is not None:
            if not self.rom.data["tilesets"][num].loaded:
                self.rom.getTilesets(num, num)
            self.tileset = self.rom.data["tilesets"][num]
            self.mapList.clear()
            mapsUsing = [m.name for m in self.rom.data["maps"] if num in m.tilesetIdxes]
            self.mapList.addItems(mapsUsing)
            for p in range(9):
                tp = self.tilePanels[p]
                tp.num = 0
                tp.update()

        pixels = []
        tw = self.tilesetPanel.width // 8
        th = self.tilesetPanel.height // 8

        order = self.tileset.getTileOrder(tw, th)
        tiles = [self.tileset.tiles[t] for t in order]

        for tRow in range(th):
            for pRow in range(8):
                row = "".join([tiles[tRow*tw+to].pixels[pRow] for to in range(tw)])
                pixels.append(row)
        self.tilesetPanel.refreshSprite(pixels, force=True)

        self.updateModifiedIndicator(self.tileset.modified)
        self.changeTile()

    def changeTile(self, num=0):
        self.curTile = num
        self.tile = self.tileset.tiles[num]
        self.editPanel.refreshSprite(self.tile.pixels)
        self.editPanel.update()
        self.refreshPixels()

    def getCurrentSpriteObject(self):
        return self.tile

    def getCurrentData(self):
        return self.tileset

    changeSelection = changeTileset