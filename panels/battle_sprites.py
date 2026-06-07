import math
import binascii
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QRadioButton, QCheckBox,
    QListWidget, QFileDialog, QMessageBox
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

        # ---------- Properties (Unimplemented) ----------
        sbs2 = QVBoxLayout()
        sbs2_widget = QWidget()
        sbs2_widget.setLayout(sbs2)                              # <-- исправлено
        sbs2_widget.setStyleSheet("border: 1px solid black;")

        animSpdText = QLabel("Anim Speed")
        self.animSpdCtrl = QSpinBox(); self.animSpdCtrl.setRange(0, 65535)
        mystText = QLabel("???")
        self.mystCtrl = QSpinBox(); self.mystCtrl.setRange(0, 65535)
        spellFrameText = QLabel("Spell Use Frame")
        self.spellFrameCtrl = QSpinBox(); self.spellFrameCtrl.setRange(0, 255)
        spellAnimText = QLabel("Spell Anim on Attack")
        self.spellAnimCtrl = QSpinBox(); self.spellAnimCtrl.setRange(0, 255)
        self.spellWaitCheck = QCheckBox(" Wait for spell anim")

        sbs2.addWidget(animSpdText, 0, Qt.AlignCenter)
        sbs2.addWidget(self.animSpdCtrl, 0, Qt.AlignCenter)
        sbs2.addWidget(mystText, 0, Qt.AlignCenter)
        sbs2.addWidget(self.mystCtrl, 0, Qt.AlignCenter)
        sbs2.addWidget(spellFrameText, 0, Qt.AlignCenter)
        sbs2.addWidget(self.spellFrameCtrl, 0, Qt.AlignCenter)
        sbs2.addWidget(spellAnimText, 0, Qt.AlignCenter)
        sbs2.addWidget(self.spellAnimCtrl, 0, Qt.AlignCenter)
        sbs2.addWidget(self.spellWaitCheck, 0, Qt.AlignCenter)

        # ---------- Palette and Frame ----------
        sbs3 = QVBoxLayout()
        sbs3_widget = QWidget()
        sbs3_widget.setLayout(sbs3)                              # <-- исправлено
        sbs3_widget.setStyleSheet("border: 1px solid black;")

        self.frameList = QComboBox()
        self.frameList.setFixedWidth(100)
        self.paletteList = QComboBox()
        self.paletteList.setFixedWidth(100)
        sbs3.addWidget(self.frameList, 0, Qt.AlignLeft)
        sbs3.addWidget(self.paletteList, 0, Qt.AlignLeft)

        # ---------- Edit ----------
        sbs4 = QVBoxLayout()
        sbs4_widget = QWidget()
        sbs4_widget.setLayout(sbs4)                              # <-- исправлено
        sbs4_widget.setStyleSheet("border: 1px solid black;")

        text1 = QLabel("Colors")
        text2 = QLabel("Sprite (Color 0 = trans)")
        self.editPanel = rompanel.SpritePanel(self, None, 128, 96, self.palette, scale=3, bg=16)
        self.colorPanels = []
        for p in range(16):
            self.colorPanels.append(rompanel.ColorPanel2(self, None, "#000000", num=p))
        self.changeColors()
        self.importButton = QPushButton("Import")
        self.importButton.setFixedSize(40, 20)
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
        sbs4mid.addWidget(self.editPanel, 0, Qt.AlignCenter)

        sbs4right = QVBoxLayout()

        sbs4.addLayout(sbs4left, 0)
        sbs4.addLayout(sbs4mid, 1)

        # ---------- Animation Preview ----------
        sbs5 = QHBoxLayout()
        sbs5_widget = QWidget()
        sbs5_widget.setLayout(sbs5)                              # <-- исправлено
        sbs5_widget.setStyleSheet("border: 1px solid black;")

        sbs5left = QVBoxLayout()
        self.animList = QComboBox()
        self.animList.addItems(["Idle", "Attack", "Defend"])
        self.animList.setCurrentIndex(0)
        self.animPanel = rompanel.SpritePanel(self, None, 128, 96, self.palette, scale=1, bg=None, edit=False)
        self.animDelays = [250, 150, 50, 50, 50, 50]
        self.animFrameIdx = 0
        self.animCur = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.TimerTest)
        self.changeAnim(0)
        sbs5left.addWidget(self.animPanel, 0, Qt.AlignCenter)
        sbs5left.addWidget(self.animList, 0, Qt.AlignCenter)

        sbs5mid = QVBoxLayout()
        self.animFrameList = QListWidget()
        self.animFrameList.setFixedSize(120, 100)
        self.animAddButton = QPushButton("Add")
        self.animAddButton.setFixedSize(40, 20)
        self.animCopyButton = QPushButton("Copy")
        self.animCopyButton.setFixedSize(40, 20)
        self.animDelButton = QPushButton("Del")
        self.animDelButton.setFixedSize(40, 20)
        sbs5midButtonSizer = QHBoxLayout()
        sbs5midButtonSizer.addWidget(self.animAddButton)
        sbs5midButtonSizer.addWidget(self.animCopyButton)
        sbs5midButtonSizer.addWidget(self.animDelButton)
        sbs5mid.addWidget(self.animFrameList)
        sbs5mid.addLayout(sbs5midButtonSizer)

        sbs5right = QGridLayout()
        animPropsText1 = QLabel("Frame")
        animPropsText2 = QLabel("Duration")
        animPropsText3 = QLabel("Char X")
        animPropsText4 = QLabel("Char Y")
        animPropsText5 = QLabel("Weapon X")
        animPropsText6 = QLabel("Weapon Y")
        self.animZCheck = QCheckBox(" Weapon in front of character")
        self.animFrameCombo = QComboBox()
        self.animDurCtrl = QSpinBox(); self.animDurCtrl.setRange(0, 255)
        self.animCharXCtrl = QSpinBox(); self.animCharXCtrl.setRange(0, 255)
        self.animCharYCtrl = QSpinBox(); self.animCharYCtrl.setRange(0, 255)
        self.animWeaponXCtrl = QSpinBox(); self.animWeaponXCtrl.setRange(0, 255)
        self.animWeaponYCtrl = QSpinBox(); self.animWeaponYCtrl.setRange(0, 255)
        sbs5right.addWidget(animPropsText1, 0, 0)
        sbs5right.addWidget(animPropsText2, 1, 0)
        sbs5right.addWidget(animPropsText3, 2, 0)
        sbs5right.addWidget(animPropsText4, 3, 0)
        sbs5right.addWidget(animPropsText5, 4, 0)
        sbs5right.addWidget(animPropsText6, 5, 0)
        sbs5right.addWidget(self.animFrameCombo, 0, 1)
        sbs5right.addWidget(self.animDurCtrl, 1, 1)
        sbs5right.addWidget(self.animCharXCtrl, 2, 1)
        sbs5right.addWidget(self.animCharYCtrl, 3, 1)
        sbs5right.addWidget(self.animWeaponXCtrl, 4, 1)
        sbs5right.addWidget(self.animWeaponYCtrl, 5, 1)
        sbs5right.addWidget(self.animZCheck, 6, 0, 1, 2)

        sbs5wf = QVBoxLayout()
        animWeaponAnglePanel = QWidget()
        angleLayout = QGridLayout(animWeaponAnglePanel)
        self.animWeaponAngleRadios = {}
        radius = 40
        first = True
        for a in range(0, 360, 30):
            rx = int(math.cos(math.radians(a)) * radius + radius)
            ry = int(-math.sin(math.radians(a)) * radius + radius)
            rb = QRadioButton(animWeaponAnglePanel)
            self.animWeaponAngleRadios[a] = rb
            angleLayout.addWidget(rb, ry // 20, rx // 20)
            if first:
                rb.setChecked(True)
                first = False
        animWSprText = QLabel("Weapon Direction")
        sbs5wf.addWidget(animWSprText, 0, Qt.AlignCenter)
        sbs5wf.addWidget(animWeaponAnglePanel, 0, Qt.AlignCenter)

        sbs5.addLayout(sbs5left)
        sbs5.addSpacing(10)
        sbs5.addLayout(sbs5mid)
        sbs5.addSpacing(10)
        sbs5.addLayout(sbs5right)
        sbs5.addSpacing(10)
        sbs5.addLayout(sbs5wf)

        # ---------- Main Layout ----------
        midSizer = QHBoxLayout()
        midRightSizer = QVBoxLayout()

        midSizer.addLayout(sbs4)
        midRightSizer.addLayout(sbs3)
        midRightSizer.addStretch()
        midRightSizer.addLayout(sbs2)
        midSizer.addLayout(midRightSizer)

        self.sizer.addLayout(midSizer, 0, 0)
        self.sizer.addLayout(sbs5, 1, 0)

        self.changeBattleSprite(0)

        self.paletteList.currentIndexChanged.connect(self.OnSelectPalette)
        self.frameList.currentIndexChanged.connect(self.OnSelectFrame)
        self.importButton.clicked.connect(self.OnImportImage)
        self.exportButton.clicked.connect(self.OnExportImage)
        self.timer.timeout.connect(self.TimerTest)
        self.printed = False

    # ====== Методы ======
    def printrb(self):
        rb = self.curFrame.raw_bytes.split("\n")
        hx = self.curFrame.hexlify().split("\n")
        for i in range(max(len(rb), len(hx))):
            line1 = rb[i] if i < len(rb) else "No line"
            line2 = hx[i] if i < len(hx) else "No line"
            if line1 and line2:
                print(["Different!!!","Same"][line1==line2])
            print(line1)
            print(line2)
            print()

    def OnImportImage(self):
        if not shiboken6.isValid(self.editPanel):
            return
        size = self.editPanel.bmp.GetSize()
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
                    QMessageBox.warning(self, f"{fn} is {imgw}x{imgh} and should be {w}x{h}.", self.parent.baseTitle + " -- Error")
                elif img.format != "GIF" or imgpal is None:
                    QMessageBox.warning(self, f"{fn} is not a GIF or is improperly formatted.", self.parent.baseTitle + " -- Error")
                else:
                    cols = ["#%02x%02x%02x" % (imgpal[i]//16*17, imgpal[i+1]//16*17, imgpal[i+2]//16*17) for i in range(0, 48, 3)]
                    pal = data.Palette()
                    pal.init(cols)
                    self.editPanel.palette = pal
                    if shiboken6.isValid(self.animPanel):
                        self.animPanel.palette = pal
                    self.palette = pal
                    self.battleSprite.palettes[self.curPaletteIdx] = pal
                    imgdata = list(img.getdata())
                    pixels = "".join(["%x" % d for d in imgdata])
                    pixels = [pixels[i:i+w] for i in range(0, w*h, w)]
                    self.curFrame.convertFromPixelRows(pixels)
                    newtiles = [None]*len(self.curFrame.tiles)
                    order = self.curFrame.getTileOrder(imgw//8, imgh//8)
                    for i in range(len(newtiles)):
                        newtiles[order[i]] = self.curFrame.tiles[i]
                    self.curFrame.tiles = newtiles
                    self.changeBattleSprite()
                    self.updateAnimFrames()
                    self.changeColors()
                    self.modify()
                del img
            except IOError:
                QMessageBox.warning(self, f"{fn} is not a GIF or is improperly formatted.", self.parent.baseTitle + " -- Error")

    def OnExportImage(self):
        if not shiboken6.isValid(self.editPanel):
            return
        size = self.editPanel.bmp.GetSize()
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
        for p in range(16):
            if shiboken6.isValid(self.colorPanels[p]):
                self.colorPanels[p].setStyleSheet(f"background-color: {self.palette.colors[p]};")
                self.colorPanels[p].update()

    def TimerTest(self):
        self.animFrameIdx ^= 1
        self.changeAnimBattleSprite()

    def changeColors(self):
        palette = self.palette
        for c in range(len(self.colorPanels)):
            if shiboken6.isValid(self.colorPanels[c]):
                self.colorPanels[c].setStyleSheet(f"background-color: {palette.colors[c]};")
                self.colorPanels[c].update()

    def OnSelectPalette(self, idx):
        self.curPaletteIdx = idx
        self.changeBattleSprite()
        self.changeAnimBattleSprite(True)

    def OnSelectFrame(self, idx):
        self.curFrameIdx = idx
        self.changeBattleSprite()

    def changeEditColor(self, button, num):
        pass

    def refreshPixels(self):
        pass

    def OnChangeAnim(self, button_id):
        pass

    def OnSelectMode(self, mode_id):
        pass

    def OnSelectBattleSprite(self, idx):
        self.changeBattleSprite(idx)

    def changeBattleSprite(self, num=None):
        if num is not None:
            if not self.rom.data["battle_sprites"][num].loaded:
                self.rom.getBattleSprites(num, num)
            self.curPaletteIdx = 0
            self.curFrameIdx = 0
            self.battleSprite = self.rom.data["battle_sprites"][num]
            if shiboken6.isValid(self.editPanel):
                if num < self.rom.sectionData["battle_sprites"][2][0]:
                    self.editPanel.width = 96
                else:
                    self.editPanel.width = 128
                self.editPanel.height = 96
            if shiboken6.isValid(self.animPanel):
                if num < self.rom.sectionData["battle_sprites"][2][0]:
                    self.animPanel.width = 96
                else:
                    self.animPanel.width = 128
                self.animPanel.height = 96
            self.updateAnimFrames()
            self.animSpdCtrl.setValue(self.battleSprite.animSpeed)
            self.mystCtrl.setValue(int(self.battleSprite.myst, 16))
            self.frameList.clear()
            self.frameList.addItems(["Frame %i" % i for i,p in enumerate(self.battleSprite.frames)])
            self.frameList.setCurrentIndex(self.curFrameIdx)
            self.paletteList.clear()
            self.paletteList.addItems(["Palette %i" % i for i,p in enumerate(self.battleSprite.palettes)])
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
            self.updateModifiedIndicator(self.battleSprite.modified)
            self.editPanel.update()
        self.refreshPixels()

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
        tw, th = self.animPanel.width // 8, self.animPanel.height // 8
        self.animFrames = []
        for f in self.battleSprite.frames:
            self.animFrames.append(f.getPixelRows(tw, th))

    def getCurrentSpriteObject(self):
        return self.battleSprite

    def getCurrentData(self):
        return self.battleSprite

    def iterateData(self):
        sprs = len(self.battleSpriteList) if hasattr(self, 'battleSpriteList') else 0
        for i in range(sprs):
            self.changeBattleSprite(i)
            num_frames = self.frameList.count()
            num_pals = self.paletteList.count()
            for j in range(num_pals):
                for k in range(num_frames):
                    self.curFrameIdx = k
                    self.curPaletteIdx = j
                    self.changeBattleSprite()
                    yield ("battle_sprite", i, j, k)

    changeSelection = changeBattleSprite

    curFrame = property(lambda self: self.battleSprite.frames[self.curFrameIdx])
    curPalette = property(lambda self: self.battleSprite.palettes[self.curPaletteIdx])
    animFrame = property(lambda self: self.animFrames[self.animFrameIdx])