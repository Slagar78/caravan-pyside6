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

class BattleFloorPanel(rompanel.ROMPanel):

    frameTitle = "Battle Floor Editor"

    def init(self):
        self.palette = self.rom.getDataByName("palettes", "Sprite & UI Palette")
        self.side = 0
        self.frame = 0
        self.mode = 0
        # Допустимые индексы для рисования (только те, что меняются)
        self.ALLOWED_COLORS = [3, 4, 8]
        # Стартовые выбранные цвета
        self.color_left = 3
        self.color_right = 8
        self.curFrameIdx = 0
        self.curPaletteIdx = 0

        # ---------- Выбор battle floor ----------
        floorLabel = QLabel("Battle Floor:")
        self.battleFloorList = QComboBox()
        self.battleFloorList.addItems([bf.name for bf in self.rom.data["battle_floors"]])
        self.battleFloorList.setCurrentIndex(0)

        # ---------- Группа Edit ----------
        sbs4 = QGroupBox("Edit")
        sbs4_layout = QHBoxLayout(sbs4)

        text1 = QLabel("Colors")

        self.editPanel = rompanel.SpritePanel(self, None, 12*8, 4*8, self.palette, scale=5, bg=16, func="edit")

        self.colorPanels = []
        for p in range(16):
            self.colorPanels.append(rompanel.ColorPanel2(self, None, "#000000", num=p))

        self.changeColors()

        self.importButton = QPushButton("Import")
        self.importButton.setFixedSize(60, 22)
        self.exportButton = QPushButton("Export")
        self.exportButton.setFixedSize(60, 22)
        # Кнопка Import активна (было False)
        self.importButton.setEnabled(True)

        # Индикаторы выбранных цветов (L / R)
        self.selectedColorLeft = QLabel()
        self.selectedColorLeft.setFixedSize(32, 32)
        self.selectedColorLeft.setStyleSheet(
            "border: 2px solid #555; border-radius: 4px; background-color: #000;"
        )
        self.selectedColorLeft.color = self.color_left

        self.selectedColorRight = QLabel()
        self.selectedColorRight.setFixedSize(32, 32)
        self.selectedColorRight.setStyleSheet(
            "border: 2px solid #555; border-radius: 4px; background-color: #000;"
        )
        self.selectedColorRight.color = self.color_right

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
        topLeftSizer.addWidget(floorLabel)
        topLeftSizer.addWidget(self.battleFloorList)
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

        self.changeBattleFloor(0)

        # Сигналы
        self.battleFloorList.currentIndexChanged.connect(self.OnSelectBattleFloor)
        self.importButton.clicked.connect(self.OnImportImage)
        self.exportButton.clicked.connect(self.OnExportImage)

    # ========== Методы ==========

    def changeEditColor(self, button, num):
        """Разрешаем выбор только из индексов 3,4,8."""
        if num not in self.ALLOWED_COLORS:
            return  # игнорируем клик по недопустимому цвету
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
        dlg = QFileDialog(self, f"Import {w}x{h} PNG", "", "PNG files (*.png)")
        dlg.setFileMode(QFileDialog.ExistingFile)
        if dlg.exec() == QDialog.Accepted:
            fn = dlg.selectedFiles()[0]
            try:
                img = Image.open(fn)
                if img.mode != 'P':
                    img = img.convert('P', palette=Image.ADAPTIVE, colors=16)
                if img.mode != 'P':
                    raise ValueError("Image is not indexed. Please save as 16-color PNG with palette.")
                if img.size != (w, h):
                    QMessageBox.warning(self, f"Image must be {w}x{h}.", self.parent.baseTitle + " -- Error")
                    return

                # Палитра изображения
                src_pal = img.getpalette()
                if src_pal is None or len(src_pal) < 15*3:   # нужно минимум до индекса 8
                    raise ValueError("PNG palette too small.")

                # Берём цвета из индексов 3,4,8 изображения (как в Java)
                new_colors = self.battleFloor.palette.colors[:]  # копируем текущую палитру пола
                for idx in [3, 4, 8]:
                    r, g, b = src_pal[idx*3], src_pal[idx*3+1], src_pal[idx*3+2]
                    cr, cg, cb = r // 16 * 17, g // 16 * 17, b // 16 * 17
                    new_colors[idx] = "#%02x%02x%02x" % (cr, cg, cb)

                pal = data.Palette()
                pal.init(new_colors)
                self.palette = pal
                self.battleFloor.palette = pal
                if shiboken6.isValid(self.editPanel):
                    self.editPanel.palette = pal

                # Пиксели остаются без изменений (индексы те же)
                indexes = list(img.getdata())
                pixels_hex = "".join(["%x" % idx for idx in indexes])
                pixel_rows = [pixels_hex[i:i+w] for i in range(0, w*h, w)]

                # Обновляем тайлы кадра
                self.curFrame.convertFromPixelRows(pixel_rows)
                tw = w // 8
                th = h // 8
                newtiles = [None] * len(self.curFrame.tiles)
                order = self.curFrame.getTileOrder(tw, th)
                for i in range(len(newtiles)):
                    newtiles[order[i]] = self.curFrame.tiles[i]
                self.curFrame.tiles = newtiles

                self.changeBattleFloor()
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
                tw = w // 8
                th = h // 8
                frame = self.curFrame
                order = frame.getTileOrder(tw, th)
                tiles = [frame.tiles[t] for t in order]
                pixels_flat = []
                for tRow in range(th):
                    for pRow in range(8):
                        row = "".join([tiles[tRow*tw+to].pixels[pRow] for to in range(tw)])
                        pixels_flat.extend([int(c, 16) for c in row])

                img = Image.new("P", (w, h))
                img.putdata(pixels_flat)

                palette_bytes = []
                for i in range(16):
                    c = self.battleFloor.palette.colors[i]
                    palette_bytes.extend([int(c[1:3],16), int(c[3:5],16), int(c[5:7],16)])
                palette_bytes += [0] * (768 - len(palette_bytes))
                img.putpalette(palette_bytes)

                img.save(fn, "PNG")   # без transparency
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

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
        """Обновляет стиль палитры: доступные цвета (3,4,8) с золотой рамкой."""
        palette = self.palette
        for c in range(len(self.colorPanels)):
            cp = self.colorPanels[c]
            if shiboken6.isValid(cp):
                if c in self.ALLOWED_COLORS:
                    border = "2px solid #FFD700"  # золотая рамка для активных
                else:
                    border = "1px solid #555"
                cp.setStyleSheet(
                    f"background-color: {palette.colors[c]}; border: {border}; border-radius: 3px;"
                )
                cp.update()
        if shiboken6.isValid(self.editPanel):
            self.editPanel.palette = palette
            self.editPanel.update()

    def OnSelectBattleFloor(self, idx):
        self.changeBattleFloor(idx)

    def changeBattleFloor(self, num=None):
        if num is not None:
            if not self.rom.data["battle_floors"][num].loaded:
                self.rom.getBattleFloors(num, num)
            self.battleFloor = self.rom.data["battle_floors"][num]
            self.editPanel.width = 96
            self.editPanel.height = 32

        if not hasattr(self, 'battleFloor') or self.battleFloor is None:
            return

        self.palette = self.battleFloor.palette
        if shiboken6.isValid(self.editPanel):
            self.editPanel.palette = self.palette
        self.changeColors()

        frame = self.battleFloor.frame
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
            self.updateModifiedIndicator(self.battleFloor.modified)
            self.editPanel.update()

    def changeAnim(self, num):
        self.animCur = num
        self.timer.start(self.animDelays[num])

    def refreshPixels(self):
        pass

    def getCurrentSpriteObject(self):
        return self.battleFloor

    def getCurrentData(self):
        return self.battleFloor

    changeSelection = changeBattleFloor

    curFrame = property(lambda self: self.battleFloor.frame)
    curPalette = property(lambda self: self.battleFloor.palette)

    # Метод для синхронизации тайлов после рисования (вызывается из SpritePanel.OnEdit)
    def _updateFrameTiles(self, frame):
        w, h = self.editPanel.width, self.editPanel.height
        frame.convertFromPixelRows(self.editPanel.pixels)
        tw = w // 8
        th = h // 8
        newtiles = [None] * len(frame.tiles)
        order = frame.getTileOrder(tw, th)
        for i in range(len(newtiles)):
            newtiles[order[i]] = frame.tiles[i]
        frame.tiles = newtiles
        frame.raw_pixels = "".join(self.editPanel.pixels)