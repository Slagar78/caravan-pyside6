from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QSlider, QSpinBox, QListWidget,
    QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import rompanel

h2i = lambda i: int(i, 16)

class PalettePanel(rompanel.ROMPanel):
    
    frameTitle = "Palette Editor"
    
    def init(self):
        
        self.curPaletteIdx = 0
        self.color = 0
        
        sbs1 = QGroupBox("Colors")
        sbs1_layout = QVBoxLayout(sbs1)
        
        self.colorPanels = []
        for p in range(16):
            cp = rompanel.ColorPanel(self, None, "#000000", num=p)
            self.colorPanels.append(cp)
        
        self.changeColors()
        
        colorSizer = QGridLayout()
        for i in range(16):
            colorSizer.addWidget(QLabel(str(i).zfill(2)), 0, i, Qt.AlignCenter)
        for i, cp in enumerate(self.colorPanels):
            colorSizer.addWidget(cp, 1, i)
        
        sbs1_layout.addLayout(colorSizer)
        
        sbs2 = QGroupBox("Maps using this palette")
        sbs2_layout = QVBoxLayout(sbs2)
        text1 = QLabel("(if applicable)")
        self.mapList = QListWidget()
        self.mapList.setFixedSize(120, 140)
        sbs2_layout.addWidget(text1, 0, Qt.AlignCenter)
        sbs2_layout.addWidget(self.mapList, 0, Qt.AlignCenter)
        
        sbs3 = QGroupBox("Edit")
        sbs3_layout = QVBoxLayout(sbs3)
        
        self.colorText = QLabel(f"Color {self.color:02d}")
        editFont = QFont("Courier New", 12, QFont.Bold)  # аналог GetTopLevelParent().editFont
        self.colorText.setFont(editFont)
        
        sbs3left = QVBoxLayout()
        text2 = QLabel("Edit")
        self.editPanel = rompanel.ColorPanel(self, None, "#000000", enable=False)
        self.editPanel.setFixedSize(60, 60)
        sbs3left.addWidget(text2, 0, Qt.AlignCenter)
        sbs3left.addWidget(self.editPanel, 0, Qt.AlignCenter)
        
        sbs3mid = QGridLayout()
        
        self.sliderRed = QSlider(Qt.Horizontal)
        self.sliderRed.setRange(0, 15)
        self.sliderGreen = QSlider(Qt.Horizontal)
        self.sliderGreen.setRange(0, 15)
        self.sliderBlue = QSlider(Qt.Horizontal)
        self.sliderBlue.setRange(0, 15)
        
        self.spinRed = QSpinBox()
        self.spinRed.setRange(0, 15)
        self.spinGreen = QSpinBox()
        self.spinGreen.setRange(0, 15)
        self.spinBlue = QSpinBox()
        self.spinBlue.setRange(0, 15)
        
        sbs3mid.addWidget(rompanel.ColorPanel(self, None, "#FF0000", size=(20,20)), 0, 0, Qt.AlignCenter)
        sbs3mid.addWidget(self.sliderRed, 0, 1)
        sbs3mid.addWidget(self.spinRed, 0, 2, Qt.AlignCenter)
        sbs3mid.addWidget(rompanel.ColorPanel(self, None, "#00FF00", size=(20,20)), 1, 0, Qt.AlignCenter)
        sbs3mid.addWidget(self.sliderGreen, 1, 1)
        sbs3mid.addWidget(self.spinGreen, 1, 2, Qt.AlignCenter)
        sbs3mid.addWidget(rompanel.ColorPanel(self, None, "#0000FF", size=(20,20)), 2, 0, Qt.AlignCenter)
        sbs3mid.addWidget(self.sliderBlue, 2, 1)
        sbs3mid.addWidget(self.spinBlue, 2, 2, Qt.AlignCenter)
        
        sbs3right = QVBoxLayout()
        text3 = QLabel("Clipboard")
        self.copyPanel = rompanel.ColorPanel(self, None, "#000000", enable=False)
        self.copyPanel.setFixedSize(60, 60)
        sbs3right.addWidget(text3, 0, Qt.AlignCenter)
        sbs3right.addWidget(self.copyPanel, 0, Qt.AlignCenter)
        
        self.copyButton = QPushButton("Copy")
        self.pasteButton = QPushButton("Paste")
        self.pasteButton.setEnabled(False)
        
        sbs3main = QGridLayout()
        sbs3main.addLayout(sbs3left, 0, 0)
        sbs3main.addLayout(sbs3mid, 0, 1)
        sbs3main.addLayout(sbs3right, 0, 2)
        sbs3main.addWidget(self.copyButton, 1, 0, Qt.AlignCenter)
        sbs3main.addWidget(self.colorText, 1, 1, Qt.AlignCenter)
        sbs3main.addWidget(self.pasteButton, 1, 2, Qt.AlignCenter)
        
        sbs3_layout.addLayout(sbs3main)
        
        sbs4 = QGroupBox("Code")
        sbs4_layout = QVBoxLayout(sbs4)
        self.symbolsBox = rompanel.HexBox(self, None)
        self.symbolsBox.setFixedHeight(42)
        sbs4_layout.addWidget(self.symbolsBox)
        
        # Layout
        self.sizer.addWidget(sbs1, 0, 0)
        self.sizer.addWidget(sbs2, 0, 1, 2, 1)
        self.sizer.addWidget(sbs3, 1, 0)
        self.sizer.addWidget(sbs4, 2, 0, 1, 2)
        
        self.changePalette(0)
        self.changeEditColor(0)
        self.updateSymbols()
        
        # Connections
        self.sliderRed.valueChanged.connect(self.OnChangeColor)
        self.sliderGreen.valueChanged.connect(self.OnChangeColor)
        self.sliderBlue.valueChanged.connect(self.OnChangeColor)
        self.spinRed.valueChanged.connect(self.OnChangeColor)
        self.spinGreen.valueChanged.connect(self.OnChangeColor)
        self.spinBlue.valueChanged.connect(self.OnChangeColor)
        self.copyButton.clicked.connect(self.OnCopyColor)
        self.pasteButton.clicked.connect(self.OnPasteColor)
    
    def changeColors(self):
        palette = self.curPalette
        for c, cp in enumerate(self.colorPanels):
            cp.setStyleSheet(f"background-color: {palette.colors[c]};")
            cp.update()
    
    def OnSelectPalette(self, idx):
        self.changePalette(idx)
        
    def changePalette(self, num):
        self.curPaletteIdx = num
        imp = self.curPalette.isMapPalette
        self.mapList.setEnabled(imp)
        self.mapList.clear()
        if imp:
            mapsUsing = [m.name for m in self.rom.data["maps"] if m.paletteIdx == self.curPaletteIdx]
            self.mapList.addItems(mapsUsing)
        self.changeColors()
        self.changeEditColor(0)
        self.updateSymbols()
    
    def changeEditColor(self, num):
        self.color = num
        self.colorText.setText(f"Color {num:02d}")
        c = self.rom.data["palettes"][self.curPaletteIdx].colors[num]
        self.editPanel.setStyleSheet(f"background-color: {c};")
        self.editPanel.update()
        self.setColor(c)
        
    def setColor(self, c):
        r, g, b = int(c[1], 16), int(c[3], 16), int(c[5], 16)
        self.sliderRed.setValue(r)
        self.spinRed.setValue(r)
        self.sliderGreen.setValue(g)
        self.spinGreen.setValue(g)
        self.sliderBlue.setValue(b)
        self.spinBlue.setValue(b)
        
    def updateSymbols(self):
        self.symbolsBox.setPlainText(self.rom.data["palettes"][self.curPaletteIdx].hexlify())
        
    def OnChangeColor(self, value):
        sender = self.sender()
        if sender == self.sliderRed:
            self.spinRed.setValue(value)
        elif sender == self.sliderGreen:
            self.spinGreen.setValue(value)
        elif sender == self.sliderBlue:
            self.spinBlue.setValue(value)
        elif sender == self.spinRed:
            self.sliderRed.setValue(value)
        elif sender == self.spinGreen:
            self.sliderGreen.setValue(value)
        elif sender == self.spinBlue:
            self.sliderBlue.setValue(value)
        else:
            return
        
        r = hex(self.spinRed.value())[2:]
        g = hex(self.spinGreen.value())[2:]
        b = hex(self.spinBlue.value())[2:]
        c = f"#{r*2}{g*2}{b*2}"
        
        self.editPanel.setStyleSheet(f"background-color: {c};")
        self.colorPanels[self.color].setStyleSheet(f"background-color: {c};")
        self.editPanel.update()
        self.colorPanels[self.color].update()
        
        self.modify()
        self.updateSymbols()
        self.rom.data["palettes"][self.curPaletteIdx].colors[self.color] = c
        
    def OnCopyColor(self):
        c = self.rom.data["palettes"][self.curPaletteIdx].colors[self.color]
        self.copyPanel.setStyleSheet(f"background-color: {c};")
        self.copyPanel.update()
        self.copyPanel.copyColor = c
        self.pasteButton.setEnabled(True)
        
    def OnPasteColor(self):
        c = self.copyPanel.copyColor
        self.editPanel.setStyleSheet(f"background-color: {c};")
        self.colorPanels[self.color].setStyleSheet(f"background-color: {c};")
        self.editPanel.update()
        self.colorPanels[self.color].update()
        self.updateSymbols()
        self.curPalette.colors[self.color] = c
        self.setColor(c)
        
    def getCurrentData(self):
        return self.curPalette
    
    changeSelection = changePalette
    
    curPalette = property(lambda self: self.rom.data["palettes"][self.curPaletteIdx])