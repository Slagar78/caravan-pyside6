import binascii
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QRadioButton, QFileDialog, QMessageBox,
    QDialog
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage, QColor
import data
from PIL import Image
import rompanel
import shiboken6

h2i = lambda i: int(i, 16)

class MenuIconPanel(rompanel.ROMPanel):
    frameTitle = "Menu Icon Editor"

    def init(self):
        # Палитра
        self.palette = self.rom.getDataByName("palettes", "Sprite & UI Palette")
        if self.palette is None:
            self.palette = data.Palette()
            self.palette.init(["#000000"] * 16)

        self.frame = 0
        self.mode = 0
        self.color_left = 0
        self.color_right = 0
        self.curIconIdx = 0
        self.animFrame = 0
        self.animCur = 0
        self.icon = None

        # ==================== Edit ====================
        sbs4 = QGroupBox("Edit")
        sbs4_layout = QHBoxLayout(sbs4)

        text1 = QLabel("Colors")
        text2 = QLabel("Icon (Color 0 = trans)")
        text3 = QLabel("Left-Click")
        text4 = QLabel("Right-Click")
        text5 = QLabel("Mode")

        # Основной холст – редактирование включено
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

        # ==================== Change Animation ====================
        sbs3 = QGroupBox("Change Animation")
        sbs3_layout = QHBoxLayout(sbs3)
        self.animButtons = []
        for i, bt in enumerate(["Walk", "Run"]):
            b = QPushButton(bt)
            b.setFixedSize(40, 20)
            self.animButtons.append(b)
            sbs3_layout.addWidget(b, alignment=Qt.AlignCenter)

        # ==================== Preview Animation ====================
        sbs5 = QGroupBox("Preview Animation")
        sbs5.setMinimumSize(100, 100)
        sbs5_layout = QVBoxLayout(sbs5)

        # Превью: клик игнорируется (пустая лямбда)
        self.animPanel = rompanel.SpritePanel(self, None, 24, 24, self.palette, scale=3, bg=16, edit=False,
                                              func=lambda event: None)
        self.animPanel.setFixedSize(72, 72)

        self.animDelays = [250, 150]
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

        midContainer = QWidget()
        midContainer.setLayout(midSizer)
        self.sizer.addWidget(midContainer, 0, 0, 1, 2)

        # Load first icon
        self.changeIcon(0)

        # ==================== Signals ====================
        self.modePixel.toggled.connect(self.OnSelectMode)
        self.modeFill.toggled.connect(self.OnSelectMode)
        self.modeReplace.toggled.connect(self.OnSelectMode)

        self.importButton.clicked.connect(self.OnImportImage)
        self.exportButton.clicked.connect(self.OnExportImage)
        self.switchButton.clicked.connect(self.OnSwitchFrame)

        for i, btn in enumerate(self.animButtons):
            btn.clicked.connect(lambda checked=False, idx=i: self.changeAnim(idx))

        self.timer.start(self.animDelays[0])   # Walk сразу

    # ====================== Methods ======================

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
                    raw = self.icon.convertFromPixelRows(pixels) or ""

                    if self.frame == 0:
                        self.icon.pixels = pixels
                        self.icon.raw_pixels = raw
                    else:
                        self.icon.pixels2 = pixels
                        self.icon.raw_pixels2 = raw

                    self.changeIcon()
                    self.changeColors()
                    self.modify()
                del img
            except Exception:
                QMessageBox.warning(self, f"{fn} is not a GIF or is improperly formatted.",
                                    self.parent.baseTitle + " -- Error")

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
        self.changeAnimIcon()

    def changeColors(self):
        for c in range(16):
            if shiboken6.isValid(self.colorPanels[c]):
                self.colorPanels[c].setStyleSheet(f"background-color: {self.palette.colors[c]};")
                self.colorPanels[c].update()

    def OnSelectMode(self, checked):
        if self.modePixel.isChecked():
            self.mode = 0
        elif self.modeFill.isChecked():
            self.mode = 1
        elif self.modeReplace.isChecked():
            self.mode = 2

    def OnSwitchFrame(self):
        self.frame ^= 1
        self.changeIcon(self.curIconIdx)

    def changeIcon(self, num=None):
        if num is not None:
            self.curIconIdx = num
            if not self.rom.data["menu_icons"][num].loaded:
                self.rom.getMenuIcons(num, num)
            self.icon = self.rom.data["menu_icons"][num]

        if not self.icon:
            return

        if self.frame == 0 or not hasattr(self.icon, 'pixels2'):
            self.editPanel.refreshSprite(self.icon.pixels)
        else:
            self.editPanel.refreshSprite(self.icon.pixels2)

        self.editPanel.update()
        self.refreshPixels()

    def changeAnim(self, num):
        self.animCur = num
        self.timer.start(self.animDelays[num])

    def changeAnimIcon(self):
        if not shiboken6.isValid(self.animPanel) or not self.icon:
            return

        if self.animFrame == 0 or not hasattr(self.icon, 'pixels2'):
            pixels = self.icon.pixels
        else:
            pixels = self.icon.pixels2

        self.animPanel.refreshSprite(pixels, force=True)
        self.animPanel.update()

    def refreshPixels(self):
        pass

    def OnShow(self, event=None):
        self.changeColors()
        if hasattr(self, 'selectedColorLeft') and shiboken6.isValid(self.selectedColorLeft):
            self.selectedColorLeft.setStyleSheet(f"background-color: {self.palette.colors[self.color_left]};")
        if hasattr(self, 'selectedColorRight') and shiboken6.isValid(self.selectedColorRight):
            self.selectedColorRight.setStyleSheet(f"background-color: {self.palette.colors[self.color_right]};")

    def changeEditColor(self, button, num):
        """Выбор цвета с палитры (левый/правый клик)"""
        if button == 0:
            self.color_left = num
            if hasattr(self, 'selectedColorLeft') and shiboken6.isValid(self.selectedColorLeft):
                self.selectedColorLeft.color = num
                self.selectedColorLeft.setStyleSheet(f"background-color: {self.palette.colors[num]};")
        else:
            self.color_right = num
            if hasattr(self, 'selectedColorRight') and shiboken6.isValid(self.selectedColorRight):
                self.selectedColorRight.color = num
                self.selectedColorRight.setStyleSheet(f"background-color: {self.palette.colors[num]};")

    def getCurrentSpriteObject(self):
        return self.icon

    def getCurrentData(self):
        return self.icon

    changeSelection = changeIcon