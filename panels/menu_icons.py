import binascii
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QRadioButton, QComboBox, QFileDialog,
    QMessageBox, QDialog
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

        # ==================== SELECT ICON ====================
        sbs1 = QGroupBox("Select Menu Icon")
        sbs1_layout = QVBoxLayout(sbs1)
        self.iconList = QComboBox()
        self.iconList.addItems([ic.name for ic in self.rom.data["menu_icons"]])
        self.iconList.setCurrentIndex(0)
        sbs1_layout.addWidget(self.iconList)

        # ==================== EDIT ====================
        sbs4 = QGroupBox("Edit")
        sbs4_layout = QHBoxLayout(sbs4)

        text1 = QLabel("Colors")
        text2 = QLabel("Icon (Color 0 = trans)")

        self.editPanel = rompanel.SpritePanel(self, None, 24, 24, self.palette, scale=8, bg=16, func="edit")

        # Палитра 16 цветов (как в оригинале – два столбца)
        self.colorPanels = []
        for p in range(16):
            self.colorPanels.append(rompanel.ColorPanel2(self, None, "#000000", num=p))
        self.changeColors()

        self.importButton = QPushButton("Import")
        self.importButton.setFixedSize(60, 22)
        self.exportButton = QPushButton("Export")
        self.exportButton.setFixedSize(60, 22)

        # Индикаторы выбранного цвета (ColorPanel без рамок, как было)
        self.selectedColorLeft = rompanel.ColorPanel(self, None, "#000000", size=(40, 40), enable=False)
        self.selectedColorRight = rompanel.ColorPanel(self, None, "#000000", size=(40, 40), enable=False)
        self.selectedColorLeft.color = 0
        self.selectedColorRight.color = 0

        # === Левая часть: палитра (два столбца) ===
        sbs4left = QVBoxLayout()
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

        sbs4left.addWidget(text1, alignment=Qt.AlignCenter)
        sbs4left.addLayout(colorSizer)
        sbs4left.addWidget(self.importButton, alignment=Qt.AlignCenter)
        sbs4left.addWidget(self.exportButton, alignment=Qt.AlignCenter)

        # === Центр: спрайт ===
        sbs4mid = QVBoxLayout()
        sbs4mid.addWidget(text2, alignment=Qt.AlignCenter)
        sbs4mid.addWidget(self.editPanel, alignment=Qt.AlignCenter)

        # === Правая часть: L / R, режимы, кнопка Frame ===
        sbs4right = QVBoxLayout()
        left_click_label = QLabel("Left-Click")
        right_click_label = QLabel("Right-Click")
        mode_label = QLabel("Mode")
        self.modePixel = QRadioButton("Pixel")
        self.modeFill = QRadioButton("Floodfill")
        self.modeReplace = QRadioButton("Replace")
        self.modePixel.setChecked(True)
        self.switchButton = QPushButton("Frame")
        self.switchButton.setFixedSize(40, 20)

        sbs4right.addWidget(left_click_label, alignment=Qt.AlignCenter)
        sbs4right.addWidget(self.selectedColorLeft, alignment=Qt.AlignCenter)
        sbs4right.addWidget(right_click_label, alignment=Qt.AlignCenter)
        sbs4right.addWidget(self.selectedColorRight, alignment=Qt.AlignCenter)
        sbs4right.addWidget(mode_label, alignment=Qt.AlignCenter)
        sbs4right.addWidget(self.modePixel)
        sbs4right.addWidget(self.modeFill)
        sbs4right.addWidget(self.modeReplace)
        sbs4right.addWidget(self.switchButton, alignment=Qt.AlignCenter)

        sbs4_layout.addLayout(sbs4left, 0)
        sbs4_layout.addLayout(sbs4mid, 1)
        sbs4_layout.addLayout(sbs4right, 0)

        # ==================== CHANGE ANIMATION ====================
        sbs3 = QGroupBox("Change Animation")
        sbs3_layout = QHBoxLayout(sbs3)
        self.animButtons = []
        for i, bt in enumerate(["Walk", "Run"]):
            b = QPushButton(bt)
            b.setFixedSize(40, 20)
            self.animButtons.append(b)
            sbs3_layout.addWidget(b, alignment=Qt.AlignCenter)

        # ==================== PREVIEW ANIMATION ====================
        sbs5 = QGroupBox("Preview Animation")
        sbs5.setMinimumSize(100, 100)
        sbs5_layout = QVBoxLayout(sbs5)

        self.animPanel = rompanel.SpritePanel(self, None, 24, 24, self.palette, scale=3, bg=16, edit=False,
                                              func=lambda event: None)
        self.animPanel.setFixedSize(72, 72)
        sbs5_layout.addWidget(self.animPanel, alignment=Qt.AlignCenter)

        self.animDelays = [250, 150]
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.TimerTest)

        # ==================== MAIN LAYOUT ====================
        midSizer = QHBoxLayout()
        midRightSizer = QVBoxLayout()

        midSizer.addWidget(sbs4)
        midRightSizer.addWidget(sbs5)
        midRightSizer.addWidget(sbs3)
        midSizer.addLayout(midRightSizer)

        midContainer = QWidget()
        midContainer.setLayout(midSizer)
        self.sizer.addWidget(sbs1, 0, 0, 1, 2)
        self.sizer.addWidget(midContainer, 1, 0, 1, 2)

        # Загрузка первой иконки
        self.changeIcon(0)

        # Signals
        self.iconList.currentIndexChanged.connect(self.OnSelectIcon)
        self.modePixel.toggled.connect(self.OnSelectMode)
        self.modeFill.toggled.connect(self.OnSelectMode)
        self.modeReplace.toggled.connect(self.OnSelectMode)

        self.importButton.clicked.connect(self.OnImportImage)
        self.exportButton.clicked.connect(self.OnExportImage)
        self.switchButton.clicked.connect(self.OnSwitchFrame)

        for i, btn in enumerate(self.animButtons):
            btn.clicked.connect(lambda checked=False, idx=i: self.changeAnim(idx))

        self.timer.start(self.animDelays[0])

    # ====================== Methods ======================

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

    def OnSelectIcon(self, idx):
        self.changeIcon(idx)

    def OnImportImage(self):
        if not shiboken6.isValid(self.editPanel):
            return
        size = self.editPanel.bmp.size()
        w, h = size.width(), size.height()
        dlg = QFileDialog(self, f"Import {w}x{h} PNG", "", "PNG files (*.png)")
        dlg.setFileMode(QFileDialog.ExistingFile)
        if dlg.exec() == QDialog.Accepted:
            fn = dlg.selectedFiles()[0]
            try:
                img = Image.open(fn)
                if img.size != (w, h):
                    QMessageBox.warning(self, f"Image must be {w}x{h}.", self.parent.baseTitle + " -- Error")
                    return

                # Фиксированная игровая палитра (индекс 0 – прозрачный)
                game_palette = []
                for i in range(16):
                    c = self.palette.colors[i]
                    game_palette.append((int(c[1:3],16), int(c[3:5],16), int(c[5:7],16)))

                if img.mode == 'P':
                    pal = img.getpalette()
                    transp = img.info.get('transparency', None)
                    mapping = []
                    for i in range(16):
                        if i == transp:
                            mapping.append(0)
                            continue
                        r, g, b = pal[i*3], pal[i*3+1], pal[i*3+2]
                        best_idx = 1
                        best_dist = 999999
                        for j in range(1, 16):
                            gr, gg, gb = game_palette[j]
                            dist = (r-gr)**2 + (g-gg)**2 + (b-gb)**2
                            if dist < best_dist:
                                best_dist = dist
                                best_idx = j
                        mapping.append(best_idx)
                    raw = list(img.getdata())
                    new_indices = [mapping[idx] for idx in raw]
                else:
                    img = img.convert("RGBA")
                    raw = list(img.getdata())
                    new_indices = []
                    for r, g, b, a in raw:
                        if a < 128:
                            new_indices.append(0)
                            continue
                        best_idx = 1
                        best_dist = 999999
                        for j in range(1, 16):
                            gr, gg, gb = game_palette[j]
                            dist = (r-gr)**2 + (g-gg)**2 + (b-gb)**2
                            if dist < best_dist:
                                best_dist = dist
                                best_idx = j
                        new_indices.append(best_idx)

                pixels = []
                for y in range(h):
                    row = new_indices[y*w:(y+1)*w]
                    pixels.append("".join(["%x" % v for v in row]))
                raw_pixels = "".join(pixels)

                if self.frame == 0:
                    self.icon.pixels = pixels
                    self.icon.raw_pixels = raw_pixels
                else:
                    self.icon.pixels2 = pixels
                    self.icon.raw_pixels2 = raw_pixels

                self.changeIcon()
                self.changeColors()
                self.modify()
            except Exception as e:
                QMessageBox.critical(self, "Import Error", str(e))

    def OnExportImage(self):
        if not shiboken6.isValid(self.editPanel):
            return
        size = self.editPanel.bmp.size()
        w, h = size.width(), size.height()
        dlg = QFileDialog(self, f"Export {w}x{h} PNG", "", "PNG files (*.png)")
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        if dlg.exec() == QDialog.Accepted:
            fn = dlg.selectedFiles()[0]
            try:
                img = Image.new("P", (w, h))
                flat = [int(a, 16) for pr in self.editPanel.pixels for a in pr]
                img.putdata(flat)

                palette_bytes = []
                for i in range(16):
                    c = self.palette.colors[i]
                    palette_bytes.extend([int(c[1:3],16), int(c[3:5],16), int(c[5:7],16)])
                palette_bytes += [0] * (768 - len(palette_bytes))
                img.putpalette(palette_bytes)

                img.save(fn, "PNG", transparency=0)
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

    def TimerTest(self):
        self.animFrame ^= 1
        self.changeAnimIcon()

    def changeColors(self):
        for c in range(16):
            if shiboken6.isValid(self.colorPanels[c]):
                self.colorPanels[c].setStyleSheet(
                    f"background-color: {self.palette.colors[c]}; border: none; border-radius: 3px;"
                )
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

    def getCurrentSpriteObject(self):
        return self.icon

    def getCurrentData(self):
        return self.icon

    changeSelection = changeIcon