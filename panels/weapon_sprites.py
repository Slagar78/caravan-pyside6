import binascii
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QComboBox, QFileDialog, QMessageBox, QDialog
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage, QColor, QPainter, QPen
import data
from PIL import Image
import rompanel
import shiboken6

h2i = lambda i: int(i, 16)

# =============================================================================
# CRAM color conversion (Sega Mega Drive) – точный аналог PaletteDecoder.java
# =============================================================================
CRAM_VALUE_MAP = {
    0: 0,
    2: 52,
    4: 87,
    6: 116,
    8: 144,
    10: 172,
    12: 206,
    14: 255
}

CRAM_OFFSET_ARRAY = [17, 63, 96, 125, 153, 183, 222, 999]

def brightness_to_cram_value(brightness):
    for i, offset in enumerate(CRAM_OFFSET_ARRAY):
        if brightness <= offset:
            return CRAM_VALUE_MAP[i * 2]
    return 0

def conform_color_to_cram(r, g, b):
    return brightness_to_cram_value(r), brightness_to_cram_value(g), brightness_to_cram_value(b)

# =============================================================================

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
        text2 = QLabel("Sprite (All 4 Frames, Color 0 = transparent)")

        # Панель для отображения всех 4 кадров (сетка 2x2)
        self.framesPanel = QWidget()
        framesGrid = QGridLayout(self.framesPanel)
        framesGrid.setContentsMargins(0, 0, 0, 0)
        framesGrid.setSpacing(4)
        self.framePanels = []
        for i in range(4):
            fp = rompanel.SpritePanel(self.framesPanel, None, 64, 64, self.palette, scale=2, bg=16)
            fp.frameIndex = i
            fp.mousePressEvent = lambda event, idx=i: self._onFrameClicked(idx)
            self.framePanels.append(fp)
            framesGrid.addWidget(fp, i // 2, i % 2)

        # Отдельная панель для редактирования текущего кадра (увеличенная)
        self.editPanel = rompanel.SpritePanel(self, None, 8*8, 8*8, self.palette, scale=4, bg=16, func="edit")

        self.colorPanels = []
        for p in range(16):
            self.colorPanels.append(rompanel.ColorPanel2(self, None, "#000000", num=p))

        self.changeColors()

        self.importButton = QPushButton("Import")
        self.importButton.setFixedSize(40, 20)
        self.importButton.setEnabled(True)   # теперь активно
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
        sbs4mid.addWidget(self.framesPanel, 0, Qt.AlignCenter)
        sbs4mid.addWidget(self.editPanel, 0, Qt.AlignCenter)

        sbs4_layout.addLayout(sbs4left, 0)
        sbs4_layout.addLayout(sbs4mid, 1)

        # Компоновка
        topSizer = QHBoxLayout()
        topLeftSizer = QVBoxLayout()
        topLeftSizer.addWidget(weaponLabel)
        topLeftSizer.addWidget(self.weaponSpriteList)
        topLeftSizer.addWidget(sbs3)

        topSizer.addLayout(topLeftSizer)
        topSizer.addWidget(sbs4, 1)

        self.sizer.addLayout(topSizer, 0, 0, 1, 2)

        # Таймер анимации
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

    # ========== Методы ==========
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
        if not hasattr(self, 'weaponSprite') or self.weaponSprite is None:
            return

        size = (self.editPanel.width, self.editPanel.height)
        dlg = QFileDialog(self, f"Import 16-color {size[0]}x{size[1]} GIF", "",
                          "GIF files (*.gif)")
        dlg.setFileMode(QFileDialog.ExistingFile)
        if dlg.exec() == QDialog.Accepted:
            fn = dlg.selectedFiles()[0]
            try:
                img = Image.open(fn)   # не конвертируем, оставляем как есть
                if img.size != size:
                    QMessageBox.warning(self, "Error", 
                        f"{fn} is {img.size[0]}x{img.size[1]} and should be {size[0]}x{size[1]}.")
                    return

                # Если изображение индексированное (GIF), читаем палитру и индексы
                if img.mode == "P":
                    img_palette = img.getpalette()
                    if img_palette is None:
                        raise ValueError("No palette in GIF")
                    # Преобразуем палитру в CRAM (порядок сохраняется)
                    cram_cols = []
                    for i in range(0, 48, 3):
                        r, g, b = img_palette[i], img_palette[i+1], img_palette[i+2]
                        cr, cg, cb = conform_color_to_cram(r, g, b)
                        cram_cols.append("#%02x%02x%02x" % (cr, cg, cb))
                    # Дополняем до 16 цветов, если меньше
                    while len(cram_cols) < 16:
                        cram_cols.append("#000000")

                    pal = data.Palette()
                    pal.init(cram_cols[:16])

                    # Пиксели: индексы 0–15
                    imgdata = list(img.getdata())
                    pixels_str = "".join(["%x" % d for d in imgdata])
                    pixel_rows = [pixels_str[i:i+size[0]] for i in range(0, size[0]*size[1], size[0])]
                else:
                    # Если не индексированное, то конвертируем (старый способ)
                    img = img.convert("RGB")
                    imgdata = list(img.getdata())
                    pixel_cram = [conform_color_to_cram(r, g, b) for (r,g,b) in imgdata]
                    unique_cram = list(dict.fromkeys(pixel_cram))
                    if len(unique_cram) > 16:
                        QMessageBox.warning(self, "Error", "Image has more than 16 unique CRAM colors.")
                        return
                    while len(unique_cram) < 16:
                        unique_cram.append((0,0,0))
                    cram_to_idx = {c: i for i, c in enumerate(unique_cram)}
                    indexed = [cram_to_idx[c] for c in pixel_cram]
                    pixels_str = "".join(["%x" % d for d in indexed])
                    pixel_rows = [pixels_str[i:i+size[0]] for i in range(0, size[0]*size[1], size[0])]
                    cols = ["#%02x%02x%02x" % c for c in unique_cram]
                    pal = data.Palette()
                    pal.init(cols)

                # Применяем к выбранному кадру
                self.weaponSprite.palettes[self.curPaletteIdx] = pal
                frame = self.weaponSprite.frames[self.curFrameIdx]
                frame.convertFromPixelRows(pixel_rows)
                newtiles = [None] * len(frame.tiles)
                order = frame.getTileOrder(size[0]//8, size[1]//8)
                for i in range(len(newtiles)):
                    newtiles[order[i]] = frame.tiles[i]
                frame.tiles = newtiles

                self.changeWeaponSprite()
                self.changeColors()
                self.modify()
            except Exception as e:
                QMessageBox.critical(self, "Import Error", str(e))

    def OnExportImage(self):
        if not hasattr(self, 'weaponSprite') or self.weaponSprite is None:
            return
        frame = self.weaponSprite.frames[self.curFrameIdx]
        if not frame or not frame.tiles:
            return

        size = (self.editPanel.width, self.editPanel.height)
        dlg = QFileDialog(self, f"Export 16-color {size[0]}x{size[1]} GIF", "", "GIF files (*.gif)")
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        if dlg.exec() == QDialog.Accepted:
            fn = dlg.selectedFiles()[0]
            try:
                # Собираем индексы пикселей (0–15) из тайлов
                pixels_flat = []
                tw = size[0] // 8
                th = size[1] // 8
                order = frame.getTileOrder(tw, th)
                tiles = [frame.tiles[t] for t in order]
                for tRow in range(th):
                    for pRow in range(8):
                        row = "".join([tiles[tRow*tw+to].pixels[pRow] for to in range(tw)])
                        pixels_flat.extend([int(c, 16) for c in row])

                # Создаём индексированное изображение
                img = Image.new("P", size)
                img.putdata(pixels_flat)

                # Фиксированная палитра 16 цветов (как есть, без перестановок)
                palette = self.curPalette
                flat_pal = []
                for color_str in palette.colors[:16]:
                    r = int(color_str[1:3], 16)
                    g = int(color_str[3:5], 16)
                    b = int(color_str[5:7], 16)
                    flat_pal.extend([r, g, b])
                # Дополняем до 768 байт (256 цветов)
                flat_pal += [0] * (768 - len(flat_pal))
                img.putpalette(flat_pal)

                # Сохраняем без оптимизации, чтобы палитра не переупорядочивалась
                img.save(fn, "GIF", optimize=False)
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

    def TimerTest(self):
        self.animFrame ^= 1
        # Можно добавить переключение отображаемого кадра в preview, но пока оставим

    def changeColors(self):
        palette = self.palette
        for c in range(len(self.colorPanels)):
            cp = self.colorPanels[c]
            if shiboken6.isValid(cp):
                cp.setStyleSheet(f"background-color: {palette.colors[c]};")
                cp.update()
        # Обновляем панели кадров
        for fp in self.framePanels:
            fp.palette = palette
            fp.update()
        self.editPanel.palette = palette
        self.editPanel.update()

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

    def _onFrameClicked(self, idx):
        """Выбор кадра для редактирования кликом по preview"""
        self.curFrameIdx = idx
        self.frameList.setCurrentIndex(idx)
        self.changeWeaponSprite()

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
        self.changeColors()

        # Обновляем все 4 панели кадров
        for i, fp in enumerate(self.framePanels):
            if i < len(self.weaponSprite.frames):
                frame = self.weaponSprite.frames[i]
                pixels = []
                tw = fp.width // 8
                th = fp.height // 8
                if frame.tiles:
                    order = frame.getTileOrder(tw, th)
                    tiles = [frame.tiles[t] for t in order]
                    for tRow in range(th):
                        for pRow in range(8):
                            row = "".join([tiles[tRow*tw+to].pixels[pRow] for to in range(tw)])
                            pixels.append(row)
                fp.refreshSprite(pixels, force=True)
                # Подсветка выбранного кадра
                if i == self.curFrameIdx:
                    fp.setStyleSheet("border: 2px solid blue;")
                else:
                    fp.setStyleSheet("")
                fp.update()
            else:
                fp.refreshSprite([])

        # Обновляем панель редактирования
        frame = self.weaponSprite.frames[self.curFrameIdx]
        if frame and frame.tiles:
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
                self.editPanel.update()

        self.updateModifiedIndicator(self.weaponSprite.modified)
        self.refreshPixels()

    def changeAnim(self, num):
        self.animCur = num
        self.timer.start(self.animDelays[num])

    def changeAnimWeaponSprite(self):
        if hasattr(self, 'animPanel') and shiboken6.isValid(self.animPanel):
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