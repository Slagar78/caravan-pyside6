import binascii
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QComboBox, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage, QColor
import data
from PIL import Image
import rompanel

h2i = lambda i: int(i, 16)

class SpellAnimationPanel(rompanel.ROMPanel):

    frameTitle = "Spell Animation Editor"

    def init(self):

        self.palette = self.rom.getDataByName("palettes", "Sprite & UI Palette")
        self.side = 0
        self.frame = 0
        self.mode = 0

        self.color_left = 0
        self.color_right = 0

        self.curFrameIdx = 0
        self.curPaletteIdx = 0

        leftSizer = QVBoxLayout()

        # sbs4 – Edit section
        sbs4 = QVBoxLayout()
        sbs4_widget = QWidget()
        sbs4_widget.setLayout(sbs4)
        sbs4_widget.setStyleSheet("border: 1px solid black;")

        text1 = QLabel("Colors")
        text2 = QLabel("Sprite (Color 0 = trans)")

        self.editPanel = rompanel.SpritePanel(self, None, 16*8, 16*8, self.palette, scale=3, bg=16)

        self.colorPanels = []
        for p in range(16):
            self.colorPanels.append(rompanel.ColorPanel2(self, None, "#000000", num=p))

        self.changeColors()

        self.importButton = QPushButton("Import")
        self.importButton.setFixedSize(40, 20)
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

        sbs4.addLayout(sbs4left, 0)
        sbs4.addLayout(sbs4mid, 1)

        midSizer = QHBoxLayout()
        midSizer.addLayout(sbs4)

        self.sizer.addLayout(midSizer, 0, 0, 1, 2)

        self.changeSpellAnim(0)

        self.importButton.clicked.connect(self.OnImportImage)
        self.exportButton.clicked.connect(self.OnExportImage)

        self.printed = False

    def printrb(self):
        rb = self.curFrame.raw_bytes.split("\n")
        hx = self.curFrame.hexlify().split("\n")
        for i in range(max(len(rb), len(hx))):
            line1 = rb[i] if i < len(rb) else "No line"
            line2 = hx[i] if i < len(hx) else "No line"
            if line1 and line2:
                print(["Different!!!", "Same"][line1 == line2])
            print(line1)
            print(line2)
            print()

    def OnImportImage(self):
        size = self.editPanel.bmp.GetSize()
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
                    QMessageBox.warning(self,
                                        f"{fn} is {imgw}x{imgh} and should be {width}x{height}.",
                                        self.parent.baseTitle + " -- Error")
                elif img.format != "GIF" or imgpal is None:
                    QMessageBox.warning(self,
                                        f"{fn} is not a GIF or is improperly formatted.",
                                        self.parent.baseTitle + " -- Error")
                else:
                    cols = ["#%02x%02x%02x" % (imgpal[i]//16*17, imgpal[i+1]//16*17, imgpal[i+2]//16*17) for i in range(0, 48, 3)]
                    pal = data.Palette()
                    pal.init(cols)
                    self.editPanel.palette = pal
                    self.palette = pal
                    self.spellAnim.palette = pal
                    imgdata = list(img.getdata())
                    pixels = "".join(["%x" % d for d in imgdata])
                    pixels = [pixels[i:i+width] for i in range(0, width*height, width)]
                    self.curFrame.convertFromPixelRows(pixels)
                    newtiles = [None]*len(self.curFrame.tiles)
                    order = self.curFrame.getTileOrder(imgw//8, imgh//8)
                    for i in range(len(newtiles)):
                        newtiles[order[i]] = self.curFrame.tiles[i]
                    self.curFrame.tiles = newtiles
                    self.changeSpellAnim()
                    self.changeColors()
                    self.modify()
                del img
            except IOError:
                QMessageBox.warning(self,
                                    f"{fn} is not a GIF or is improperly formatted.",
                                    self.parent.baseTitle + " -- Error")

    def OnExportImage(self):
        size = self.editPanel.bmp.GetSize()
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

    def OnShow(self):
        for p in range(16):
            self.colorPanels[p].setStyleSheet(f"background-color: {self.palette.colors[p]};")
            self.colorPanels[p].update()

    def TimerTest(self):
        self.animFrame ^= 1

    def changeColors(self):
        palette = self.palette
        for c in range(len(self.colorPanels)):
            self.colorPanels[c].setStyleSheet(f"background-color: {palette.colors[c]};")
            self.colorPanels[c].update()

    def OnSelectPalette(self, idx):
        self.curPaletteIdx = idx
        self.changeSpellAnim()

    def OnSelectFrame(self, idx):
        self.curFrameIdx = idx
        self.changeSpellAnim()

    def changeEditColor(self, button, num):
        if button == 0:
            self.color_left = num
        else:
            self.color_right = num
        # button = [self.selectedColorLeft, self.selectedColorRight][button]
        # button.color = num
        # button.SetBackgroundColour(self.palette.colors[num])
        # button.Refresh()

    def refreshPixels(self):
        pass

    def OnChangeAnim(self, button_id):
        # logic not fully implemented
        pass

    def OnSelectMode(self, mode_id):
        pass

    def OnSelectSpellAnim(self, idx):
        self.changeSpellAnim(idx)

    def OnSwitchFrame(self):
        self.frame ^= 1
        self.changeSpellAnim(self.spellAnimList.GetSelection())

    def changeSpellAnim(self, num=None):
        if num is not None:
            if not self.rom.data["spell_animations"][num].loaded:
                self.rom.getSpellAnimations(num, num)
            self.curPaletteIdx = 0
            self.curFrameIdx = 0
            self.spellAnim = self.rom.data["spell_animations"][num]

        self.palette = self.curPalette
        self.editPanel.palette = self.palette
        self.changeColors()

        pixels = []
        tw = self.editPanel.width // 8
        th = self.editPanel.height // 8
        order = self.curFrame.getTileOrder(tw, th)
        tiles = [self.curFrame.tiles[t] for t in order]

        for tRow in range(th):
            for pRow in range(8):
                row = "".join([tiles[tRow*tw+to].pixels[pRow] for to in range(tw) if tRow*tw+to < len(tiles)])
                row += "0" * (tw*8 - len(row))
                pixels.append(row)
        self.editPanel.refreshSprite(pixels, force=True)

        self.updateModifiedIndicator(self.spellAnim.modified)
        self.editPanel.update()
        self.refreshPixels()

    def changeAnim(self, num):
        self.animCur = num
        # self.timer.Start(self.animDelays[num])

    def getCurrentSpriteObject(self):
        return self.spellAnim

    def getCurrentData(self):
        return self.spellAnim

    changeSelection = changeSpellAnim

    curFrame = property(lambda self: self.spellAnim.frame)
    curPalette = property(lambda self: self.spellAnim.palette)