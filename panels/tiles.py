import binascii
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QComboBox, QRadioButton, QListWidget,
    QScrollArea, QFileDialog, QMessageBox, QAbstractItemView
)
from PySide6.QtCore import Qt, QTimer
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
        
        leftSizer = QVBoxLayout()
        
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
        
        # Maps list
        self.mapList = QListWidget()
        self.mapList.setFixedSize(150, 80)
        sbs2_layout.addWidget(self.mapList)
        
        # Colors + palette
        text1 = QLabel("Colors")
        text2 = QLabel("Tile (Color 0 = trans)")
        text3 = QLabel("Left-Click")
        text4 = QLabel("Right-Click")
        text5 = QLabel("Mode")
        text6 = QLabel("Palette")
        
        self.editPanel = rompanel.SpritePanel(self, None, 8, 8, self.palette, scale=20, bg=16, func="edit")
        
        self.colorPanels = []
        for p in range(16):
            self.colorPanels.append(rompanel.ColorPanel2(self, None, "#000000", num=p))
        
        self.paletteList = QComboBox()
        self.paletteList.addItems([s.name for s in self.rom.data["palettes"]])
        self.paletteList.setCurrentIndex(0)
        
        sbs4left = QVBoxLayout()
        colorSizer = QGridLayout()
        for i, cp in enumerate(self.colorPanels):
            colorSizer.addWidget(cp, i // 2, i % 2)
        
        sbs4left.addWidget(text1, 0, Qt.AlignCenter)
        sbs4left.addLayout(colorSizer)
        sbs4left.addWidget(text6, 0, Qt.AlignCenter)
        
        sbs4mid = QVBoxLayout()
        sbs4mid.addWidget(text2, 0, Qt.AlignCenter)
        sbs4mid.addWidget(self.editPanel, 0, Qt.AlignCenter)
        sbs4mid.addWidget(self.paletteList, 0, Qt.AlignCenter)
        
        sbs4right = QVBoxLayout()
        self.selectedColorLeft = rompanel.ColorPanel(self, None, "#000000", size=(40,40))
        self.selectedColorRight = rompanel.ColorPanel(self, None, "#000000", size=(40,40))
        self.selectedColorLeft.color = 0
        self.selectedColorRight.color = 0

        self.modePixel = QRadioButton("Pixel")
        self.modeFill = QRadioButton("Floodfill")
        self.modeReplace = QRadioButton("Replace")
        self.modePixel.setChecked(True)
        
        sbs4right.addWidget(text3, 0, Qt.AlignCenter)
        sbs4right.addWidget(self.selectedColorLeft, 0, Qt.AlignCenter)
        sbs4right.addWidget(text4, 0, Qt.AlignCenter)
        sbs4right.addWidget(self.selectedColorRight, 0, Qt.AlignCenter)
        sbs4right.addWidget(text5, 0, Qt.AlignCenter)
        sbs4right.addWidget(self.modePixel, 0, Qt.AlignLeft)
        sbs4right.addWidget(self.modeFill, 0, Qt.AlignLeft)
        sbs4right.addWidget(self.modeReplace, 0, Qt.AlignLeft)
        
        sbs4_layout.addLayout(sbs4left, 0)
        sbs4_layout.addLayout(sbs4mid, 1)
        sbs4_layout.addLayout(sbs4right, 0)
        
        # Tile block editor (3x3 grid)
        tps = QGridLayout()
        self.tilePanels = []
        for p in range(9):
            tp = rompanel.SpritePanel(self, None, 8, 8, self.palette, scale=4, bg=16, func=self.OnChangeLayoutTile)
            tp.num = 0
            self.tilePanels.append(tp)
            tps.addWidget(tp, p // 3, p % 3)
        
        sbs3_layout.addLayout(tps)
        
        # Import/Export buttons
        self.importButton = QPushButton("Import")
        self.importButton.setFixedSize(40, 20)
        self.exportButton = QPushButton("Export")
        self.exportButton.setFixedSize(40, 20)
        sbs1_layout.addWidget(self.importButton, 0, Qt.AlignCenter)
        sbs1_layout.addWidget(self.exportButton, 0, Qt.AlignCenter)
        
        # Tileset panel
        self.tilesetPanel = rompanel.SpritePanel(self, None, 8*16, 8*8, self.palette, scale=3, bg=16, func=self.OnClickTilesetPanel, grid=8)
        sbs5_layout.addWidget(self.tilesetPanel)
        
        # Layout
        topSizer = QHBoxLayout()
        topLeftSizer = QVBoxLayout()
        topLeftSizer.addWidget(sbs2)
        
        topSizer.addLayout(topLeftSizer)
        topSizer.addWidget(sbs4)
        
        bottomSizer = QHBoxLayout()
        bottomSizer.addWidget(sbs3)
        bottomSizer.addWidget(sbs5)
        bottomSizer.addWidget(sbs1)
        
        self.sizer.addLayout(topSizer, 0, 0)
        self.sizer.addLayout(bottomSizer, 1, 0)
        
        self.changeTileset(0)
        self.changeColors()
        
        # Connections
        self.paletteList.currentIndexChanged.connect(self.OnSelectPalette)
        self.importButton.clicked.connect(self.OnImportImage)
        self.exportButton.clicked.connect(self.OnExportImage)
        self.modePixel.toggled.connect(self.OnSelectMode)
        self.modeFill.toggled.connect(self.OnSelectMode)
        self.modeReplace.toggled.connect(self.OnSelectMode)

    def OnShow(self):
        for p in range(16):
            self.colorPanels[p].setStyleSheet(f"background-color: {self.palette.colors[p]};")
            self.colorPanels[p].update()
        self.selectedColorLeft.setStyleSheet(f"background-color: {self.palette.colors[self.color_left]};")
        self.selectedColorRight.setStyleSheet(f"background-color: {self.palette.colors[self.color_right]};")

    def OnImportImage(self):
        size = self.tilesetPanel.bmp.GetSize()
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
                    QMessageBox.warning(self, f"{fn} is {imgw}x{imgh} and should be {w}x{h}.", self.parent.baseTitle + " -- Error")
                elif img.format != "GIF" or imgpal is None:
                    QMessageBox.warning(self, f"{fn} is not a GIF or is improperly formatted.", self.parent.baseTitle + " -- Error")
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
                QMessageBox.warning(self, f"{fn} is not a GIF or is improperly formatted.", self.parent.baseTitle + " -- Error")

    def OnExportImage(self):
        size = self.tilesetPanel.bmp.GetSize()
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
        else:
            self.color_right = num
        if button == 0:
            self.selectedColorLeft.color = num
            self.selectedColorLeft.setStyleSheet(f"background-color: {self.palette.colors[num]};")
        else:
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

    def OnEditTile(self, evt):
        obj = self.sender()
        obj.OnEdit(evt)  # делегируем стандартный обработчик SpritePanel

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
        # obj – это SpritePanel, на которую кликнули
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

        print(tw, th)
        print(len(self.tileset.tiles))

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