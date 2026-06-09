import binascii
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QComboBox, QSlider, QFileDialog, QMessageBox, QDialog
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage, QColor
import data
from PIL import Image
import rompanel
import shiboken6

h2i = lambda i: int(i, 16)

class SpellAnimationPanel(rompanel.ROMPanel):

    frameTitle = "Spell Animation Editor"

    def init(self):
        self.palette = self.rom.getDataByName("palettes", "Sprite & UI Palette")
        self.mode = 0
        self.color_left = 0
        self.color_right = 0
        self.curFrameIdx = 0
        self.curPaletteIdx = 0

        # ---------- Выбор анимации ----------
        spell_label = QLabel("Spell Animation:")
        self.spellAnimList = QComboBox()
        self.spellAnimList.addItems([sa.name for sa in self.rom.data["spell_animations"]])
        self.spellAnimList.setCurrentIndex(0)

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
        text2 = QLabel("Sprite (Color 0 = transparent)")

        self.editPanel = rompanel.SpritePanel(self, None, 16*8, 16*8, self.palette, scale=2, bg=16, func="edit")

        self.colorPanels = []
        for p in range(16):
            self.colorPanels.append(rompanel.ColorPanel2(self, None, "#000000", num=p))

        self.changeColors()

        self.importButton = QPushButton("Import")
        self.importButton.setFixedSize(40, 20)
        self.exportButton = QPushButton("Export")
        self.exportButton.setFixedSize(40, 20)

        # Левая часть (цвета + кнопки)
        sbs4left = QVBoxLayout()
        colorSizer = QGridLayout()
        for i, cp in enumerate(self.colorPanels):
            colorSizer.addWidget(cp, i // 2, i % 2)

        sbs4left.addWidget(text1, 0, Qt.AlignCenter)
        sbs4left.addLayout(colorSizer)
        sbs4left.addWidget(self.importButton, 0, Qt.AlignCenter)
        sbs4left.addWidget(self.exportButton, 0, Qt.AlignCenter)

        # Центр (спрайт)
        sbs4mid = QVBoxLayout()
        sbs4mid.addWidget(text2, 0, Qt.AlignCenter)
        sbs4mid.addWidget(self.editPanel, 0, Qt.AlignCenter)

        sbs4_layout.addLayout(sbs4left, 0)
        sbs4_layout.addLayout(sbs4mid, 1)

        # ---------- Компоновка ----------
        topSizer = QHBoxLayout()
        topLeftSizer = QVBoxLayout()
        topLeftSizer.addWidget(spell_label)
        topLeftSizer.addWidget(self.spellAnimList)
        topLeftSizer.addWidget(sbs3)

        topSizer.addLayout(topLeftSizer)
        topSizer.addWidget(sbs4, 1)   # добавляем виджет целиком, а не его лейаут

        self.sizer.addLayout(topSizer, 0, 0, 1, 2)

        # Таймер анимации (как в оригинале)
        self.animFrame = 0
        self.animCur = 0
        self.animDelays = [250, 150, 50, 50, 50, 50]
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.TimerTest)
        self.timer.start(self.animDelays[0])

        self.changeSpellAnim(0)

        # Сигналы
        self.spellAnimList.currentIndexChanged.connect(self.OnSelectSpellAnim)
        self.paletteList.currentIndexChanged.connect(self.OnSelectPalette)
        self.frameList.currentIndexChanged.connect(self.OnSelectFrame)
        self.importButton.clicked.connect(self.OnImportImage)
        self.exportButton.clicked.connect(self.OnExportImage)

    # ========== Методы оригинала ==========
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
                    QMessageBox.warning(self, f"Image is {img.size[0]}x{img.size[1]}, need {w}x{h}.",
                                        self.parent.baseTitle + " -- Error")
                    return

                raw_palette = img.getpalette()
                if raw_palette is None or len(raw_palette) < 48:
                    raw_palette = list(raw_palette or [])
                    raw_palette += [0] * (48 - len(raw_palette))

                cols = []
                for i in range(0, 48, 3):
                    r, g, b = raw_palette[i], raw_palette[i+1], raw_palette[i+2]
                    cr, cg, cb = r // 16 * 17, g // 16 * 17, b // 16 * 17
                    cols.append("#%02x%02x%02x" % (cr, cg, cb))

                pal = data.Palette()
                pal.init(cols)
                self.editPanel.palette = pal
                self.palette = pal
                self.spellAnim.palette = pal

                indexes = list(img.getdata())
                pixels_hex = "".join(["%x" % idx for idx in indexes])
                pixel_rows = [pixels_hex[i:i+w] for i in range(0, w*h, w)]

                self.curFrame.convertFromPixelRows(pixel_rows)
                tw = w // 8
                th = h // 8
                newtiles = [None] * len(self.curFrame.tiles)
                order = self.curFrame.getTileOrder(tw, th)
                for i in range(len(newtiles)):
                    newtiles[order[i]] = self.curFrame.tiles[i]
                self.curFrame.tiles = newtiles

                self.changeSpellAnim()
                self.changeColors()
                self.modify()
            except Exception as e:
                QMessageBox.warning(self, f"Import failed: {e}", self.parent.baseTitle + " -- Error")

    def OnExportImage(self):
        if not shiboken6.isValid(self.editPanel):
            return
        size = self.editPanel.bmp.size()
        w, h = size.width(), size.height()
        dlg = QFileDialog(self, f"Export {w}x{h} PNG", "", "PNG files (*.png)")
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        if dlg.exec() == QDialog.Accepted:
            fn = dlg.selectedFiles()[0]
            img = Image.new("P", (w, h))
            img.putdata([int(a, 16) for pr in self.editPanel.pixels for a in pr])
            p = [v for rt in self.editPanel.palette.rgbaTuples() for v in rt[:3]]
            p += [0] * (768 - len(p))
            img.putpalette(p)
            img.save(fn, "PNG", transparency=0)

    def TimerTest(self):
        self.animFrame ^= 1

    def OnShow(self):
        for p in range(16):
            if p < len(self.colorPanels):
                cp = self.colorPanels[p]
                if shiboken6.isValid(cp):
                    cp.setStyleSheet(f"background-color: {self.palette.colors[p]};")
                    cp.update()

    def changeColors(self):
        palette = self.palette
        for c in range(len(self.colorPanels)):
            cp = self.colorPanels[c]
            if shiboken6.isValid(cp):
                cp.setStyleSheet(f"background-color: {palette.colors[c]};")
                cp.update()
        if shiboken6.isValid(self.editPanel):
            self.editPanel.palette = palette
            self.editPanel.update()

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

    def refreshPixels(self):
        pass

    def OnSelectSpellAnim(self, idx):
        self.changeSpellAnim(idx)

    def changeSpellAnim(self, num=None):
        if num is not None:
            if not self.rom.data["spell_animations"][num].loaded:
                self.rom.getSpellAnimations(num, num)
            self.spellAnim = self.rom.data["spell_animations"][num]
            self.curPaletteIdx = 0
            self.curFrameIdx = 0
            self.frameList.clear()
            self.frameList.addItems(["Frame %i" % i for i in range(1)])
            self.frameList.setCurrentIndex(0)
            self.paletteList.clear()
            self.paletteList.addItems(["Palette %i" % i for i in range(1)])
            self.paletteList.setCurrentIndex(0)

        if not hasattr(self, 'spellAnim') or self.spellAnim is None:
            return

        self.palette = self.curPalette
        if shiboken6.isValid(self.editPanel):
            self.editPanel.palette = self.palette
        self.changeColors()

        frame = self.spellAnim.frame
        if not frame or not frame.tiles:
            return

        # При необходимости дополняем тайлы до нужного количества (16×16 = 256)
        tw = self.editPanel.width // 8
        th = self.editPanel.height // 8
        total_needed = tw * th
        while len(frame.tiles) < total_needed:
            empty_tile = data.Tile("Empty")
            empty_tile.init(["0" * 8 for _ in range(8)])
            frame.tiles.append(empty_tile)

        order = frame.getTileOrder(tw, th)
        tiles = [frame.tiles[t] for t in order]

        pixels = []
        for tRow in range(th):
            for pRow in range(8):
                row = "".join([tiles[tRow*tw+to].pixels[pRow] for to in range(tw)])
                pixels.append(row)

        if shiboken6.isValid(self.editPanel):
            self.editPanel.refreshSprite(pixels, force=True)
            self.updateModifiedIndicator(self.spellAnim.modified)
            self.editPanel.update()
        self.refreshPixels()

    def changeAnim(self, num):
        self.animCur = num
        self.timer.start(self.animDelays[num])
        
    def getCurrentSpriteObject(self):
        return self.spellAnim

    def getCurrentData(self):
        return self.spellAnim

    changeSelection = changeSpellAnim

    curFrame = property(lambda self: self.spellAnim.frame)
    curPalette = property(lambda self: self.spellAnim.palette)