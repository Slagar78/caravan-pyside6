import binascii
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QComboBox, QFileDialog, QMessageBox, QDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage, QColor
import data
from PIL import Image
import rompanel
import shiboken6

h2i = lambda i: int(i, 16)

class OtherIconPanel(rompanel.ROMPanel):

    frameTitle = "Item/Spell Icon Editor"

    def init(self):
        self.palette = self.rom.getDataByName("palettes", "Sprite & UI Palette")
        self.mode = 0
        self.color_left = 0
        self.color_right = 0
        self.curIconIdx = 0

        # ---------- Выбор иконки ----------
        iconLabel = QLabel("Icon:")
        self.iconList = QComboBox()
        self.iconList.addItems([ic.name for ic in self.rom.data["other_icons"]])
        self.iconList.setCurrentIndex(0)

        # ---------- Группа Edit ----------
        sbs4 = QGroupBox("Edit")
        sbs4_layout = QHBoxLayout(sbs4)

        text1 = QLabel("Colors")

        self.editPanel = rompanel.SpritePanel(self, None, 16, 24, self.palette, scale=6, bg=16, func="edit")

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

        # Палитра в два столбца
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

        # Центральная панель – сама иконка
        sbs4mid = QVBoxLayout()
        sbs4mid.addWidget(self.editPanel, alignment=Qt.AlignCenter)

        sbs4_layout.addLayout(sbs4left, 0)
        sbs4_layout.addLayout(sbs4mid, 1)

        # Основная компоновка
        topSizer = QHBoxLayout()
        topLeftSizer = QVBoxLayout()
        topLeftSizer.addWidget(iconLabel)
        topLeftSizer.addWidget(self.iconList)
        topLeftSizer.addStretch(1)

        topSizer.addLayout(topLeftSizer)
        topSizer.addWidget(sbs4, 1)

        self.sizer.addLayout(topSizer, 0, 0, 1, 2)

        self.changeIcon(0)

        # Сигналы
        self.iconList.currentIndexChanged.connect(self.OnSelectIcon)
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

    def OnSelectIcon(self, idx):
        self.changeIcon(idx)

    def OnImportImage(self):
        if not shiboken6.isValid(self.editPanel):
            return
        dlg = QFileDialog(self, "Import 16x24 icon from GIF", "", "GIF files (*.gif)")
        dlg.setFileMode(QFileDialog.ExistingFile)
        if dlg.exec() != QDialog.Accepted:
            return
        fn = dlg.selectedFiles()[0]
        try:
            img = Image.open(fn)
            w, h = img.size
            if (w, h) != (16, 24):
                QMessageBox.warning(self, "Error", f"Image must be 16x24 pixels. This one is {w}x{h}.")
                return

            # Эталонный «прозрачный» цвет из игровой палитры (индекс 0)
            base_transparent = self.palette.colors[0]
            tr = int(base_transparent[1:3], 16)
            tg = int(base_transparent[3:5], 16)
            tb = int(base_transparent[5:7], 16)

            # Игровая палитра (индекс 0 = прозрачный, 1..15 – остальные цвета)
            game_pal = [(tr, tg, tb)]
            for i in range(1, 16):
                cstr = self.palette.colors[i]
                game_pal.append((int(cstr[1:3], 16), int(cstr[3:5], 16), int(cstr[5:7], 16)))

            if img.mode == "P":
                pal = img.getpalette()
                transp = img.info.get('transparency', 0)
                gif_pal = []
                for i in range(16):
                    if pal and i*3+2 < len(pal):
                        gif_pal.append((pal[i*3], pal[i*3+1], pal[i*3+2]))
                    else:
                        gif_pal.append((0,0,0))
                # Маппинг индексов GIF → игровых
                mapping = [0] * 16
                mapping[transp] = 0
                for i in range(16):
                    if i == transp:
                        continue
                    best_j = 1
                    best_dist = 999999
                    for j in range(1, 16):
                        pr, pg, pb = gif_pal[i]
                        gr, gg, gb = game_pal[j]
                        dist = (pr-gr)**2 + (pg-gg)**2 + (pb-gb)**2
                        if dist < best_dist:
                            best_dist = dist
                            best_j = j
                    mapping[i] = best_j

                raw = list(img.getdata())
                new_indices = [mapping[idx] for idx in raw]
                pixels = []
                for y in range(24):
                    row_data = new_indices[y*w:(y+1)*w]
                    pixels.append("".join(["%x" % v for v in row_data]))
            else:
                if img.mode != "RGB":
                    img = img.convert("RGB")
                raw = list(img.getdata())
                new_indices = []
                for px in raw:
                    r, g, b = px[:3]
                    dist_to_transp = (r-tr)**2 + (g-tg)**2 + (b-tb)**2
                    if dist_to_transp < 500:
                        new_indices.append(0)
                    else:
                        best_j = 1
                        best_dist = 999999
                        for j in range(1, 16):
                            gr, gg, gb = game_pal[j]
                            dist = (r-gr)**2 + (g-gg)**2 + (b-gb)**2
                            if dist < best_dist:
                                best_dist = dist
                                best_j = j
                        new_indices.append(best_j)
                pixels = []
                for y in range(24):
                    row_data = new_indices[y*w:(y+1)*w]
                    pixels.append("".join(["%x" % v for v in row_data]))

            icon = self.curIcon
            icon.pixels = pixels
            icon.raw_pixels = "".join(pixels)
            icon.modified = True

            self.changeIcon(self.curIconIdx)
            self.changeColors()
            self.modify()
        except Exception as e:
            QMessageBox.critical(self, "Import Error", str(e))

    def OnExportImage(self):
        if not shiboken6.isValid(self.editPanel):
            return
        size = (16, 24)
        dlg = QFileDialog(self, "Export icon as GIF", "", "GIF files (*.gif)")
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        if dlg.exec() != QDialog.Accepted:
            return
        fn = dlg.selectedFiles()[0]
        try:
            img = Image.new("P", size)
            flat = [int(a, 16) for pr in self.editPanel.pixels for a in pr]
            img.putdata(flat)

            # Полная 16-цветная палитра (ровно 48 байт)
            palette_colors = []
            for i in range(16):
                cstr = self.palette.colors[i]
                r = int(cstr[1:3], 16)
                g = int(cstr[3:5], 16)
                b = int(cstr[5:7], 16)
                palette_colors.extend([r, g, b])

            # Дополняем до 768 байт (256 цветов)
            palette_colors += [0] * (768 - len(palette_colors))
            img.putpalette(palette_colors)

            # Прозрачность для индекса 0
            img.save(fn, "GIF", transparency=0)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

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
        import shiboken6
        palette = self.palette
        for c in range(len(self.colorPanels)):
            cp = self.colorPanels[c]
            if shiboken6.isValid(cp):
                cp.setStyleSheet(f"background-color: {palette.colors[c]}; border: none; border-radius: 3px;")
                cp.update()
        if shiboken6.isValid(self.editPanel):
            self.editPanel.palette = palette
            self.editPanel.update()

    def changeIcon(self, num=None):
        if num is not None:
            if not self.rom.data["other_icons"][num].loaded:
                self.rom.getOtherIcons()
            self.curIconIdx = num
            self.curIcon = self.rom.data["other_icons"][num]
            self.editPanel.width = 16
            self.editPanel.height = 24

        if not hasattr(self, 'curIcon') or self.curIcon is None:
            return

        self.palette = self.rom.getDataByName("palettes", "Sprite & UI Palette")
        if shiboken6.isValid(self.editPanel):
            self.editPanel.palette = self.palette
        self.changeColors()

        if shiboken6.isValid(self.editPanel):
            self.editPanel.refreshSprite(self.curIcon.pixels, force=True)
            self.updateModifiedIndicator(self.curIcon.modified)
            self.editPanel.update()

    def refreshPixels(self):
        pass

    def getCurrentSpriteObject(self):
        return self.curIcon

    def getCurrentData(self):
        return self.curIcon

    changeSelection = changeIcon