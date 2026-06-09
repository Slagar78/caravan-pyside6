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
        dlg = QFileDialog(self, "Import 16x24 icon from PNG", "", "PNG files (*.png)")
        dlg.setFileMode(QFileDialog.ExistingFile)
        if dlg.exec() != QDialog.Accepted:
            return
        fn = dlg.selectedFiles()[0]
        try:
            img = Image.open(fn)
            if img.size != (16, 24):
                QMessageBox.warning(self, "Error", f"Image must be 16x24 pixels. This one is {img.size[0]}x{img.size[1]}.")
                return

            # Фиксированная игровая палитра (индекс 0 – прозрачный)
            game_palette = []
            for i in range(16):
                c = self.palette.colors[i]
                game_palette.append((int(c[1:3],16), int(c[3:5],16), int(c[5:7],16)))

            # Если PNG индексированный – работаем с его палитрой
            if img.mode == 'P':
                pal = img.getpalette()
                transp = img.info.get('transparency', None)
                # Строим маппинг: индекс PNG -> индекс игры
                mapping = []
                for i in range(16):
                    if i == transp:          # прозрачный индекс в PNG
                        mapping.append(0)
                        continue
                    r, g, b = pal[i*3], pal[i*3+1], pal[i*3+2]
                    # Ищем ближайший в игровой палитре (кроме индекса 0)
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
                # Не индексированный – конвертируем в RGBA, прозрачность по альфе
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

            # Записываем пиксели в иконку (16×24)
            w, h = 16, 24
            pixels = []
            for y in range(h):
                row = new_indices[y*w:(y+1)*w]
                pixels.append("".join(["%x" % v for v in row]))

            self.curIcon.pixels = pixels
            self.curIcon.raw_pixels = "".join(pixels)
            self.curIcon.modified = True

            self.changeIcon(self.curIconIdx)
            self.changeColors()
            self.modify()
        except Exception as e:
            QMessageBox.critical(self, "Import Error", str(e))

    def OnExportImage(self):
        if not shiboken6.isValid(self.editPanel):
            return
        dlg = QFileDialog(self, "Export icon as PNG", "", "PNG files (*.png)")
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        if dlg.exec() != QDialog.Accepted:
            return
        fn = dlg.selectedFiles()[0]
        try:
            w, h = 16, 24
            img = Image.new("P", (w, h))
            flat = [int(a, 16) for pr in self.editPanel.pixels for a in pr]
            img.putdata(flat)

            # Палитра из self.palette (16 цветов)
            palette_bytes = []
            for i in range(16):
                c = self.palette.colors[i]
                palette_bytes.extend([int(c[1:3],16), int(c[3:5],16), int(c[5:7],16)])
            palette_bytes += [0] * (768 - len(palette_bytes))
            img.putpalette(palette_bytes)

            # Прозрачность для индекса 0
            img.save(fn, "PNG", transparency=0)
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