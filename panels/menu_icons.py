import binascii
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QRadioButton, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage, QColor
import data
from PIL import Image
import rompanel

h2i = lambda i: int(i, 16)

class MenuIconPanel(rompanel.ROMPanel):
    
    frameTitle = "Menu Icon Editor"
    
    def init(self):
        
        self.palette = self.rom.getDataByName("palettes", "Sprite & UI Palette")
        self.frame = 0
        self.mode = 0
        
        self.color_left = 0
        self.color_right = 0
        
        self.curIconIdx = 0
        
        leftSizer = QVBoxLayout()
        
        sbs4 = QVBoxLayout()
        sbs4_widget = QWidget()
        sbs4_widget.setLayout(sbs4)
        sbs4_widget.setStyleSheet("border: 1px solid black;")
        
        sbs5 = QVBoxLayout()
        sbs5_widget = QWidget()
        sbs5_widget.setLayout(sbs5)
        sbs5_widget.setStyleSheet("border: 1px solid black;")
        
        text1 = QLabel("Colors")
        text2 = QLabel("Icon (Color 0 = trans)")
        text3 = QLabel("Left-Click")
        text4 = QLabel("Right-Click")
        text5 = QLabel("Mode")
        
        self.editPanel = rompanel.SpritePanel(self, None, 24, 24, self.palette, scale=8, bg=16, func="edit")
        
        self.colorPanels = []
        for p in range(16):
            self.colorPanels.append(rompanel.ColorPanel2(self, None, "#000000", num=p))
        
        self.changeColors()
        
        self.switchButton = QPushButton("Frame")
        self.switchButton.setFixedSize(40, 20)
        
        sbs4left = QVBoxLayout()
        
        colorSizer = QGridLayout()
        for i, cp in enumerate(self.colorPanels):
            colorSizer.addWidget(cp, i // 2, i % 2)
        
        self.importButton = QPushButton("Import")
        self.importButton.setFixedSize(40, 20)
        self.exportButton = QPushButton("Export")
        self.exportButton.setFixedSize(40, 20)
        
        sbs4left.addWidget(text1, 0, Qt.AlignCenter)
        sbs4left.addLayout(colorSizer)
        sbs4left.addWidget(self.importButton, 0, Qt.AlignCenter)
        sbs4left.addWidget(self.exportButton, 0, Qt.AlignCenter)
        
        sbs4mid = QVBoxLayout()
        
        sbs4mid.addWidget(text2, 0, Qt.AlignCenter)
        sbs4mid.addWidget(self.editPanel, 0, Qt.AlignCenter)
        
        sbs4right = QVBoxLayout()
        
        self.selectedColorLeft = QLabel()
        self.selectedColorLeft.setFixedSize(40, 40)
        self.selectedColorLeft.setStyleSheet("background-color: #000000;")
        self.selectedColorLeft.color = 0
        
        self.selectedColorRight = QLabel()
        self.selectedColorRight.setFixedSize(40, 40)
        self.selectedColorRight.setStyleSheet("background-color: #000000;")
        self.selectedColorRight.color = 0

        self.modePixel = QRadioButton("Pixel")
        self.modeFill = QRadioButton("Floodfill")
        self.modeReplace = QRadioButton("Replace")
        self.modePixel.setChecked(True)
        
        sbs4right.addWidget(text3, 0, Qt.AlignCenter)
        sbs4right.addWidget(self.selectedColorLeft, 0, Qt.AlignCenter)
        sbs4right.addWidget(text4, 0, Qt.AlignCenter)
        sbs4right.addWidget(self.selectedColorRight, 0, Qt.AlignCenter)
        sbs4right.addWidget(text5, 0, Qt.AlignCenter)
        sbs4right.addWidget(self.modePixel, 0, Qt.AlignLeft)
        sbs4right.addWidget(self.modeFill, 0, Qt.AlignLeft)
        sbs4right.addWidget(self.modeReplace, 0, Qt.AlignLeft)
        sbs4right.addWidget(self.switchButton, 0, Qt.AlignCenter)
        
        sbs4.addLayout(sbs4left, 0)
        sbs4.addLayout(sbs4mid, 1)
        sbs4.addLayout(sbs4right, 0)
        
        # Preview Animation
        self.animPanel = rompanel.SpritePanel(self, None, 24, 24, self.palette, scale=3, bg=None, edit=False)
    
        self.animDelays = [250]
        self.animFrame = 0
        self.animCur = 0
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.TimerTest)
        self.changeAnim(0)
        
        sbs5.addWidget(self.animPanel, 0, Qt.AlignCenter)
        
        midSizer = QHBoxLayout()
        midRightSizer = QVBoxLayout()
        
        midSizer.addLayout(sbs4)
        midRightSizer.addLayout(sbs5)
        midSizer.addLayout(midRightSizer)
        
        self.sizer.addLayout(midSizer, 0, 0, 1, 2)
        
        self.changeIcon(0)
        
        self.modePixel.toggled.connect(self.OnSelectMode)
        self.modeFill.toggled.connect(self.OnSelectMode)
        self.modeReplace.toggled.connect(self.OnSelectMode)
        self.importButton.clicked.connect(self.OnImportImage)
        self.exportButton.clicked.connect(self.OnExportImage)
        self.switchButton.clicked.connect(self.OnSwitchFrame)
        self.timer.timeout.connect(self.TimerTest)
        
        self.printed = False
    
    def OnShow(self):
        for p in range(16):
            self.colorPanels[p].setStyleSheet(f"background-color: {self.palette.colors[p]};")
            self.colorPanels[p].update()
        self.selectedColorLeft.setStyleSheet(f"background-color: {self.palette.colors[self.color_left]};")
        self.selectedColorRight.setStyleSheet(f"background-color: {self.palette.colors[self.color_right]};")

    def OnImportImage(self):
        
        size = self.editPanel.bmp.GetSize()
        width, height = size.width(), size.height()
        
        dlg = QFileDialog(self, f"Import 16-color {width}x{height} GIF", "", "GIF files (*.gif)")
        dlg.setFileMode(QFileDialog.ExistingFile)
        
        if dlg.exec() == QDialog.Accepted:
            
            fn = dlg.selectedFiles()[0]
            
            try:
                
                img = Image.open(fn)
                imgw, imgh = img.size
                imgpal = img.getpalette()
                
                if img.size != (width, height):
                    
                    QMessageBox.warning(self, f"{fn} is {imgw}x{imgh} and should be {width}x{height}.",
                                        self.parent.baseTitle + " -- Error")
                
                elif img.format != "GIF" or imgpal is None:
                    
                    QMessageBox.warning(self, f"{fn} is not a GIF or is improperly formatted.",
                                        self.parent.baseTitle + " -- Error")
                    
                else:
                    
                    imgdata = list(img.getdata())
                    pixels = "".join(["%x" % d for d in imgdata])
                    pixels = [pixels[i:i+width] for i in range(0, width*height, width)]
                    
                    if self.frame == 0:
                        self.icon.pixels = pixels
                        self.icon.raw_pixels = "".join(self.icon.convertFromPixelRows(pixels))
                    else:
                        self.icon.pixels2 = pixels
                        self.icon.raw_pixels2 = "".join(self.icon.convertFromPixelRows(pixels))
                    
                    self.changeIcon()
                    
                    self.changeColors()
                    
                    self.modify()
                    
                del img
                
            except IOError as e:
                
                QMessageBox.warning(self, f"{fn} is not a GIF or is improperly formatted.",
                                    self.parent.baseTitle + " -- Error")

        
    def OnExportImage(self):
        
        size = self.editPanel.bmp.GetSize()
        width, height = size.width(), size.height()
        
        dlg = QFileDialog(self, f"Export 16-color {width}x{height} GIF", "", "GIF files (*.gif)")
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        
        if dlg.exec() == QDialog.Accepted:
            
            fn = dlg.selectedFiles()[0]
            
            img = Image.new("P", (width, height))
            img.putdata([int(a, 16) for pr in self.editPanel.pixels for a in pr])

            p = [v for rt in self.editPanel.palette.rgbaTuples() for v in rt[:3]]
            p += [0] * (768 - len(p))
            
            img.putpalette(p)
            img.save(fn, "GIF")
            
    def TimerTest(self):
        
        self.animFrame ^= 1
        self.changeAnimIcon()
            
    def changeColors(self):
        palette = self.palette
        for c in range(len(self.colorPanels)):
            self.colorPanels[c].setStyleSheet(f"background-color: {palette.colors[c]};")
            self.colorPanels[c].update()

    def changeEditColor(self, button, num):
        
        if button == 0:
            self.color_left = num
        else:
            self.color_right = num

        if button == 0:
            self.selectedColorLeft.color = num
            self.selectedColorLeft.setStyleSheet(f"background-color: {self.palette.colors[num]};")
        else:
            self.selectedColorRight.color = num
            self.selectedColorRight.setStyleSheet(f"background-color: {self.palette.colors[num]};")
        
    def refreshPixels(self):
        pass

    def OnSelectMode(self, checked):
        if self.modePixel.isChecked():
            self.mode = 0
        elif self.modeFill.isChecked():
            self.mode = 1
        elif self.modeReplace.isChecked():
            self.mode = 2
        
    def OnSelectIcon(self, idx):
        self.changeIcon(idx)
    
    def OnSwitchFrame(self):
        self.frame ^= 1
        self.changeIcon(self.curIconIdx)
        
    def changeIcon(self, num=None):
        
        if num is not None:
            
            self.curIconIdx = num
            if not self.rom.data["menu_icons"][num].loaded:
                self.rom.getMenuIcons(num, num)
                
            self.icon = self.rom.data["menu_icons"][num]
        
        if self.frame == 0:
            self.editPanel.refreshSprite(self.icon.pixels)
        else:
            self.editPanel.refreshSprite(self.icon.pixels2)
        
        self.updateModifiedIndicator(self.icon.modified)
        
        self.editPanel.update()
        self.refreshPixels()
    
    def changeAnim(self, num):
        self.animCur = num
        self.timer.start(self.animDelays[num])
        
    def changeAnimIcon(self):

        if self.animFrame == 0:
            self.animPanel.refreshSprite(self.icon.pixels)
        else:
            self.animPanel.refreshSprite(self.icon.pixels2)
            
        self.animPanel.update()
        
    def getCurrentSpriteObject(self):
        return self.icon
        
    def getCurrentData(self):
        return self.icon
        
    changeSelection = changeIcon