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

class BackgroundPanel(rompanel.ROMPanel):

    frameTitle = "Battle Background Editor"

    def init(self):
        self.palette = self.rom.getDataByName("palettes", "Sprite & UI Palette")
        self.mode = 0
        self.color_left = 0
        self.color_right = 0

        # ---------- Выбор фона ----------
        bgLabel = QLabel("Background:")
        self.backgroundList = QComboBox()
        self.backgroundList.addItems([bs.name for bs in self.rom.data["backgrounds"]])
        self.backgroundList.setCurrentIndex(0)

        # ---------- Группа Edit ----------
        sbs4 = QGroupBox("Edit")
        sbs4_layout = QHBoxLayout(sbs4)

        text1 = QLabel("Colors")

        self.editPanel = rompanel.SpritePanel(self, None, 32*8, 12*8, self.palette, scale=2, bg=16, func="edit")

        self.colorPanels = []
        for p in range(16):
            self.colorPanels.append(rompanel.ColorPanel2(self, None, "#000000", num=p))

        self.changeColors()

        self.importButton = QPushButton("Import")
        self.importButton.setFixedSize(60, 22)
        self.exportButton = QPushButton("Export")
        self.exportButton.setFixedSize(60, 22)

        # Индикаторы выбранных цветов (L / R)
        self.selectedColorLeft = QLabel()
        self.selectedColorLeft.setFixedSize(32, 32)
        self.selectedColorLeft.setStyleSheet("border: 2px solid #555; border-radius: 4px; background-color: #000;")
        self.selectedColorLeft.color = 0

        self.selectedColorRight = QLabel()
        self.selectedColorRight.setFixedSize(32, 32)
        self.selectedColorRight.setStyleSheet("border: 2px solid #555; border-radius: 4px; background-color: #000;")
        self.selectedColorRight.color = 0

        # Левая панель: Colors + палитра + кнопки
        sbs4left = QVBoxLayout()
        sbs4left.setContentsMargins(4, 4, 4, 4)
        sbs4left.setSpacing(6)

        # Палитра в два столбца (как в BattleSpritePanel)
        leftCol = QVBoxLayout()
        leftCol.setSpacing(3)
        for i in range(0, 8):
            leftCol.addWidget(self.colorPanels[i], alignment=Qt.AlignCenter)

        rightCol = QVBoxLayout()
        rightCol.setSpacing(3)
        for i in range(8, 16):
            rightCol.addWidget(self.colorPanels[i], alignment=Qt.AlignCenter)

        colorSizer = QHBoxLayout()
        colorSizer.addLayout(leftCol)
        colorSizer.addSpacing(10)
        colorSizer.addLayout(rightCol)
        colorSizer.addSpacing(6)

        # Индикаторы L / R справа от палитры
        indicators_col = QVBoxLayout()
        indicators_col.setSpacing(4)
        left_lbl = QLabel("L"); left_lbl.setAlignment(Qt.AlignCenter)
        indicators_col.addWidget(left_lbl)
        indicators_col.addWidget(self.selectedColorLeft)
        right_lbl = QLabel("R"); right_lbl.setAlignment(Qt.AlignCenter)
        indicators_col.addWidget(right_lbl)
        indicators_col.addWidget(self.selectedColorRight)

        colorSizer.addLayout(indicators_col)
        colorSizer.addStretch(1)

        sbs4left.addWidget(text1, alignment=Qt.AlignCenter)
        sbs4left.addLayout(colorSizer)
        sbs4left.addWidget(self.importButton, alignment=Qt.AlignCenter)
        sbs4left.addWidget(self.exportButton, alignment=Qt.AlignCenter)

        # Центральная панель – сам спрайт
        sbs4mid = QVBoxLayout()
        sbs4mid.addWidget(self.editPanel, alignment=Qt.AlignCenter)

        sbs4_layout.addLayout(sbs4left, 0)
        sbs4_layout.addLayout(sbs4mid, 1)

        # Основная компоновка
        topSizer = QHBoxLayout()
        topLeftSizer = QVBoxLayout()
        topLeftSizer.addWidget(bgLabel)
        topLeftSizer.addWidget(self.backgroundList)
        topLeftSizer.addStretch(1)

        topSizer.addLayout(topLeftSizer)
        topSizer.addWidget(sbs4, 1)

        self.sizer.addLayout(topSizer, 0, 0, 1, 2)

        # Таймер анимации
        self.animFrame = 0
        self.animCur = 0
        self.animDelays = [250, 150, 50, 50, 50, 50]
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.TimerTest)
        self.changeAnim(0)

        self.changeBackground(0)

        # Сигналы
        self.backgroundList.currentIndexChanged.connect(self.OnSelectBackground)
        self.importButton.clicked.connect(self.OnImportImage)
        self.exportButton.clicked.connect(self.OnExportImage)

    # ========== Методы ==========

    def changeEditColor(self, button, num):
        if button == 0:
            self.color_left = num
            self.selectedColorLeft.color = num
            self.selectedColorLeft.setStyleSheet(
                f"border: 2px solid #555; border-radius: 4px; background-color: {self.palette.colors[num]};"
            )
        else:
            self.color_right = num
            self.selectedColorRight.color = num
            self.selectedColorRight.setStyleSheet(
                f"border: 2px solid #555; border-radius: 4px; background-color: {self.palette.colors[num]};"
            )

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
                    self.background.palette = pal
                    imgdata = list(img.getdata())
                    pixels = "".join(["%x" % d for d in imgdata])
                    pixels = [pixels[i:i+w] for i in range(0, w*h, w)]
                    self.curFrame.convertFromPixelRows(pixels)
                    newtiles = [None]*len(self.curFrame.tiles)
                    order = self.curFrame.getTileOrder(imgw//8, imgh//8)
                    for i in range(len(newtiles)):
                        newtiles[order[i]] = self.curFrame.tiles[i]
                    self.curFrame.tiles = newtiles
                    self.changeBackground()
                    self.changeColors()
                    self.modify()
                del img
            except Exception as e:
                QMessageBox.warning(self, f"Import failed: {e}", self.parent.baseTitle + " -- Error")

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

    def OnShow(self):
        import shiboken6
        for p in range(16):
            if p < len(self.colorPanels):
                cp = self.colorPanels[p]
                if shiboken6.isValid(cp):
                    cp.setStyleSheet(f"background-color: {self.palette.colors[p]}; border: none; border-radius: 3px;")
                    cp.update()
        if hasattr(self, 'selectedColorLeft') and shiboken6.isValid(self.selectedColorLeft):
            self.selectedColorLeft.setStyleSheet(
                f"border: 2px solid #555; border-radius: 4px; background-color: {self.palette.colors[self.color_left]};"
            )
        if hasattr(self, 'selectedColorRight') and shiboken6.isValid(self.selectedColorRight):
            self.selectedColorRight.setStyleSheet(
                f"border: 2px solid #555; border-radius: 4px; background-color: {self.palette.colors[self.color_right]};"
            )

    def changeColors(self):
        palette = self.palette
        for c in range(len(self.colorPanels)):
            cp = self.colorPanels[c]
            if shiboken6.isValid(cp):
                cp.setStyleSheet(f"background-color: {palette.colors[c]}; border: none; border-radius: 3px;")
                cp.update()
        if shiboken6.isValid(self.editPanel):
            self.editPanel.palette = palette
            self.editPanel.update()

    def OnSelectBackground(self, idx):
        self.changeBackground(idx)

    def changeBackground(self, num=None):
        if num is not None:
            if not self.rom.data["backgrounds"][num].loaded:
                self.rom.getBackgrounds(num, num)
            self.background = self.rom.data["backgrounds"][num]
            self.editPanel.width = 256
            self.editPanel.height = 96

        if not hasattr(self, 'background') or self.background is None:
            return

        self.palette = self.background.palette
        if shiboken6.isValid(self.editPanel):
            self.editPanel.palette = self.palette
        self.changeColors()

        frame = self.background.frame
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
            self.updateModifiedIndicator(self.background.modified)
            self.editPanel.update()

    def changeAnim(self, num):
        self.animCur = num
        self.timer.start(self.animDelays[num])

    def refreshPixels(self):
        pass

    def getCurrentSpriteObject(self):
        return self.background

    def getCurrentData(self):
        return self.background

    changeSelection = changeBackground

    curFrame = property(lambda self: self.background.frame)
    curPalette = property(lambda self: self.background.palette)