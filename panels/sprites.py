import binascii
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QRadioButton, QFileDialog, QMessageBox,
    QButtonGroup
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage, QColor
import data
from PIL import Image
import rompanel
import shiboken6

h2i = lambda i: int(i, 16)

class SpritePanel(rompanel.ROMPanel):
    
    frameTitle = "Sprite Editor"
    
    def init(self):
        
        self.palette = self.rom.getDataByName("palettes", "Sprite & UI Palette")
        self.side = 0
        self.frame = 0
        self.mode = 0
        
        self.color_left = 0
        self.color_right = 0
        
        self.curSpriteIdx = 0
        
        leftSizer = QVBoxLayout()
        
        sbs1 = QGroupBox("Direction")
        sbs1_layout = QVBoxLayout(sbs1)
        
        radioSizer = QHBoxLayout()
        
        self.facingRadioUp = QRadioButton("Up")
        self.facingRadioSide = QRadioButton("Left/Right")
        self.facingRadioDown = QRadioButton("Down")
        self.facingRadioSide.setChecked(True)
        
        self.facingGroup = QButtonGroup()
        self.facingGroup.addButton(self.facingRadioUp, 0)
        self.facingGroup.addButton(self.facingRadioSide, 1)
        self.facingGroup.addButton(self.facingRadioDown, 2)
        
        radioSizer.addWidget(self.facingRadioUp)
        radioSizer.addWidget(self.facingRadioSide)
        radioSizer.addWidget(self.facingRadioDown)
        
        sbs1_layout.addLayout(radioSizer)
        
        sbs3 = QGroupBox("Change Animation")
        sbs3_layout = QGridLayout(sbs3)
        self.animButtons = []
        for i, bt in enumerate(["Walk", "Run", "Nod", "Shake", "Shock", "Jump"]):
            b = QPushButton(bt)
            b.setFixedSize(40, 20)
            if i > 1:
                b.setEnabled(False)
            self.animButtons.append(b)
            sbs3_layout.addWidget(b, i // 2, i % 2)
        
        sbs4 = QGroupBox("Edit")
        sbs4_layout = QHBoxLayout(sbs4)
        
        text1 = QLabel("Colors")
        text2 = QLabel("Sprite (Color 0 = trans)")
        text3 = QLabel("Left-Click")
        text4 = QLabel("Right-Click")
        text5 = QLabel("Mode")
        
        self.editPanel = rompanel.SpritePanel(self, None, 24, 24, self.palette, scale=8, bg=16, func="edit")
        
        self.colorPanels = []
        for p in range(16):
            self.colorPanels.append(rompanel.ColorPanel2(self, None, "#000000", num=p))
        
        self.changeColors()
        
        self.switchButton = QPushButton("Frame")
        self.switchButton.setFixedSize(40, 20)
        
        sbs4left = QVBoxLayout()
        
        colorSizer = QGridLayout()
        for i, cp in enumerate(self.colorPanels):
            colorSizer.addWidget(cp, i // 2, i % 2)
        
        self.importButton = QPushButton("Import")
        self.importButton.setFixedSize(40, 20)
        self.exportButton = QPushButton("Export")
        self.exportButton.setFixedSize(40, 20)
        
        sbs4left.addWidget(text1, 0, Qt.AlignCenter)
        sbs4left.addLayout(colorSizer)
        sbs4left.addWidget(self.importButton, 0, Qt.AlignCenter)
        sbs4left.addWidget(self.exportButton, 0, Qt.AlignCenter)
        
        sbs4mid = QVBoxLayout()
        
        sbs4mid.addWidget(text2, 0, Qt.AlignCenter)
        sbs4mid.addWidget(self.editPanel, 0, Qt.AlignCenter)
        
        sbs4right = QVBoxLayout()
        
        self.selectedColorLeft = rompanel.ColorPanel(self, None, "#000000", size=(40,40), enable=False)
        self.selectedColorRight = rompanel.ColorPanel(self, None, "#000000", size=(40,40), enable=False)
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
        sbs4right.addWidget(self.switchButton, 0, Qt.AlignCenter)
        
        sbs4_layout.addLayout(sbs4left, 0)
        sbs4_layout.addLayout(sbs4mid, 1)
        sbs4_layout.addLayout(sbs4right, 0)
        
        sbs5 = QGroupBox("Preview Animation")
        sbs5_layout = QVBoxLayout(sbs5)
        
        self.animPanel = rompanel.SpritePanel(self, None, 24, 24, self.palette, scale=3, bg=None, edit=False)
    
        self.animDelays = [250, 150, 50, 50, 50, 50]
        self.animFrame = 0
        self.animCur = 0
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.TimerTest)
        self.changeAnim(0)
        
        sbs5_layout.addWidget(self.animPanel, 0, Qt.AlignCenter)
        
        midSizer = QHBoxLayout()
        midRightSizer = QVBoxLayout()
        
        midSizer.addLayout(sbs4_layout)
        midRightSizer.addWidget(sbs5)
        midRightSizer.addWidget(sbs3)
        midSizer.addLayout(midRightSizer)
        
        self.sizer.addWidget(sbs1, 0, 0)
        self.sizer.addLayout(midSizer, 1, 0, 1, 2)
        
        self.changeSprite(0)
        
        self.facingGroup.buttonClicked.connect(self.OnSelectFacing)
        self.modePixel.toggled.connect(self.OnSelectMode)
        self.modeFill.toggled.connect(self.OnSelectMode)
        self.modeReplace.toggled.connect(self.OnSelectMode)
        self.importButton.clicked.connect(self.OnImportImage)
        self.exportButton.clicked.connect(self.OnExportImage)
        self.switchButton.clicked.connect(self.OnSwitchFrame)
        for btn in self.animButtons:
            btn.clicked.connect(self.OnChangeAnim)
        self.timer.timeout.connect(self.TimerTest)
        
        self.printed = False

    def printrb(self):
        rb = self.sprite.raw_bytes.split("\n")
        hx = self.sprite.hexlify().split("\n")
        for i in range(max(len(rb), len(hx))):
            line1 = rb[i] if i < len(rb) else "No line"
            line2 = hx[i] if i < len(hx) else "No line"
            if line1 and line2:
                print(["Different!!!","Same"][line1==line2])
            print(line1)
            print(line2)
            print()

    def OnImportImage(self):
        if not shiboken6.isValid(self.editPanel):
            return
        size = self.editPanel.bmp.GetSize()
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
                    imgdata = list(img.getdata())
                    pixels = "".join(["%x" % d for d in imgdata])
                    pixels = [pixels[i:i+w] for i in range(0, w*h, w)]
                    if self.frame == 0:
                        self.sprite.pixels = pixels
                        self.sprite.raw_pixels = "".join(self.sprite.convertFromPixelRows(pixels))
                    else:
                        self.sprite.pixels2 = pixels
                        self.sprite.raw_pixels2 = "".join(self.sprite.convertFromPixelRows(pixels))
                    self.changeSprite()
                    self.changeColors()
                    self.modify()
                del img
            except IOError:
                QMessageBox.warning(self, f"{fn} is not a GIF or is improperly formatted.", self.parent.baseTitle + " -- Error")

    def OnExportImage(self):
        if not shiboken6.isValid(self.editPanel):
            return
        size = self.editPanel.bmp.GetSize()
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

    def OnShow(self, event=None):
        for p in range(16):
            if shiboken6.isValid(self.colorPanels[p]):
                self.colorPanels[p].setStyleSheet(f"background-color: {self.palette.colors[p]};")
                self.colorPanels[p].update()
        if shiboken6.isValid(self.selectedColorLeft):
            self.selectedColorLeft.setStyleSheet(f"background-color: {self.palette.colors[self.color_left]};")
        if shiboken6.isValid(self.selectedColorRight):
            self.selectedColorRight.setStyleSheet(f"background-color: {self.palette.colors[self.color_right]};")

    def TimerTest(self):
        self.animFrame ^= 1
        self.changeAnimSprite()

    def changeColors(self):
        palette = self.palette
        for c in range(len(self.colorPanels)):
            if shiboken6.isValid(self.colorPanels[c]):
                self.colorPanels[c].setStyleSheet(f"background-color: {palette.colors[c]};")
                self.colorPanels[c].update()

    def changeEditColor(self, button, num):
        if button == 0:
            self.color_left = num
        else:
            self.color_right = num
        if button == 0:
            if shiboken6.isValid(self.selectedColorLeft):
                self.selectedColorLeft.color = num
                self.selectedColorLeft.setStyleSheet(f"background-color: {self.palette.colors[num]};")
        else:
            if shiboken6.isValid(self.selectedColorRight):
                self.selectedColorRight.color = num
                self.selectedColorRight.setStyleSheet(f"background-color: {self.palette.colors[num]};")

    def refreshPixels(self):
        pass

    def OnChangeAnim(self):
        btn = self.sender()
        for i, b in enumerate(self.animButtons):
            if b is btn:
                self.changeAnim(i)
                return

    def OnSelectFacing(self, btn):
        self.side = self.facingGroup.id(btn)
        self.changeSprite(self.curSpriteIdx)

    def OnSelectMode(self, checked):
        if self.modePixel.isChecked():
            self.mode = 0
        elif self.modeFill.isChecked():
            self.mode = 1
        elif self.modeReplace.isChecked():
            self.mode = 2

    def OnSelectSprite(self, idx):
        self.changeSprite(idx * 3)

    def OnSwitchFrame(self):
        self.frame ^= 1
        self.changeSprite(self.curSpriteIdx)

    def changeSprite(self, num=None):
        if num is not None:
            self.curSpriteIdx = num
            if not self.rom.data["sprites"][num].loaded:
                self.rom.getSprites(num, num+2)
            self.sprite = self.rom.data["sprites"][num+self.side]
        if not shiboken6.isValid(self.editPanel):
            return
        if self.frame == 0:
            self.editPanel.refreshSprite(self.sprite.pixels)
        else:
            self.editPanel.refreshSprite(self.sprite.pixels2)
        self.updateModifiedIndicator(self.sprite.modified)
        top = self.window()
        if hasattr(top, 'tempUndoStack'):
            top.tempUndoStack = {}
            top.tempRedoStack = {}
        self.editPanel.update()
        self.refreshPixels()

    def changeAnim(self, num):
        self.animCur = num
        self.timer.start(self.animDelays[num])

    def changeAnimSprite(self):
        if not shiboken6.isValid(self.animPanel):
            return
        if self.animFrame == 0:
            self.animPanel.refreshSprite(self.sprite.pixels)
        else:
            self.animPanel.refreshSprite(self.sprite.pixels2)
        self.animPanel.update()

    def getCurrentSpriteObject(self):
        return self.sprite

    def getCurrentData(self):
        return self.sprite

    changeSelection = changeSprite