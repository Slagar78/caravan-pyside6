import binascii
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QRadioButton, QFileDialog, QMessageBox,
    QButtonGroup, QDialog, QComboBox          # <-- добавлен QComboBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
import data
from PIL import Image
import rompanel
import shiboken6


class SpritePanel(rompanel.ROMPanel):
    frameTitle = "Sprite Editor"

    def init(self):
        self.palette = data.Palette()
        self.palette.init(["#000000"] * 16)
        if self.rom and "palettes" in self.rom.data:
            pal = self.rom.getDataByName("palettes", "Sprite & UI Palette")
            if pal is not None:
                self.palette = pal

        self.side = 0
        self.frame = 0
        self.mode = 0
        self.color_left = 0
        self.color_right = 0
        self.curSpriteIdx = 0
        self.animCur = 0
        self.animFrame = 0
        self.sprite = None

        # ---------- Select Sprite ----------
        sbs0 = QGroupBox("Select Sprite")
        sbs0_layout = QVBoxLayout(sbs0)
        self.spriteList = QComboBox()
        sprite_names = [self.rom.data["sprites"][s*3].name for s in range(len(self.rom.data["sprites"])//3)]
        self.spriteList.addItems(sprite_names)
        self.spriteList.setCurrentIndex(0)
        sbs0_layout.addWidget(self.spriteList)

        # ==================== Direction ====================
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

        # ==================== Change Animation ====================
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

        # ==================== Edit ====================
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

        # Left part
        sbs4left = QVBoxLayout()
        colorSizer = QGridLayout()
        for i, cp in enumerate(self.colorPanels):
            colorSizer.addWidget(cp, i // 2, i % 2)

        self.importButton = QPushButton("Import")
        self.importButton.setFixedSize(40, 20)
        self.exportButton = QPushButton("Export")
        self.exportButton.setFixedSize(40, 20)

        sbs4left.addWidget(text1, alignment=Qt.AlignCenter)
        sbs4left.addLayout(colorSizer)
        sbs4left.addWidget(self.importButton, alignment=Qt.AlignCenter)
        sbs4left.addWidget(self.exportButton, alignment=Qt.AlignCenter)

        # Center
        sbs4mid = QVBoxLayout()
        sbs4mid.addWidget(text2, alignment=Qt.AlignCenter)
        sbs4mid.addWidget(self.editPanel, alignment=Qt.AlignCenter)

        # Right part
        sbs4right = QVBoxLayout()
        self.selectedColorLeft = rompanel.ColorPanel(self, None, "#000000", size=(40, 40), enable=False)
        self.selectedColorRight = rompanel.ColorPanel(self, None, "#000000", size=(40, 40), enable=False)
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
        sbs4right.addWidget(self.switchButton, alignment=Qt.AlignCenter)

        sbs4_layout.addLayout(sbs4left, 0)
        sbs4_layout.addLayout(sbs4mid, 1)
        sbs4_layout.addLayout(sbs4right, 0)

        # ==================== Preview Animation ====================
        sbs5 = QGroupBox("Preview Animation")
        sbs5.setMinimumSize(100, 100)
        sbs5_layout = QVBoxLayout(sbs5)

        self.animPanel = rompanel.SpritePanel(self, None, 24, 24, self.palette, scale=3, bg=16, edit=False)
        self.animPanel.setFixedSize(72, 72)

        self.animDelays = [250, 150, 120, 80, 60, 60]   # Walk, Run, Nod...
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.TimerTest)

        sbs5_layout.addWidget(self.animPanel, alignment=Qt.AlignCenter)

        # ==================== Main Layout ====================
        midSizer = QHBoxLayout()
        midRightSizer = QVBoxLayout()

        midSizer.addWidget(sbs4)
        midRightSizer.addWidget(sbs5)
        midRightSizer.addWidget(sbs3)
        midSizer.addLayout(midRightSizer)

        self.sizer.addWidget(sbs0, 0, 0, 1, 2)          # строка 0 – Select Sprite
        self.sizer.addWidget(sbs1, 1, 0, 1, 2)          # строка 1 – Direction
        midContainer = QWidget()
        midContainer.setLayout(midSizer)
        self.sizer.addWidget(midContainer, 2, 0, 1, 2)  # строка 2 – редактор + анимация

        # Load first sprite
        if self.rom and "sprites" in self.rom.data and len(self.rom.data["sprites"]) >= 3:
            self.changeSprite(0)

        # ==================== Signals ====================
        self.facingGroup.buttonClicked.connect(self.OnSelectFacing)
        self.modePixel.toggled.connect(self.OnSelectMode)
        self.modeFill.toggled.connect(self.OnSelectMode)
        self.modeReplace.toggled.connect(self.OnSelectMode)

        self.importButton.clicked.connect(self.OnImportImage)
        self.exportButton.clicked.connect(self.OnExportImage)
        self.switchButton.clicked.connect(self.OnSwitchFrame)
        self.spriteList.currentIndexChanged.connect(self.OnSelectSprite)

        for i, btn in enumerate(self.animButtons):
            btn.clicked.connect(lambda checked=False, idx=i: self.changeAnim(idx))

        # Timer
        self.timer.start(self.animDelays[0])  # start with Walk

    # ====================== Methods ======================

    def OnImportImage(self):
        if not shiboken6.isValid(self.editPanel):
            return
        if self.editPanel.bmp is None:
            self.editPanel.refreshSprite(self.editPanel.pixels)

        size = self.editPanel.bmp.size()
        w, h = size.width(), size.height()

        dlg = QFileDialog(self, f"Import 16-color {w}x{h} GIF", "", "GIF files (*.gif)")
        dlg.setFileMode(QFileDialog.ExistingFile)

        if dlg.exec() == QDialog.Accepted:
            fn = dlg.selectedFiles()[0]
            try:
                img = Image.open(fn)
                if img.size != (w, h):
                    QMessageBox.warning(self, f"{fn} is {img.size[0]}x{img.size[1]} and should be {w}x{h}.",
                                        self.parent.baseTitle + " -- Error")
                elif img.format != "GIF" or img.getpalette() is None:
                    QMessageBox.warning(self, f"{fn} is not a GIF or is improperly formatted.",
                                        self.parent.baseTitle + " -- Error")
                else:
                    imgdata = list(img.getdata())
                    pixels = "".join(f"{d:x}" for d in imgdata)
                    pixels = [pixels[i:i + w] for i in range(0, w * h, w)]

                    raw = self.sprite.convertFromPixelRows(pixels) or ""

                    if self.frame == 0:
                        self.sprite.pixels = pixels
                        self.sprite.raw_pixels = raw
                    else:
                        self.sprite.pixels2 = pixels
                        self.sprite.raw_pixels2 = raw

                    self.changeSprite()
                    self.changeColors()
                    self.modify()
                del img
            except Exception:
                QMessageBox.warning(self, f"{fn} is not a GIF or is improperly formatted.",
                                    self.parent.baseTitle + " -- Error")

    def OnExportImage(self):
        if not shiboken6.isValid(self.editPanel):
            return
        if self.editPanel.bmp is None:
            self.editPanel.refreshSprite(self.editPanel.pixels)

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

    def OnShow(self, event=None):
        self.changeColors()
        if hasattr(self, 'selectedColorLeft') and shiboken6.isValid(self.selectedColorLeft):
            self.selectedColorLeft.setStyleSheet(f"background-color: {self.palette.colors[self.color_left]};")
        if hasattr(self, 'selectedColorRight') and shiboken6.isValid(self.selectedColorRight):
            self.selectedColorRight.setStyleSheet(f"background-color: {self.palette.colors[self.color_right]};")

    def TimerTest(self):
        self.animFrame ^= 1
        self.changeAnimSprite()

    def changeColors(self):
        for c in range(16):
            if shiboken6.isValid(self.colorPanels[c]):
                self.colorPanels[c].setStyleSheet(f"background-color: {self.palette.colors[c]};")
                self.colorPanels[c].update()

    def changeEditColor(self, button, num):
        if button == 0:
            self.color_left = num
            self.selectedColorLeft.color = num
            self.selectedColorLeft.setStyleSheet(f"background-color: {self.palette.colors[num]};")
        else:
            self.color_right = num
            self.selectedColorRight.color = num
            self.selectedColorRight.setStyleSheet(f"background-color: {self.palette.colors[num]};")

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

    def OnSwitchFrame(self):
        self.frame ^= 1
        self.changeSprite()

    def OnSelectSprite(self, idx):
        self.changeSprite(idx * 3)

    def changeSprite(self, num=None):
        if num is not None:
            self.curSpriteIdx = num
            if self.rom and "sprites" in self.rom.data and not self.rom.data["sprites"][num].loaded:
                self.rom.getSprites(num, num + 2)
            self.sprite = self.rom.data["sprites"][num + self.side]

        if not self.sprite or not shiboken6.isValid(self.editPanel):
            return

        if self.frame == 0 or not hasattr(self.sprite, 'pixels2'):
            self.editPanel.refreshSprite(self.sprite.pixels)
        else:
            self.editPanel.refreshSprite(self.sprite.pixels2)

        self.updateModifiedIndicator(self.sprite.modified)
        self.editPanel.update()
        self.refreshPixels()

    def changeAnim(self, num):
        self.animCur = num
        self.timer.start(self.animDelays[num])

    def changeAnimSprite(self):
        if not shiboken6.isValid(self.animPanel) or not self.sprite:
            return

        if self.animFrame == 0 or not hasattr(self.sprite, 'pixels2'):
            pixels = self.sprite.pixels
        else:
            pixels = self.sprite.pixels2

        self.animPanel.refreshSprite(pixels, force=True)
        self.animPanel.update()

    def refreshPixels(self):
        pass

    def getCurrentSpriteObject(self):
        return self.sprite

    def getCurrentData(self):
        return self.sprite

    changeSelection = changeSprite