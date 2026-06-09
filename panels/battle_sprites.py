import math, binascii
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel,
    QPushButton, QComboBox, QSpinBox, QRadioButton, QCheckBox,
    QListWidget, QFileDialog, QMessageBox, QDialog, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage, QColor
import data
from PIL import Image
import rompanel
import shiboken6

h2i = lambda i: int(i, 16)

class BattleSpritePanel(rompanel.ROMPanel):
    frameTitle = "Battle Sprite Editor"
    canMaximize = True

    def init(self):
        self.palette = self.rom.getDataByName("palettes", "Sprite & UI Palette")
        self.side = 0
        self.frame = 0
        self.mode = 0
        self.color_left = 0
        self.color_right = 0
        self.animFrames = []
        self.curFrameIdx = 0
        self.curPaletteIdx = 0
        self.current_scale = 3

        # ==================== SELECT SPRITE ====================
        sbs1 = QGroupBox("Select Battle Sprite")
        sbs1_layout = QVBoxLayout(sbs1)
        self.battleSpriteList = QComboBox()
        self.battleSpriteList.addItems([bs.name for bs in self.rom.data["battle_sprites"]])
        self.battleSpriteList.setCurrentIndex(0)
        sbs1_layout.addWidget(self.battleSpriteList)

        # ==================== PROPERTIES (UNIMPLEMENTED) ====================
        sbs2 = QGroupBox("Properties (UNIMPLEMENTED)")
        sbs2_layout = QVBoxLayout(sbs2)
        sbs2_layout.setAlignment(Qt.AlignCenter)

        animSpdText = QLabel("Anim Speed")
        self.animSpdCtrl = QSpinBox(); self.animSpdCtrl.setRange(0, 65535); self.animSpdCtrl.setFixedSize(65, 20)
        mystText = QLabel("???")
        self.mystCtrl = QSpinBox(); self.mystCtrl.setRange(0, 65535); self.mystCtrl.setFixedSize(65, 20)
        spellFrameText = QLabel("Spell Use Frame")
        self.spellFrameCtrl = QSpinBox(); self.spellFrameCtrl.setRange(0, 255); self.spellFrameCtrl.setFixedSize(65, 20)
        spellAnimText = QLabel("Spell Anim on Attack")
        self.spellAnimCtrl = QSpinBox(); self.spellAnimCtrl.setRange(0, 255); self.spellAnimCtrl.setFixedSize(65, 20)
        self.spellWaitCheck = QCheckBox(" Wait for spell anim")

        sbs2_layout.addWidget(animSpdText, alignment=Qt.AlignCenter)
        sbs2_layout.addWidget(self.animSpdCtrl, alignment=Qt.AlignCenter)
        sbs2_layout.addWidget(mystText, alignment=Qt.AlignCenter)
        sbs2_layout.addWidget(self.mystCtrl, alignment=Qt.AlignCenter)
        sbs2_layout.addWidget(spellFrameText, alignment=Qt.AlignCenter)
        sbs2_layout.addWidget(self.spellFrameCtrl, alignment=Qt.AlignCenter)
        sbs2_layout.addWidget(spellAnimText, alignment=Qt.AlignCenter)
        sbs2_layout.addWidget(self.spellAnimCtrl, alignment=Qt.AlignCenter)
        sbs2_layout.addWidget(self.spellWaitCheck, alignment=Qt.AlignCenter)

        # ==================== PALETTE AND FRAME ====================
        sbs3 = QGroupBox("Palette and Frame")
        sbs3_layout = QVBoxLayout(sbs3)

        self.frameList = QComboBox()
        self.frameList.setFixedWidth(100)
        self.paletteList = QComboBox()
        self.paletteList.setFixedWidth(100)

        sbs3_layout.addWidget(self.frameList)
        sbs3_layout.addWidget(self.paletteList)

        # ==================== EDIT ====================
        sbs4 = QGroupBox("Edit")
        sbs4_layout = QHBoxLayout(sbs4)

        text1 = QLabel("Colors")
        text2 = QLabel("Sprite (Color 0 = trans)")

        self.editPanel = rompanel.SpritePanel(self, None, 128, 96, self.palette, scale=self.current_scale, bg=16, func="edit")

        self.colorPanels = []
        for p in range(16):
            self.colorPanels.append(rompanel.ColorPanel2(self, None, "#000000", num=p))

        self.changeColors()

        self.importButton = QPushButton("Import")
        self.importButton.setFixedSize(60, 22)
        self.exportButton = QPushButton("Export")
        self.exportButton.setFixedSize(60, 22)

        self.selectedColorLeft = QLabel()
        self.selectedColorLeft.setFixedSize(32, 32)
        self.selectedColorLeft.setStyleSheet("border: 2px solid #555; border-radius: 4px; background-color: #000;")
        self.selectedColorLeft.color = 0

        self.selectedColorRight = QLabel()
        self.selectedColorRight.setFixedSize(32, 32)
        self.selectedColorRight.setStyleSheet("border: 2px solid #555; border-radius: 4px; background-color: #000;")
        self.selectedColorRight.color = 0

        sbs4left = QVBoxLayout()
        sbs4left.setContentsMargins(4, 4, 4, 4)
        sbs4left.setSpacing(6)

        # ---------- Палитра ----------
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

        # Индикаторы L и R вертикально справа от палитры
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

        self.zoomLabel = QLabel("Zoom")
        self.zoomRadios = {}
        zoomSizer = QHBoxLayout()
        for scale_val in [3, 5, 7, 8]:
            rb = QRadioButton(f"{scale_val}x")
            if scale_val == self.current_scale:
                rb.setChecked(True)
            self.zoomRadios[scale_val] = rb
            zoomSizer.addWidget(rb)
            rb.toggled.connect(lambda checked, s=scale_val: self.changeZoom(s))

        sbs4left.addWidget(text1, alignment=Qt.AlignCenter)
        sbs4left.addLayout(colorSizer)
        
        sbs4left.addWidget(self.importButton, alignment=Qt.AlignCenter)
        sbs4left.addWidget(self.exportButton, alignment=Qt.AlignCenter)
        sbs4left.addSpacing(4)
        sbs4left.addWidget(self.zoomLabel, alignment=Qt.AlignCenter)
        sbs4left.addLayout(zoomSizer)

        sbs4mid = QVBoxLayout()
        sbs4mid.addWidget(text2, alignment=Qt.AlignCenter)

        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(False)
        self.scrollArea.setWidget(self.editPanel)
        self.scrollArea.setAlignment(Qt.AlignCenter)
        sbs4mid.addWidget(self.scrollArea, alignment=Qt.AlignCenter)

        sbs4_layout.addLayout(sbs4left, 0)
        sbs4_layout.addLayout(sbs4mid, 1)

        # ==================== EDIT/PREVIEW ANIMATION ====================
        sbs5 = QGroupBox("Edit/Preview Animation (UNIMPLEMENTED)")
        sbs5_layout = QHBoxLayout(sbs5)

        sbs5left = QVBoxLayout()
        self.animList = QComboBox()
        self.animList.addItems(["Idle", "Attack", "Defend"])
        self.animList.setCurrentIndex(0); self.animList.setFixedWidth(100)

        self.animPanel = rompanel.SpritePanel(self, None, 128, 96, self.palette, scale=1, bg=None, edit=False)
        self.animDelays = [250, 150, 50, 50, 50, 50]
        self.animFrameIdx = 0; self.animCur = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.TimerTest)
        self.changeAnim(0)

        sbs5left.addWidget(self.animPanel, alignment=Qt.AlignCenter)
        sbs5left.addWidget(self.animList, alignment=Qt.AlignCenter)

        sbs5mid = QVBoxLayout()
        self.animFrameListBox = QListWidget(); self.animFrameListBox.setFixedSize(120, 100)
        self.animAddButton = QPushButton("Add"); self.animAddButton.setFixedSize(40, 20)
        self.animCopyButton = QPushButton("Copy"); self.animCopyButton.setFixedSize(40, 20)
        self.animDelButton = QPushButton("Del"); self.animDelButton.setFixedSize(40, 20)

        sbs5midButtonSizer = QHBoxLayout()
        sbs5midButtonSizer.addWidget(self.animAddButton)
        sbs5midButtonSizer.addWidget(self.animCopyButton)
        sbs5midButtonSizer.addWidget(self.animDelButton)

        sbs5mid.addWidget(self.animFrameListBox)
        sbs5mid.addLayout(sbs5midButtonSizer)

        sbs5right = QGridLayout()
        animPropsText1 = QLabel("Frame"); animPropsText2 = QLabel("Duration")
        animPropsText3 = QLabel("Char X"); animPropsText4 = QLabel("Char Y")
        animPropsText5 = QLabel("Weapon X"); animPropsText6 = QLabel("Weapon Y")

        self.animZCheck = QCheckBox(" Weapon in front of character")
        self.animFrameCombo = QComboBox(); self.animFrameCombo.setFixedWidth(100)
        self.animDurCtrl = QSpinBox(); self.animDurCtrl.setRange(0, 255); self.animDurCtrl.setFixedSize(65, 20)
        self.animCharXCtrl = QSpinBox(); self.animCharXCtrl.setRange(0, 255); self.animCharXCtrl.setFixedSize(65, 20)
        self.animCharYCtrl = QSpinBox(); self.animCharYCtrl.setRange(0, 255); self.animCharYCtrl.setFixedSize(65, 20)
        self.animWeaponXCtrl = QSpinBox(); self.animWeaponXCtrl.setRange(0, 255); self.animWeaponXCtrl.setFixedSize(65, 20)
        self.animWeaponYCtrl = QSpinBox(); self.animWeaponYCtrl.setRange(0, 255); self.animWeaponYCtrl.setFixedSize(65, 20)

        sbs5right.addWidget(animPropsText1, 0, 0, Qt.AlignRight)
        sbs5right.addWidget(animPropsText2, 1, 0, Qt.AlignRight)
        sbs5right.addWidget(animPropsText3, 2, 0, Qt.AlignRight)
        sbs5right.addWidget(animPropsText4, 3, 0, Qt.AlignRight)
        sbs5right.addWidget(animPropsText5, 4, 0, Qt.AlignRight)
        sbs5right.addWidget(animPropsText6, 5, 0, Qt.AlignRight)

        sbs5right.addWidget(self.animFrameCombo, 0, 1)
        sbs5right.addWidget(self.animDurCtrl, 1, 1)
        sbs5right.addWidget(self.animCharXCtrl, 2, 1)
        sbs5right.addWidget(self.animCharYCtrl, 3, 1)
        sbs5right.addWidget(self.animWeaponXCtrl, 4, 1)
        sbs5right.addWidget(self.animWeaponYCtrl, 5, 1)
        sbs5right.addWidget(self.animZCheck, 6, 0, 1, 2)

        sbs5wf = QVBoxLayout()
        animWSprText = QLabel("Weapon Direction"); animWSprText.setAlignment(Qt.AlignCenter)

        self.weaponAnglePanel = QWidget(); self.weaponAnglePanel.setFixedSize(100, 100)
        self.animWeaponAngleRadios = {}
        radius = 40; center = radius + 2
        first = True
        for a in range(0, 360, 30):
            rx = int(math.cos(math.radians(a)) * radius + center)
            ry = int(-math.sin(math.radians(a)) * radius + center)
            rb = QRadioButton(self.weaponAnglePanel)
            rb.move(rx, ry); rb.setFixedSize(16, 16)
            self.animWeaponAngleRadios[a] = rb
            if first: rb.setChecked(True); first = False

        sbs5wf.addWidget(animWSprText, alignment=Qt.AlignCenter)
        sbs5wf.addWidget(self.weaponAnglePanel, alignment=Qt.AlignCenter)

        sbs5_layout.addLayout(sbs5left)
        sbs5_layout.addSpacing(10)
        sbs5_layout.addLayout(sbs5mid)
        sbs5_layout.addSpacing(10)
        sbs5_layout.addLayout(sbs5right, 1)
        sbs5_layout.addSpacing(10)
        sbs5_layout.addLayout(sbs5wf, 1)

        # ==================== MAIN LAYOUT ====================
        midWidget = QWidget()
        midSizer = QHBoxLayout(midWidget)
        midRightSizer = QVBoxLayout()

        midSizer.addWidget(sbs4, 0)
        midRightSizer.addWidget(sbs3, 0)
        midRightSizer.addStretch(1)
        midRightSizer.addWidget(sbs2, 0)
        midSizer.addLayout(midRightSizer, 1)

        self.sizer.addWidget(sbs1, 0, 0, 1, 2)
        self.sizer.addWidget(midWidget, 1, 0)
        self.sizer.addWidget(sbs5, 2, 0)

        # Signals
        self.battleSpriteList.currentIndexChanged.connect(self.OnSelectBattleSprite)
        self.paletteList.currentIndexChanged.connect(self.OnSelectPalette)
        self.frameList.currentIndexChanged.connect(self.OnSelectFrame)
        self.importButton.clicked.connect(self.OnImportImage)
        self.exportButton.clicked.connect(self.OnExportImage)
        self.timer.timeout.connect(self.TimerTest)

        self.changeBattleSprite(0)

    # ---------- Methods ----------
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

    def OnSelectBattleSprite(self, idx):
        self.changeBattleSprite(idx)

    def OnImportImage(self):
        if not shiboken6.isValid(self.editPanel) or self.editPanel.bmp is None:
            return
        size = self.editPanel.bmp.size()
        w, h = size.width(), size.height()
        dlg = QFileDialog(self, f"Import {w}x{h} PNG (indexed, 16 colors)", "", "PNG files (*.png)")
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
                if shiboken6.isValid(self.animPanel):
                    self.animPanel.palette = pal
                self.palette = pal
                self.battleSprite.palettes[self.curPaletteIdx] = pal

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

                self.changeBattleSprite()
                self.updateAnimFrames()
                self.changeColors()
                self.modify()
            except Exception as e:
                import traceback
                QMessageBox.critical(self, "Import failed", f"Error: {str(e)}\n\n{traceback.format_exc()}")

    def OnExportImage(self):
        if not shiboken6.isValid(self.editPanel) or self.editPanel.bmp is None:
            return
        size = self.editPanel.bmp.size()
        w, h = size.width(), size.height()
        dlg = QFileDialog(self, f"Export 16-color {w}x{h} PNG", "", "PNG files (*.png)")
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        if dlg.exec() == QDialog.Accepted:
            fn = dlg.selectedFiles()[0]
            # Индексированное изображение (16 цветов)
            img = Image.new("P", (w, h))
            img.putdata([int(a, 16) for pr in self.editPanel.pixels for a in pr])
            # Палитра RGB (альфу не сохраняем в палитре – прозрачность задаём отдельно)
            p = [v for rt in self.editPanel.palette.rgbaTuples() for v in rt[:3]]
            p += [0] * (768 - len(p))
            img.putpalette(p)
            # Сохраняем с прозрачностью для индекса 0
            img.save(fn, "PNG", transparency=0)

    def OnShow(self, event=None):
        self.changeColors()
        if hasattr(self, 'selectedColorLeft') and shiboken6.isValid(self.selectedColorLeft):
            self.selectedColorLeft.setStyleSheet(
                f"border: 2px solid #555; border-radius: 4px; background-color: {self.palette.colors[self.color_left]};"
            )
        if hasattr(self, 'selectedColorRight') and shiboken6.isValid(self.selectedColorRight):
            self.selectedColorRight.setStyleSheet(
                f"border: 2px solid #555; border-radius: 4px; background-color: {self.palette.colors[self.color_right]};"
            )

    def TimerTest(self):
        self.animFrameIdx ^= 1
        self.changeAnimBattleSprite()

    def changeColors(self):
        palette = self.palette
        for c in range(len(self.colorPanels)):
            if shiboken6.isValid(self.colorPanels[c]):
                self.colorPanels[c].setStyleSheet(
                    f"background-color: {palette.colors[c]}; border: none; border-radius: 3px;"
                )
                self.colorPanels[c].update()

    def refreshPixels(self):
        pass

    def OnSelectPalette(self, idx):
        self.curPaletteIdx = idx
        self.changeBattleSprite()
        self.changeAnimBattleSprite(True)

    def OnSelectFrame(self, idx):
        self.curFrameIdx = idx
        self.changeBattleSprite()

    def changeZoom(self, scale):
        if not hasattr(self, 'editPanel') or not shiboken6.isValid(self.editPanel):
            return
        current_pixels = self.editPanel.pixels
        w, h = self.editPanel.width, self.editPanel.height
        old_ep = self.editPanel
        self.editPanel = rompanel.SpritePanel(self, None, w, h, self.palette, scale=scale, bg=16, func="edit")
        self.scrollArea.takeWidget()
        old_ep.deleteLater()
        self.scrollArea.setWidget(self.editPanel)
        self.editPanel.refreshSprite(current_pixels, force=True)
        self.editPanel.update()
        self.current_scale = scale

    def changeBattleSprite(self, num=None):
        if num is not None:
            if not self.rom.data["battle_sprites"][num].loaded:
                self.rom.getBattleSprites(num, num)
            self.curPaletteIdx = 0
            self.curFrameIdx = 0
            self.battleSprite = self.rom.data["battle_sprites"][num]

            if num < self.rom.sectionData["battle_sprites"][2][0]:
                new_w = 96
            else:
                new_w = 128
            new_h = 96

            self.editPanel.width = new_w
            self.editPanel.height = new_h
            self.animPanel.width = new_w
            self.animPanel.height = new_h

            if shiboken6.isValid(self.editPanel):
                self.editPanel.setFixedSize(
                    int(new_w * self.editPanel.scale + self.editPanel.xpad * 2),
                    int(new_h * self.editPanel.scale + self.editPanel.ypad * 2)
                )
            if shiboken6.isValid(self.animPanel):
                self.animPanel.setFixedSize(
                    int(new_w * self.animPanel.scale + self.animPanel.xpad * 2),
                    int(new_h * self.animPanel.scale + self.animPanel.ypad * 2)
                )

            self.updateAnimFrames()
            self.animSpdCtrl.setValue(self.battleSprite.animSpeed)
            self.mystCtrl.setValue(int(self.battleSprite.myst, 16))

            self.frameList.clear()
            self.frameList.addItems(["Frame %i" % i for i, p in enumerate(self.battleSprite.frames)])
            self.frameList.setCurrentIndex(self.curFrameIdx)

            self.paletteList.clear()
            self.paletteList.addItems(["Palette %i" % i for i, p in enumerate(self.battleSprite.palettes)])
            self.paletteList.setCurrentIndex(self.curPaletteIdx)

        self.palette = self.curPalette
        if shiboken6.isValid(self.editPanel):
            self.editPanel.palette = self.palette
        if shiboken6.isValid(self.animPanel):
            self.animPanel.palette = self.palette

        self.changeColors()

        if shiboken6.isValid(self.editPanel):
            tw = self.editPanel.width // 8
            th = self.editPanel.height // 8
            pixels = self.curFrame.getPixelRows(tw, th)
            self.editPanel.refreshSprite(pixels, force=True)
            self.editPanel.update()

        self.updateModifiedIndicator(self.battleSprite.modified)

    def changeAnim(self, num):
        self.animCur = num
        self.timer.start(self.animDelays[num])

    def changeAnimBattleSprite(self, force=False):
        if shiboken6.isValid(self.animPanel):
            self.animPanel.refreshSprite(self.animFrame, force=force)
            self.animPanel.update()

    def updateAnimFrames(self):
        if not shiboken6.isValid(self.animPanel):
            return
        tw = self.animPanel.width // 8
        th = self.animPanel.height // 8
        self.animFrames = []
        for f in self.battleSprite.frames:
            self.animFrames.append(f.getPixelRows(tw, th))

    def getCurrentSpriteObject(self):
        return self.battleSprite

    def getCurrentData(self):
        return self.battleSprite

    changeSelection = changeBattleSprite

    curFrame = property(lambda self: self.battleSprite.frames[self.curFrameIdx])
    curPalette = property(lambda self: self.battleSprite.palettes[self.curPaletteIdx])
    animFrame = property(lambda self: self.animFrames[self.animFrameIdx])