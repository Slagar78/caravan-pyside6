import binascii
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QComboBox, QFileDialog, QMessageBox, QDialog
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage, QColor
import data
from PIL import Image
import rompanel
import shiboken6

h2i = lambda i: int(i, 16)

class WeaponSpritePanel(rompanel.ROMPanel):

    frameTitle = "Weapon Sprite Editor"

    def init(self):
        self.palette = self.rom.getDataByName("palettes", "Sprite & UI Palette")
        self.side = 0
        self.frame = 0
        self.mode = 0
        self.color_left = 0
        self.color_right = 0
        self.curFrameIdx = 0
        self.curPaletteIdx = 0

        # ---------- Выпадающий список оружия ----------
        weaponLabel = QLabel("Weapon Sprite:")
        self.weaponSpriteList = QComboBox()
        self.weaponSpriteList.addItems([bs.name for bs in self.rom.data["weapon_sprites"]])
        self.weaponSpriteList.setCurrentIndex(0)

        # ---------- Группы ----------
        sbs3 = QGroupBox("Palette and Frame")
        sbs3_layout = QVBoxLayout(sbs3)

        sbs4 = QGroupBox("Edit")
        sbs4_layout = QHBoxLayout(sbs4)

        self.frameList = QComboBox()
        self.frameList.setFixedWidth(100)
        self.paletteList = QComboBox()
        self.paletteList.setFixedWidth(100)

        sbs3_layout.addWidget(self.frameList, 0, Qt.AlignLeft)
        sbs3_layout.addWidget(self.paletteList, 0, Qt.AlignLeft)

        text1 = QLabel("Colors")
        text2 = QLabel("Sprite (Color 0 = transparent)")

        self.editPanel = rompanel.SpritePanel(self, None, 8*8, 8*8, self.palette, scale=3, bg=16, func="edit")

        self.colorPanels = []
        for p in range(16):
            self.colorPanels.append(rompanel.ColorPanel2(self, None, "#000000", num=p))

        self.changeColors()

        self.importButton = QPushButton("Import")
        self.importButton.setFixedSize(40, 20)
        self.importButton.setEnabled(False)
        self.exportButton = QPushButton("Export")
        self.exportButton.setFixedSize(40, 20)

        sbs4left = QVBoxLayout()
        colorSizer = QGridLayout()
        for i, cp in enumerate(self.colorPanels):
            colorSizer.addWidget(cp, i // 2, i % 2)

        sbs4left.addWidget(text1, 0, Qt.AlignCenter)
        sbs4left.addLayout(colorSizer)
        sbs4left.addWidget(self.importButton, 0, Qt.AlignCenter)
        sbs4left.addWidget(self.exportButton, 0, Qt.AlignCenter)

        sbs4mid = QVBoxLayout()
        sbs4mid.addWidget(text2, 0, Qt.AlignCenter)
        sbs4mid.addWidget(self.editPanel, 0, Qt.AlignCenter)

        sbs4_layout.addLayout(sbs4left, 0)
        sbs4_layout.addLayout(sbs4mid, 1)

        # Компоновка с исправленной ошибкой лейаута
        topSizer = QHBoxLayout()
        topLeftSizer = QVBoxLayout()
        topLeftSizer.addWidget(weaponLabel)
        topLeftSizer.addWidget(self.weaponSpriteList)
        topLeftSizer.addWidget(sbs3)

        topSizer.addLayout(topLeftSizer)
        topSizer.addWidget(sbs4, 1)   # добавляем сам виджет, а не его лейаут!

        self.sizer.addLayout(topSizer, 0, 0, 1, 2)

        # Таймер анимации (как в оригинале)
        self.animFrame = 0
        self.animCur = 0
        self.animDelays = [250, 150, 50, 50, 50, 50]
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.TimerTest)
        self.timer.start(self.animDelays[0])

        self.changeWeaponSprite(0)

        self.weaponSpriteList.currentIndexChanged.connect(self.OnSelectWeaponSprite)
        self.paletteList.currentIndexChanged.connect(self.OnSelectPalette)
        self.frameList.currentIndexChanged.connect(self.OnSelectFrame)
        self.importButton.clicked.connect(self.OnImportImage)
        self.exportButton.clicked.connect(self.OnExportImage)

    # ---------- Все методы оригинала ----------
    def printrb(self):
        rb = self.curFrame.raw_bytes.split("\n")
        hx = self.curFrame.hexlify().split("\n")
        for i in range(max(len(rb), len(hx))):
            line1 = rb[i] if i < len(rb) else "No line"
            line2 = hx[i] if i < len(hx) else "No line"
            if line1 and line2:
                print("Different!!!" if line1 != line2 else "Same")
            print(line1)
            print(line2)
            print()

    def OnImportImage(self):
        if not shiboken6.isValid(self.editPanel):
            return
        size = self.editPanel.bmp.size()
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
                    self.weaponSprite.palettes[self.curPaletteIdx] = pal
                    imgdata = list(img.getdata())
                    pixels = "".join(["%x" % d for d in imgdata])
                    pixels = [pixels[i:i+w] for i in range(0, w*h, w)]
                    self.curFrame.convertFromPixelRows(pixels)
                    newtiles = [None]*len(self.curFrame.tiles)
                    order = self.curFrame.getTileOrder(imgw//8, imgh//8)
                    for i in range(len(newtiles)):
                        newtiles[order[i]] = self.curFrame.tiles[i]
                    self.curFrame.tiles = newtiles
                    self.changeWeaponSprite()
                    self.changeColors()
                    self.modify()
                del img
            except IOError:
                QMessageBox.warning(self, f"{fn} is not a GIF or is improperly formatted.", self.parent.baseTitle + " -- Error")

    def OnExportImage(self):
        if not shiboken6.isValid(self.editPanel):
            return
        size = self.editPanel.bmp.size()
        w, h = size.width(), size.height()
        dlg = QFileDialog(self, f"Export 16-color {w}x{h} GIF", "", "GIF files (*.gif)")
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        if dlg.exec() == QDialog.Accepted:
            fn = dlg.selectedFiles()[0]
            img = Image.new("P", (w, h))
            img.putdata([int(a, 16) for pr in self.editPanel.pixels for a in pr])
            p = [v for rt in self.editPanel.palette.rgbaTuples() for v in rt[:3]]
            p += [0] * (768 - len(p))
            img.putpalette(p)
            img.save(fn, "GIF")

    def TimerTest(self):
        self.animFrame ^= 1

    def changeColors(self):
        palette = self.palette
        for c in range(len(self.colorPanels)):
            cp = self.colorPanels[c]
            if shiboken6.isValid(cp):
                cp.setStyleSheet(f"background-color: {palette.colors[c]};")
                cp.update()

    def OnSelectPalette(self, idx):
        self.curPaletteIdx = idx
        self.changeWeaponSprite()

    def OnSelectFrame(self, idx):
        self.curFrameIdx = idx
        self.changeWeaponSprite()

    def changeEditColor(self, button, num):
        if button == 0:
            self.color_left = num
        else:
            self.color_right = num

    def refreshPixels(self):
        pass

    def OnChangeAnim(self, button_id):
        pass

    def OnSelectMode(self, mode_id):
        pass

    def OnSelectWeaponSprite(self, idx):
        self.changeWeaponSprite(idx)

    def OnSwitchFrame(self):
        self.frame ^= 1
        self.changeWeaponSprite(self.weaponSpriteList.currentIndex())

    def changeWeaponSprite(self, num=None):
        if num is not None:
            if not self.rom.data["weapon_sprites"][num].loaded:
                self.rom.getWeaponSprites(num, num)
            self.curPaletteIdx = 0
            self.curFrameIdx = 0
            self.weaponSprite = self.rom.data["weapon_sprites"][num]
            self.editPanel.width = 64
            self.editPanel.height = 64
            self.frameList.clear()
            self.frameList.addItems(["Frame %i" % i for i,p in enumerate(self.weaponSprite.frames)])
            self.frameList.setCurrentIndex(self.curFrameIdx)
            self.paletteList.clear()
            self.paletteList.addItems(["Palette %i" % i for i,p in enumerate(self.weaponSprite.palettes)])
            self.paletteList.setCurrentIndex(self.curPaletteIdx)

        if not hasattr(self, 'weaponSprite') or self.weaponSprite is None:
            return

        self.palette = self.curPalette
        if shiboken6.isValid(self.editPanel):
            self.editPanel.palette = self.palette
        self.changeColors()

        frame = self.weaponSprite.frames[self.curFrameIdx]
        if not frame or not frame.tiles:
            return

        pixels = []
        tw = self.editPanel.width // 8
        th = self.editPanel.height // 8
        order = frame.getTileOrder(tw, th)
        tiles = [frame.tiles[t] for t in order]
        for tRow in range(th):
            for pRow in range(8):
                row = "".join([tiles[tRow*tw+to].pixels[pRow] for to in range(tw)])
                pixels.append(row)

        if shiboken6.isValid(self.editPanel):
            self.editPanel.refreshSprite(pixels, force=True)
            self.updateModifiedIndicator(self.weaponSprite.modified)
            self.editPanel.update()
        self.refreshPixels()

    def changeAnim(self, num):
        self.animCur = num
        self.timer.start(self.animDelays[num])

    def changeAnimWeaponSprite(self):
        if shiboken6.isValid(self.animPanel):
            if self.animFrame == 0:
                self.animPanel.refreshSprite(self.curFrame.pixels)
            else:
                self.animPanel.refreshSprite(self.curFrame.pixels2)
            self.animPanel.update()

    def getCurrentSpriteObject(self):
        return self.weaponSprite

    def getCurrentData(self):
        return self.weaponSprite

    changeSelection = changeWeaponSprite

    curFrame = property(lambda self: self.weaponSprite.frames[self.curFrameIdx])
    curPalette = property(lambda self: self.weaponSprite.palettes[self.curPaletteIdx])