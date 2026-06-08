import binascii
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QComboBox, QSpinBox, QSlider, QRadioButton,
    QCheckBox, QListWidget, QTabWidget, QScrollArea, QAbstractItemView,
    QLineEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from rompanel import SpritePanel
import rompanel
import window, consts

h2i = lambda i: int(i, 16)

class MapPanel(rompanel.ROMPanel):
    
    frameTitle = "Map Definition Editor"
    
    def init(self):
        self.palette = self.rom.data["palettes"][0]
        self.mode = 0

        self.curEditBlock = 0
        self.curListBlockLeft = 0
        self.curListBlockRight = 1

        self.curEditBlockPage = 0
        self.curListBlockPage = 0

        self.curLeftTile = 0x100
        self.curRightTile = 0x100

        self.curInterFlag = 0xc000

        self.curViewMode = 0
        self.viewAll = False

        self.curMapIdx = 0

        self.curTilesetIdx = 0
        self.curAnimTSIdx = 0

        self.curEventIdx = 0
        self.curEventType = 0

        self.blockEditMode = 0

        self.map = self.rom.data["maps"][0]

        # ====================== Главный Layout ======================
        leftSizer = QVBoxLayout()
        
        # Контейнер с границей
        sbs2_widget = QWidget()
        sbs2_widget.setStyleSheet("border: 1px solid black;")
        self.sbs2_widget = sbs2_widget
        sbs2 = QVBoxLayout(sbs2_widget)

        # ====================== NOTEBOOK ======================
        self.mainNotebook = QTabWidget()
        self.mainNotebook.setFixedWidth(420)

        genWindow = QWidget()
        self.blockWindow = QWidget()
        layoutWindow = QWidget()
        configWindow = QWidget()
        eventWindow = QWidget()
        animWindow = QWidget()

        genWndSizer = QVBoxLayout(genWindow)
        blockWndSizer = QVBoxLayout(self.blockWindow)
        layoutWndSizer = QHBoxLayout(layoutWindow)
        configWndSizer = QVBoxLayout(configWindow)
        eventWndSizer = QVBoxLayout(eventWindow)
        animWndSizer = QVBoxLayout(animWindow)

        # ========== GENERAL TAB ==========
        # Palette
        sbs2paletteBS = QGroupBox("Palette")
        sbs2paletteBS_layout = QVBoxLayout(sbs2paletteBS)

        self.paletteList = QComboBox()
        self.paletteList.addItems([p.name for p in self.rom.data["palettes"] if p.isMapPalette])

        self.colorPanels = []
        for p in range(16):
            cp = rompanel.ColorPanel(genWindow, None, "#000000", num=p)
            self.colorPanels.append(cp)

        colorSizer = QGridLayout()
        for i in range(16):
            colorSizer.addWidget(QLabel(str(i).zfill(2)), 0, i, Qt.AlignCenter)
        for i, cp in enumerate(self.colorPanels):
            colorSizer.addWidget(cp, 1, i)

        sbs2paletteBS_layout.addLayout(colorSizer)
        sbs2paletteBS_layout.addWidget(self.paletteList)

        # Tilesets
        sbs2tilesetBS = QGroupBox("Tilesets")
        sbs2tilesetBS_layout = QVBoxLayout(sbs2tilesetBS)
        sbs2tilesetBSSizer = QGridLayout()

        self.layerChecks = []
        self.tilesetLists = []

        sbs2tilesetBSSizer.addWidget(QLabel("Tileset"), 0, 1, Qt.AlignCenter)

        for i in range(5):
            chk = QCheckBox(f" {i+1}")
            chk.setEnabled(False)
            self.layerChecks.append(chk)

            tl = QComboBox()
            tl.addItems([ts.name for ts in self.rom.data["tilesets"]])
            self.tilesetLists.append(tl)

            sbs2tilesetBSSizer.addWidget(chk, i+1, 0)
            sbs2tilesetBSSizer.addWidget(tl, i+1, 1)

        sbs2tilesetBS_layout.addLayout(sbs2tilesetBSSizer)

        # Areas
        sbs2areaBS = QGroupBox("Areas")
        sbs2areaBS_layout = QVBoxLayout(sbs2areaBS)

        self.areaList = QComboBox()
        self.areaAddButton = QPushButton("Add")
        self.areaAddButton.setFixedSize(40, 20)
        self.areaAddButton.setEnabled(False)
        self.areaDelButton = QPushButton("Del")
        self.areaDelButton.setFixedSize(40, 20)
        self.areaDelButton.setEnabled(False)

        areaTopSizer = QHBoxLayout()
        areaTopSizer.addWidget(QLabel("Area:"))
        areaTopSizer.addWidget(self.areaList)
        areaTopSizer.addWidget(self.areaAddButton)
        areaTopSizer.addWidget(self.areaDelButton)

        self.areaLayer2Check = QCheckBox(" Layer 2: ")
        self.areaLayer2ForeRadio = QRadioButton("Foreground")
        self.areaLayer2BackRadio = QRadioButton("Background")
        self.areaLayer2ForeRadio.setChecked(True)

        areaMidSizer = QHBoxLayout()
        areaMidSizer.addWidget(self.areaLayer2Check)
        areaMidSizer.addWidget(self.areaLayer2ForeRadio)
        areaMidSizer.addWidget(self.areaLayer2BackRadio)

        # Spin Controls for Areas
        self.areaLayer1X1Ctrl = QSpinBox(); self.areaLayer1X1Ctrl.setRange(0, 64)
        self.areaLayer1Y1Ctrl = QSpinBox(); self.areaLayer1Y1Ctrl.setRange(0, 64)
        self.areaLayer1X2Ctrl = QSpinBox(); self.areaLayer1X2Ctrl.setRange(0, 64)
        self.areaLayer1Y2Ctrl = QSpinBox(); self.areaLayer1Y2Ctrl.setRange(0, 64)
        self.areaLayer1ParaXCtrl = QSpinBox(); self.areaLayer1ParaXCtrl.setRange(0, 2048)
        self.areaLayer1ParaYCtrl = QSpinBox(); self.areaLayer1ParaYCtrl.setRange(0, 2048)
        self.areaLayer1ScrXCtrl = QSpinBox(); self.areaLayer1ScrXCtrl.setRange(-128, 127)
        self.areaLayer1ScrYCtrl = QSpinBox(); self.areaLayer1ScrYCtrl.setRange(-128, 127)
        self.areaLayer2X1Ctrl = QSpinBox(); self.areaLayer2X1Ctrl.setRange(0, 64)
        self.areaLayer2Y1Ctrl = QSpinBox(); self.areaLayer2Y1Ctrl.setRange(0, 64)
        self.areaLayer2ParaXCtrl = QSpinBox(); self.areaLayer2ParaXCtrl.setRange(0, 2048)
        self.areaLayer2ParaYCtrl = QSpinBox(); self.areaLayer2ParaYCtrl.setRange(0, 2048)
        self.areaLayer2ScrXCtrl = QSpinBox(); self.areaLayer2ScrXCtrl.setRange(-128, 127)
        self.areaLayer2ScrYCtrl = QSpinBox(); self.areaLayer2ScrYCtrl.setRange(-128, 127)

        areaPropsGrid = QGridLayout()
        areaPropsGrid.addWidget(QLabel("Layer 1 X:"), 0, 0);   areaPropsGrid.addWidget(self.areaLayer1X1Ctrl, 0, 1)
        areaPropsGrid.addWidget(QLabel("Layer 1 Y:"), 1, 0);   areaPropsGrid.addWidget(self.areaLayer1Y1Ctrl, 1, 1)
        areaPropsGrid.addWidget(QLabel("Layer 1 X2:"), 2, 0);  areaPropsGrid.addWidget(self.areaLayer1X2Ctrl, 2, 1)
        areaPropsGrid.addWidget(QLabel("Layer 1 Y2:"), 3, 0);  areaPropsGrid.addWidget(self.areaLayer1Y2Ctrl, 3, 1)
        areaPropsGrid.addWidget(QLabel("Parallax X:"), 4, 0);  areaPropsGrid.addWidget(self.areaLayer1ParaXCtrl, 4, 1)
        areaPropsGrid.addWidget(QLabel("Parallax Y:"), 5, 0);  areaPropsGrid.addWidget(self.areaLayer1ParaYCtrl, 5, 1)
        areaPropsGrid.addWidget(QLabel("Scroll X:"), 6, 0);    areaPropsGrid.addWidget(self.areaLayer1ScrXCtrl, 6, 1)
        areaPropsGrid.addWidget(QLabel("Scroll Y:"), 7, 0);    areaPropsGrid.addWidget(self.areaLayer1ScrYCtrl, 7, 1)
        areaPropsGrid.addWidget(QLabel("Layer 2 X:"), 8, 0);   areaPropsGrid.addWidget(self.areaLayer2X1Ctrl, 8, 1)
        areaPropsGrid.addWidget(QLabel("Layer 2 Y:"), 9, 0);   areaPropsGrid.addWidget(self.areaLayer2Y1Ctrl, 9, 1)
        areaPropsGrid.addWidget(QLabel("Parallax X2:"),10,0);  areaPropsGrid.addWidget(self.areaLayer2ParaXCtrl,10,1)
        areaPropsGrid.addWidget(QLabel("Parallax Y2:"),11,0);  areaPropsGrid.addWidget(self.areaLayer2ParaYCtrl,11,1)
        areaPropsGrid.addWidget(QLabel("Scroll X2:"),  12,0);  areaPropsGrid.addWidget(self.areaLayer2ScrXCtrl, 12,1)
        areaPropsGrid.addWidget(QLabel("Scroll Y2:"),  13,0);  areaPropsGrid.addWidget(self.areaLayer2ScrYCtrl, 13,1)

        self.areaMusicList = QComboBox()
        self.areaMusicList.addItems([m.name for m in self.rom.data["music"]])

        areaBotSizer = QHBoxLayout()
        areaBotSizer.addWidget(QLabel(" Music: "))
        areaBotSizer.addWidget(self.areaMusicList)

        sbs2areaBS_layout.addLayout(areaTopSizer)
        sbs2areaBS_layout.addLayout(areaMidSizer)
        sbs2areaBS_layout.addLayout(areaPropsGrid)
        sbs2areaBS_layout.addLayout(areaBotSizer)

        # Собираем General Tab
        genWndSizerRow1 = QHBoxLayout()
        genWndSizerRow1.addWidget(sbs2paletteBS)
        genWndSizerRow2 = QHBoxLayout()
        genWndSizerRow2.addWidget(sbs2tilesetBS)
        genWndSizerRow2.addWidget(sbs2areaBS)

        genWndSizer.addLayout(genWndSizerRow1)
        genWndSizer.addLayout(genWndSizerRow2)

        # ========== BLOCKS TAB ==========
        sbs2blockTSListBS = QGroupBox("Tilesets used by this map")
        sbs2blockTSListBS_layout = QVBoxLayout(sbs2blockTSListBS)
        self.blockTSList = QComboBox()
        sbs2blockTSListBS_layout.addWidget(self.blockTSList)

        sbs2blockEditorBS = QGroupBox("2. Edit the block.")
        sbs2blockEditorBS_layout = QVBoxLayout(sbs2blockEditorBS)
        self.blockPanel = rompanel.SpritePanel(self.blockWindow, None, 24, 24, self.palette, scale=3, bg=16, func=self.OnChangeBlockTile, edit=True)
        sbs2blockEditorBS_layout.addWidget(self.blockPanel)

        sbs2blockTSBS = QGroupBox("Tileset")
        sbs2blockTSBS_layout = QHBoxLayout(sbs2blockTSBS)
        tsScroll = QScrollArea()
        tsScroll.setWidgetResizable(True)
        tsScroll.setFixedSize(250, 120)
        tsWidget = QWidget()
        tsLayout = QVBoxLayout(tsWidget)
        self.tilesetPanel = rompanel.SpritePanel(tsWidget, None, 128, 64, self.palette, scale=3, bg=16, func=self.OnClickBlockTilesetPanel, edit=True, grid=8)
        tsLayout.addWidget(self.tilesetPanel)
        tsScroll.setWidget(tsWidget)

        editTileSizer = QVBoxLayout()
        self.blockEditLeftPanel = rompanel.SpritePanel(self.blockWindow, None, 8, 8, self.palette, scale=6, bg=16)
        self.blockEditRightPanel = rompanel.SpritePanel(self.blockWindow, None, 8, 8, self.palette, scale=6, bg=16)
        editTileSizer.addWidget(QLabel("Left-Click"))
        editTileSizer.addWidget(self.blockEditLeftPanel)
        editTileSizer.addWidget(QLabel("Right-Click"))
        editTileSizer.addWidget(self.blockEditRightPanel)

        sbs2blockTSBS_layout.addWidget(tsScroll)
        sbs2blockTSBS_layout.addLayout(editTileSizer)

        # Block List
        sbs2blockListBS = QGroupBox("1. Select a block.")
        sbs2blockListBS_layout = QHBoxLayout(sbs2blockListBS)
        self.blockEditSlider = QSlider(Qt.Vertical)
        self.blockEditSlider.setRange(0, 15)
        self.blockEditSlider.context = "edit"

        self.blockEditPosText = QLabel("0")
        self.blockEditMaxText = QLabel("0")
        self.blockEditAddButton = QPushButton("Add")
        self.blockEditDelButton = QPushButton("Delete")

        self.blockEditPanels = []
        self.blockEditText = []
        blockEditListSizer = QVBoxLayout()
        for idx in range(3):
            p = rompanel.SpritePanel(self.blockWindow, None, 24, 24, self.palette, scale=2, bg=None, xpad=4, ypad=4, func=self.OnClickBlockEditPanel)
            p.index = idx
            self.blockEditPanels.append(p)
            t = QLabel(str(idx))
            self.blockEditText.append(t)
            blockEditListSizer.addWidget(t, 0, Qt.AlignCenter)
            blockEditListSizer.addWidget(p, 0, Qt.AlignCenter)

        blockEditListSelSizer = QVBoxLayout()
        blockEditListSelSizer.addWidget(self.blockEditPosText, 0, Qt.AlignCenter)
        blockEditListSelSizer.addWidget(self.blockEditSlider)
        blockEditListSelSizer.addWidget(self.blockEditMaxText, 0, Qt.AlignCenter)
        blockEditListSelSizer.addWidget(self.blockEditAddButton, 0, Qt.AlignCenter)
        blockEditListSelSizer.addWidget(self.blockEditDelButton, 0, Qt.AlignCenter)

        sbs2blockListBS_layout.addLayout(blockEditListSelSizer)
        sbs2blockListBS_layout.addLayout(blockEditListSizer)

        blockWndSizer_row1 = QHBoxLayout()
        blockWndSizer_row1.addWidget(sbs2blockTSListBS)
        blockWndSizer_row1.addWidget(sbs2blockEditorBS)
        blockWndSizer.addLayout(blockWndSizer_row1)
        blockWndSizer.addWidget(sbs2blockTSBS)
        blockWndSizer.addWidget(sbs2blockListBS)
    
        # ========== LAYOUT TAB (начало) ==========
        self.blockListSlider = QSlider(Qt.Horizontal)
        self.blockListSlider.setRange(0, 15)
        self.blockListSlider.context = "list"
        
        self.blockListPosText = QLabel("0")
        self.blockListMaxText = QLabel("0")
        
        self.blockListPanels = []
        blockListSizer = QGridLayout()
        numC, numR = 7, 8
        for idx in range(numC * numR):
            p = rompanel.SpritePanel(layoutWindow, None, 24, 24, self.palette, scale=1.5, bg=16, func=self.OnClickBlockListPanel, edit=True, grid=24)
            p.index = idx
            self.blockListPanels.append(p)
            row = idx // numC
            col = idx % numC
            blockListSizer.addWidget(p, row, col, Qt.AlignCenter)
        
        self.blockListLeftText = QLabel("L (0)")
        self.blockListRightText = QLabel("R (0)")
        self.blockListLeftPanel = rompanel.SpritePanel(layoutWindow, None, 24, 24, self.palette, scale=1.5, bg=17, func=self.OnClickBlockSelPanel)
        self.blockListRightPanel = rompanel.SpritePanel(layoutWindow, None, 24, 24, self.palette, scale=1.5, bg=18, func=self.OnClickBlockSelPanel)
        self.blockListOverText = QLabel("Block 000")
        self.blockListOverText.setFont(QFont("Courier New", 12, QFont.Bold))
        
        blockListSliderSizer = QHBoxLayout()
        blockListSliderSizer.addWidget(self.blockListPosText, 0, Qt.AlignCenter)
        blockListSliderSizer.addWidget(self.blockListSlider)
        blockListSliderSizer.addWidget(self.blockListMaxText, 0, Qt.AlignCenter)
        blockListSliderSizer.addWidget(self.blockListOverText, 0, Qt.AlignCenter)
        
        layoutWindowSizer2 = QGroupBox("Block List")
        layoutBlockListSizer = QVBoxLayout(layoutWindowSizer2)
        layoutBlockListSizer.addLayout(blockListSizer)
        layoutBlockListSizer.addLayout(blockListSliderSizer)
        
        layoutWindowSizer_layout = QVBoxLayout()
        layoutWindowSizer_layout.addWidget(layoutWindowSizer2)
        
        layoutInterBlockSizer = QGroupBox("Selected Blocks")
        layoutInterBlockSizer_layout = QVBoxLayout(layoutInterBlockSizer)
        self.interBlockRadio = QRadioButton("Graphical Block")
        self.interBlockRadio.setChecked(True)
        self.interBlockRadio.context = 0x03ff
        blockListSelSizer = QGridLayout()
        blockListSelSizer.addWidget(self.blockListLeftText, 0, 0, Qt.AlignCenter)
        blockListSelSizer.addWidget(self.blockListRightText, 0, 1, Qt.AlignCenter)
        blockListSelSizer.addWidget(self.blockListLeftPanel, 1, 0, Qt.AlignCenter)
        blockListSelSizer.addWidget(self.blockListRightPanel, 1, 1, Qt.AlignCenter)
        layoutInterBlockSizer_layout.addWidget(self.interBlockRadio, 0, Qt.AlignCenter)
        layoutInterBlockSizer_layout.addLayout(blockListSelSizer)
        
        # Movement Data / Event Data
        layoutInterObsSizer = QGroupBox("Movement Data")
        layoutInterObsGrid = QGridLayout()
        layoutInterObsSizer.setLayout(layoutInterObsGrid)
        layoutInterEventSizer = QGroupBox("Event Data")
        layoutInterEventGrid = QGridLayout()
        layoutInterEventSizer.setLayout(layoutInterEventGrid)
        
        radios = [None] * 12
        texts = ["Obstructed", "* Stairs", "Warp", "Trigger",
                 "Table/Desk", "Chest", "Barrel", "Vase",
                 "Searchable", "Perm Copy", "Temp Copy", "Undo Copy"]
        masks = [0xc000, 0x4000, 0x1000, 0x1400, 0x2800, 0x1800, 0x3000, 0x2c00, 0x1c00, 0x0400, 0x0800, 0x0c00]
        
        for i, mask in enumerate(masks):
            rb = QRadioButton(texts[i])
            rb.context = mask
            if i == 0:
                self.interObsRadio = rb
            elif i == 1:
                self.interStairsRadio = rb
            radios[i] = rb
            
            p = rompanel.SpritePanel(layoutWindow, None, 24, 24, self.palette, scale=1, bg=None, draw=self.drawMapData)
            p.special = mask
            
            if i < 2:
                sizer = layoutInterObsGrid
                row = (i // 2) * 2
                col = (i % 2) * 2
                sizer.addWidget(p, row, col)
                sizer.addWidget(rb, row, col+1)
            else:
                sizer = layoutInterEventGrid
                row = (i // 2 - 1) * 2
                col = (i % 2) * 2
                sizer.addWidget(p, row, col)
                sizer.addWidget(rb, row, col+1)
        
        layoutWindowSubSizer = QVBoxLayout()
        layoutWindowSubSizer.addWidget(layoutInterBlockSizer)
        layoutWindowSubSizer.addWidget(layoutInterObsSizer)
        layoutWindowSubSizer.addWidget(layoutInterEventSizer)
        
        layoutWndSizer.addLayout(layoutWindowSubSizer)
        layoutWndSizer.addWidget(layoutWindowSizer2)
        # --- конец Layout Tab ---

        # ========== SETUPS TAB (пустой) ==========

        # ========== INTERACTION TAB ==========
        sbs2eventSizer = QHBoxLayout()
        sbs2eventCol1Sizer = QVBoxLayout()
        
        self.eventTypeBS = QGroupBox("Event Type")
        eventTypeBS_layout = QVBoxLayout(self.eventTypeBS)
        self.eventTypeList = QComboBox()
        self.eventTypeList.addItems(["Warps", "Block Copies", "Obtainable Items",
                                     "NPCs", "Scene Triggers", "Books, Signs, Etc."])
        eventTypeBS_layout.addWidget(self.eventTypeList)
        
        self.eventConfigBS = QGroupBox("Configuration (if applicable)")
        eventConfigBS_layout = QVBoxLayout(self.eventConfigBS)
        self.eventConfigList = QListWidget()
        self.eventConfigList.setFixedHeight(58)
        self.eventConfigAddButton = QPushButton("Add")
        self.eventConfigCopyButton = QPushButton("Copy")
        self.eventConfigDelButton = QPushButton("Delete")
        eventConfigButtonSizer = QHBoxLayout()
        eventConfigButtonSizer.addWidget(self.eventConfigAddButton)
        eventConfigButtonSizer.addWidget(self.eventConfigCopyButton)
        eventConfigButtonSizer.addWidget(self.eventConfigDelButton)
        eventConfigBS_layout.addWidget(self.eventConfigList)
        eventConfigBS_layout.addLayout(eventConfigButtonSizer)
        
        self.eventBS = QGroupBox("Event")
        eventBS_layout = QVBoxLayout(self.eventBS)
        self.eventList = QListWidget()
        self.eventList.setFixedHeight(82)
        self.eventAddButton = QPushButton("Add")
        self.eventCopyButton = QPushButton("Copy")
        self.eventDelButton = QPushButton("Delete")
        eventListButtonSizer = QHBoxLayout()
        eventListButtonSizer.addWidget(self.eventAddButton)
        eventListButtonSizer.addWidget(self.eventCopyButton)
        eventListButtonSizer.addWidget(self.eventDelButton)
        eventBS_layout.addWidget(self.eventList)
        eventBS_layout.addLayout(eventListButtonSizer)
        
        sbs2eventCol1Sizer.addWidget(self.eventTypeBS)
        sbs2eventCol1Sizer.addWidget(self.eventConfigBS)
        sbs2eventCol1Sizer.addWidget(self.eventBS)
        
        self.eventPropBox = QGroupBox("Event Properties")
        self.eventPropBS = QVBoxLayout(self.eventPropBox)
        
        eventPropNameSizer = QHBoxLayout()
        self.eventNameCtrl = QLineEdit()
        eventPropNameSizer.addWidget(QLabel("Name:"))
        eventPropNameSizer.addWidget(self.eventNameCtrl)
        self.eventPropBS.addLayout(eventPropNameSizer)
        
        # Warp panel
        self.eventPropWarp = QWidget()
        eventPropWarpSizer = QVBoxLayout(self.eventPropWarp)
        
        warpFromCoordGrid = QGridLayout()
        self.eventPropWarpXCheck = QCheckBox(" Trigger X:")
        self.eventPropWarpYCheck = QCheckBox(" Trigger Y:")
        self.eventPropWarpXCtrl = QSpinBox(); self.eventPropWarpXCtrl.setRange(0, 64)
        self.eventPropWarpYCtrl = QSpinBox(); self.eventPropWarpYCtrl.setRange(0, 64)
        warpFromCoordGrid.addWidget(self.eventPropWarpXCheck, 0, 0)
        warpFromCoordGrid.addWidget(self.eventPropWarpXCtrl, 0, 1)
        warpFromCoordGrid.addWidget(self.eventPropWarpYCheck, 1, 0)
        warpFromCoordGrid.addWidget(self.eventPropWarpYCtrl, 1, 1)

        warpDestMapSizer = QVBoxLayout()
        self.eventPropWarpChangeCheck = QCheckBox(" Change map to:")
        self.eventPropWarpMapList = QComboBox()
        self.eventPropWarpMapList.addItems([s.name for s in self.rom.data["maps"]])
        warpDestMapSizer.addWidget(self.eventPropWarpChangeCheck)
        warpDestMapSizer.addWidget(self.eventPropWarpMapList)

        warpToCoordSizer = QHBoxLayout()
        warpToCoordGrid = QGridLayout()
        self.eventPropWarpDestXCheck = QCheckBox(" New X: ")
        self.eventPropWarpDestYCheck = QCheckBox(" New Y: ")
        self.eventPropWarpDestXCtrl = QSpinBox(); self.eventPropWarpDestXCtrl.setRange(0, 64)
        self.eventPropWarpDestYCtrl = QSpinBox(); self.eventPropWarpDestYCtrl.setRange(0, 64)
        warpToCoordGrid.addWidget(self.eventPropWarpDestXCheck, 0, 0)
        warpToCoordGrid.addWidget(self.eventPropWarpDestXCtrl, 0, 1)
        warpToCoordGrid.addWidget(self.eventPropWarpDestYCheck, 1, 0)
        warpToCoordGrid.addWidget(self.eventPropWarpDestYCtrl, 1, 1)

        self.warpFacingUpRadio = QRadioButton()
        self.warpFacingLeftRadio = QRadioButton()
        self.warpFacingRightRadio = QRadioButton()
        self.warpFacingDownRadio = QRadioButton()
        self.warpFacingUpRadio.context = 1
        self.warpFacingLeftRadio.context = 2
        self.warpFacingRightRadio.context = 0
        self.warpFacingDownRadio.context = 3
        self.warpFacingRadios = [self.warpFacingRightRadio, self.warpFacingUpRadio,
                                 self.warpFacingLeftRadio, self.warpFacingDownRadio]
        warpFacingFacingMidSizer = QHBoxLayout()
        warpFacingFacingMidSizer.addWidget(self.warpFacingLeftRadio)
        warpFacingFacingMidSizer.addWidget(self.warpFacingRightRadio)
        warpFacingSizer = QVBoxLayout()
        warpFacingSizer.addWidget(QLabel("Facing"), 0, Qt.AlignCenter)
        warpFacingSizer.addWidget(self.warpFacingUpRadio, 0, Qt.AlignCenter)
        warpFacingSizer.addLayout(warpFacingFacingMidSizer)
        warpFacingSizer.addWidget(self.warpFacingDownRadio, 0, Qt.AlignCenter)
        warpToCoordSizer.addLayout(warpToCoordGrid)
        warpToCoordSizer.addLayout(warpFacingSizer)

        eventPropWarpSizer.addLayout(warpFromCoordGrid)
        eventPropWarpSizer.addLayout(warpDestMapSizer)
        eventPropWarpSizer.addLayout(warpToCoordSizer)
        self.eventPropWarp.hide()

        # Copy panel
        self.eventPropCopy = QWidget()
        eventPropCopySizer = QVBoxLayout(self.eventPropCopy)
        copyCoordGrid = QGridLayout()
        copyTrigXText = QLabel("Trigger X: ")
        copyTrigYText = QLabel("Trigger Y: ")
        copyWidthText = QLabel("Width: ")
        copyHeightText = QLabel("Height: ")
        copySrcXText = QLabel("From X: ")
        copySrcYText = QLabel("From Y: ")
        copyDestXText = QLabel("To X: ")
        copyDestYText = QLabel("To Y: ")
        self.eventPropCopyTrigXCtrl = QSpinBox(); self.eventPropCopyTrigXCtrl.setRange(0, 64)
        self.eventPropCopyTrigYCtrl = QSpinBox(); self.eventPropCopyTrigYCtrl.setRange(0, 64)
        self.eventPropCopyWidthCtrl = QSpinBox(); self.eventPropCopyWidthCtrl.setRange(0, 64)
        self.eventPropCopyHeightCtrl = QSpinBox(); self.eventPropCopyHeightCtrl.setRange(0, 64)
        self.eventPropCopySrcXCtrl = QSpinBox(); self.eventPropCopySrcXCtrl.setRange(0, 64)
        self.eventPropCopySrcYCtrl = QSpinBox(); self.eventPropCopySrcYCtrl.setRange(0, 64)
        self.eventPropCopyDestXCtrl = QSpinBox(); self.eventPropCopyDestXCtrl.setRange(0, 64)
        self.eventPropCopyDestYCtrl = QSpinBox(); self.eventPropCopyDestYCtrl.setRange(0, 64)
        copyCoordGrid.addWidget(copyTrigXText, 0, 0)
        copyCoordGrid.addWidget(self.eventPropCopyTrigXCtrl, 0, 1)
        copyCoordGrid.addWidget(copyTrigYText, 1, 0)
        copyCoordGrid.addWidget(self.eventPropCopyTrigYCtrl, 1, 1)
        copyCoordGrid2 = QGridLayout()
        copyCoordGrid2.addWidget(copySrcXText, 0, 0)
        copyCoordGrid2.addWidget(self.eventPropCopySrcXCtrl, 0, 1)
        copyCoordGrid2.addWidget(copyDestXText, 0, 2)
        copyCoordGrid2.addWidget(self.eventPropCopyDestXCtrl, 0, 3)
        copyCoordGrid2.addWidget(copyWidthText, 0, 4)
        copyCoordGrid2.addWidget(self.eventPropCopyWidthCtrl, 0, 5)
        copyCoordGrid2.addWidget(copySrcYText, 1, 0)
        copyCoordGrid2.addWidget(self.eventPropCopySrcYCtrl, 1, 1)
        copyCoordGrid2.addWidget(copyDestYText, 1, 2)
        copyCoordGrid2.addWidget(self.eventPropCopyDestYCtrl, 1, 3)
        copyCoordGrid2.addWidget(copyHeightText, 1, 4)
        copyCoordGrid2.addWidget(self.eventPropCopyHeightCtrl, 1, 5)
        copyRadioSizer = QVBoxLayout()
        self.eventPropCopyFlagRadio = QRadioButton(" If flag is set (story/progress-based)")
        self.eventPropCopyPermRadio = QRadioButton(" Step-Triggered (doors, switches)")
        self.eventPropCopyTempRadio = QRadioButton(" Temporary Step-Triggered (roofs)")
        self.eventPropCopyFlagRadio.context = 0
        self.eventPropCopyPermRadio.context = 1
        self.eventPropCopyTempRadio.context = 2
        self.eventPropCopyFlagCtrl = QSpinBox(); self.eventPropCopyFlagCtrl.setRange(0, 65535)
        copyRadioSizer.addWidget(self.eventPropCopyFlagRadio)
        copyRadioSizer.addWidget(self.eventPropCopyFlagCtrl)
        copyRadioSizer.addWidget(self.eventPropCopyPermRadio)
        copyRadioSizer.addWidget(self.eventPropCopyTempRadio)
        copyWarningText = QLabel("(Note: Permanent block copies are undone upon changing maps; temporary copies are undone by stepping on a block with the \"undo copy\" flag set.)")
        copyWarningText.setWordWrap(True)
        self.eventPropCopyBlankCheck = QCheckBox("Copy blank blocks")
        eventPropCopySizer.addLayout(copyCoordGrid)
        eventPropCopySizer.addWidget(self.eventPropCopyBlankCheck)
        eventPropCopySizer.addLayout(copyCoordGrid2)
        eventPropCopySizer.addLayout(copyRadioSizer)
        eventPropCopySizer.addWidget(copyWarningText)
        self.eventPropCopy.hide()

        # Item panel
        self.eventPropItem = QWidget()
        eventPropItemSizer = QVBoxLayout(self.eventPropItem)
        itemCoordGrid = QGridLayout()
        itemXText = QLabel("X: ")
        itemYText = QLabel("Y: ")
        itemFlagText = QLabel("Flag: ")
        self.eventPropItemXCtrl = QSpinBox(); self.eventPropItemXCtrl.setRange(0, 64)
        self.eventPropItemYCtrl = QSpinBox(); self.eventPropItemYCtrl.setRange(0, 64)
        self.eventPropItemFlagCtrl = QSpinBox(); self.eventPropItemFlagCtrl.setRange(0, 255)
        itemCoordGrid.addWidget(itemXText, 0, 0)
        itemCoordGrid.addWidget(self.eventPropItemXCtrl, 0, 1)
        itemCoordGrid.addWidget(itemFlagText, 0, 2)
        itemCoordGrid.addWidget(self.eventPropItemFlagCtrl, 0, 3)
        itemCoordGrid.addWidget(itemYText, 1, 0)
        itemCoordGrid.addWidget(self.eventPropItemYCtrl, 1, 1)
        itemListSizer = QVBoxLayout()
        self.eventPropItemItemRadio = QRadioButton("Item: ")
        self.eventPropItemGoldRadio = QRadioButton("Gold: ")
        self.eventPropItemNoneRadio = QRadioButton("Nothing")
        self.eventPropItemItemRadio.setChecked(True)
        self.eventPropItemList = QComboBox()
        self.eventPropItemList.addItems([i.name for i in self.rom.data["items"][:-1]])
        self.eventPropItemGoldCtrl = QSpinBox(); self.eventPropItemGoldCtrl.setRange(10, 65535)
        self.eventPropItemItemRadio.context = 0
        self.eventPropItemList.context = 0
        self.eventPropItemGoldRadio.context = 1
        self.eventPropItemGoldCtrl.context = 1
        self.eventPropItemNoneRadio.context = 2
        itemListSizer.addWidget(self.eventPropItemItemRadio)
        itemListSizer.addWidget(self.eventPropItemList)
        itemListSizer.addWidget(self.eventPropItemGoldRadio)
        itemListSizer.addWidget(self.eventPropItemGoldCtrl)
        itemListSizer.addWidget(self.eventPropItemNoneRadio)
        self.eventPropItemChestCheck = QCheckBox("Item is in a chest (graphic purposes only)")
        itemGoldWarningText = QLabel("(Note: Due to a restriction in the way the ROM is laid out, the maximum amount of gold that can be found is 130.)")
        itemGoldWarningText.setWordWrap(True)
        eventPropItemSizer.addLayout(itemCoordGrid)
        eventPropItemSizer.addLayout(itemListSizer)
        eventPropItemSizer.addWidget(self.eventPropItemChestCheck)
        eventPropItemSizer.addWidget(itemGoldWarningText)
        self.eventPropItem.hide()

        self.eventPropBS.addWidget(self.eventPropWarp)
        self.eventPropBS.addWidget(self.eventPropCopy)
        self.eventPropBS.addWidget(self.eventPropItem)

        sbs2eventSizer.addLayout(sbs2eventCol1Sizer)
        sbs2eventSizer.addWidget(self.eventPropBox)

        eventWndSizer.addLayout(sbs2eventSizer)
        # --- конец Interaction Tab ---

        # ========== ANIMATIONS TAB ==========
        sbs2animSizer = QVBoxLayout()
        
        animListSizer = QGroupBox("Select animation.")
        animListSizer_layout = QVBoxLayout(animListSizer)
        self.animList = QListWidget()
        self.animList.setFixedSize(120, 100)
        self.animAddButton = QPushButton("Add")
        self.animCopyButton = QPushButton("Copy")
        self.animDelButton = QPushButton("Del")
        animButtonSizer = QHBoxLayout()
        animButtonSizer.addWidget(self.animAddButton)
        animButtonSizer.addWidget(self.animCopyButton)
        animButtonSizer.addWidget(self.animDelButton)
        animListSizer_layout.addWidget(self.animList)
        animListSizer_layout.addLayout(animButtonSizer)
        
        animPropSizer = QGroupBox("Animation Properties")
        animPropSizer_layout = QVBoxLayout(animPropSizer)
        self.animNameCtrl = QLineEdit()
        self.animTSList = QComboBox()
        self.animStart = QSpinBox(); self.animStart.setRange(0, 128)
        self.animEnd = QSpinBox(); self.animEnd.setRange(0, 128)
        self.animDest = QSpinBox(); self.animDest.setRange(0, 0x37f)
        self.animDelay = QSpinBox(); self.animDelay.setRange(0, 255)
        
        animPropRow1Sizer = QHBoxLayout()
        animPropRow1Sizer.addWidget(QLabel("Tileset"))
        animPropRow1Sizer.addWidget(self.animTSList)
        animPropRow2Sizer = QHBoxLayout()
        animPropRow2Sizer.addWidget(QLabel("Start"))
        animPropRow2Sizer.addWidget(self.animStart)
        animPropRow2Sizer.addWidget(QLabel("End"))
        animPropRow2Sizer.addWidget(self.animEnd)
        animPropRow2Sizer.addWidget(QLabel("Dest"))
        animPropRow2Sizer.addWidget(self.animDest)
        animPropRow2Sizer.addWidget(QLabel("Delay"))
        animPropRow2Sizer.addWidget(self.animDelay)
        
        animPropNameSizer = QHBoxLayout()
        animPropNameSizer.addWidget(QLabel("Name: "))
        animPropNameSizer.addWidget(self.animNameCtrl)
        
        animPropSizer_layout.addLayout(animPropNameSizer)
        animPropSizer_layout.addLayout(animPropRow1Sizer)
        animPropSizer_layout.addLayout(animPropRow2Sizer)
        
        sbs2animRow1Sizer = QHBoxLayout()
        sbs2animRow1Sizer.addWidget(animListSizer)
        sbs2animRow1Sizer.addWidget(animPropSizer)
        
        animPreviewSizer = QGroupBox("Preview")
        animPreviewSizer_layout = QVBoxLayout(animPreviewSizer)
        animPreviewSizer_layout.addWidget(QLabel("Not implemented."))
        
        animTSSizer = QGroupBox("Tileset")
        animTSSizer_layout = QVBoxLayout(animTSSizer)
        tsScroll2 = QScrollArea()
        tsScroll2.setWidgetResizable(True)
        tsScroll2.setFixedSize(330, 120)
        tsWidget2 = QWidget()
        tsLayout2 = QVBoxLayout(tsWidget2)
        self.animTSPanel = rompanel.SpritePanel(tsWidget2, None, 8*16, 8*8, self.palette, scale=3, bg=16, func=self.OnClickAnimTSPanel, edit=True, grid=8)
        tsLayout2.addWidget(self.animTSPanel)
        tsScroll2.setWidget(tsWidget2)
        animTSSizer_layout.addWidget(tsScroll2)
        
        sbs2animRow2Sizer = QHBoxLayout()
        sbs2animRow2Sizer.addWidget(animPreviewSizer)
        sbs2animRow2Sizer.addWidget(animTSSizer)
        
        sbs2animSizer.addLayout(sbs2animRow1Sizer)
        sbs2animSizer.addLayout(sbs2animRow2Sizer)
        
        animWndSizer.addLayout(sbs2animSizer)
        # --- конец Animations Tab ---

        # Добавление вкладок
        self.mainNotebook.addTab(genWindow, "General")
        self.mainNotebook.addTab(self.blockWindow, "Blocks")
        self.mainNotebook.addTab(layoutWindow, "Layout")
        self.mainNotebook.addTab(configWindow, "Setups")
        self.mainNotebook.addTab(eventWindow, "Interaction")
        self.mainNotebook.addTab(animWindow, "Animations")
        
        sbs2.addWidget(self.mainNotebook)
        
        # Map viewer
        self.mapViewer = window.MapViewer(self, None, self.parent)
        self.mapViewer.init(None, None)
        
        # Главный layout
        self.sizer.addWidget(self.sbs2_widget, 0, 0)
        self.sizer.addWidget(self.mapViewer, 0, 1)
        self.sizer.setColumnStretch(1, 1)
        
        self.curEventProps = None

        self.changeMap(0)

        # Connections
        self.mainNotebook.currentChanged.connect(self.OnChangePage)
        self.paletteList.currentIndexChanged.connect(self.OnSelectPalette)
        for tsl in self.tilesetLists:
            tsl.currentIndexChanged.connect(self.OnSelectTileset)
        self.areaList.currentIndexChanged.connect(self.OnSelectArea)
        self.areaMusicList.currentIndexChanged.connect(self.OnSelectAreaMusic)
        self.areaLayer2Check.stateChanged.connect(self.OnToggleAreaLayer2Check)
        self.areaLayer2ForeRadio.toggled.connect(self.OnSelectAreaLayer2Type)
        self.areaLayer2BackRadio.toggled.connect(self.OnSelectAreaLayer2Type)
        self.blockTSList.currentIndexChanged.connect(self.OnSelectBlockTileset)
        self.blockEditSlider.valueChanged.connect(self.OnChangeBlockPage)
        self.blockListSlider.valueChanged.connect(self.OnChangeBlockPage)
        self.eventTypeList.currentIndexChanged.connect(self.OnSelectEventType)
        self.eventList.currentRowChanged.connect(self.OnSelectEvent)
        self.eventNameCtrl.textChanged.connect(self.OnChangeEventName)
        for r in [self.interBlockRadio, self.interObsRadio, self.interStairsRadio] + radios[2:]:
            r.toggled.connect(self.OnClickLayoutInterRadio)
        self.animList.currentRowChanged.connect(self.OnChangeAnim)
        self.animTSList.currentIndexChanged.connect(self.OnSelectAnimTS)
        self.animStart.valueChanged.connect(self.OnChangeAnimStart)
        self.animEnd.valueChanged.connect(self.OnChangeAnimEnd)
        self.animDest.valueChanged.connect(self.OnChangeAnimDest)
        self.animDelay.valueChanged.connect(self.OnChangeAnimDelay)

        # Сигналы для warp/copy/item
        self.eventPropWarpXCtrl.valueChanged.connect(self.OnChangeWarpXCtrl)
        self.eventPropWarpYCtrl.valueChanged.connect(self.OnChangeWarpYCtrl)
        self.eventPropWarpDestXCtrl.valueChanged.connect(self.OnChangeWarpDestXCtrl)
        self.eventPropWarpDestYCtrl.valueChanged.connect(self.OnChangeWarpDestYCtrl)
        self.eventPropWarpXCheck.stateChanged.connect(self.OnToggleWarpLineCheck)
        self.eventPropWarpYCheck.stateChanged.connect(self.OnToggleWarpLineCheck)
        self.eventPropWarpDestXCheck.stateChanged.connect(self.OnToggleWarpDestLineCheck)
        self.eventPropWarpDestYCheck.stateChanged.connect(self.OnToggleWarpDestLineCheck)
        self.eventPropWarpChangeCheck.stateChanged.connect(self.OnToggleWarpChangeCheck)
        self.eventPropWarpMapList.currentIndexChanged.connect(self.OnSelectWarpMap)
        for r in self.warpFacingRadios:
            r.toggled.connect(self.OnSelectWarpFacing)
        self.eventPropCopyBlankCheck.stateChanged.connect(self.OnToggleCopyBlankCheck)
        self.eventPropCopyTrigXCtrl.valueChanged.connect(self.OnChangeCopyTrigXCtrl)
        self.eventPropCopyTrigYCtrl.valueChanged.connect(self.OnChangeCopyTrigYCtrl)
        self.eventPropCopySrcXCtrl.valueChanged.connect(self.OnChangeCopySrcXCtrl)
        self.eventPropCopySrcYCtrl.valueChanged.connect(self.OnChangeCopySrcYCtrl)
        self.eventPropCopyDestXCtrl.valueChanged.connect(self.OnChangeCopyDestXCtrl)
        self.eventPropCopyDestYCtrl.valueChanged.connect(self.OnChangeCopyDestYCtrl)
        self.eventPropCopyWidthCtrl.valueChanged.connect(self.OnChangeCopyWidthCtrl)
        self.eventPropCopyHeightCtrl.valueChanged.connect(self.OnChangeCopyHeightCtrl)
        self.eventPropCopyFlagRadio.toggled.connect(self.OnClickCopyTypeRadio)
        self.eventPropCopyPermRadio.toggled.connect(self.OnClickCopyTypeRadio)
        self.eventPropCopyTempRadio.toggled.connect(self.OnClickCopyTypeRadio)
        self.eventPropCopyFlagCtrl.valueChanged.connect(self.OnChangeCopyFlagCtrl)
        self.eventPropItemXCtrl.valueChanged.connect(self.OnChangeItemXCtrl)
        self.eventPropItemYCtrl.valueChanged.connect(self.OnChangeItemYCtrl)
        self.eventPropItemFlagCtrl.valueChanged.connect(self.OnChangeItemFlagCtrl)
        self.eventPropItemItemRadio.toggled.connect(self.OnSelectItemType)
        self.eventPropItemList.currentIndexChanged.connect(self.OnSelectItemType)
        self.eventPropItemGoldRadio.toggled.connect(self.OnSelectItemType)
        self.eventPropItemGoldCtrl.valueChanged.connect(self.OnSelectItemType)
        self.eventPropItemNoneRadio.toggled.connect(self.OnSelectItemType)
        self.eventPropItemChestCheck.stateChanged.connect(self.OnToggleItemChestCheck)
        
    # ========== МЕТОДЫ КЛАССА ==========

    def OnShow(self):
        import shiboken6
        for p in range(16):
            if p < len(self.colorPanels):
                cp = self.colorPanels[p]
                if shiboken6.isValid(cp):
                    cp.setStyleSheet(f"background-color: {self.palette.colors[p]};")
                    cp.update()
        self.updateMapViewerContext()

    def OnChangePage(self, idx):
        self.updateMapViewerContext()

    def updateMapViewerContext(self):
        if self.mapViewer.inited:
            pg = self.mainNotebook.currentIndex()
            if pg == 0:
                self.mapViewer.updateContext(consts.VC_AREA)
            elif pg == 2:
                self.mapViewer.updateContext(self.vcsBlock[self.blockEditMode])
            elif pg == 4:
                self.mapViewer.updateContext(self.vcsEvent[min(len(self.vcsEvent)-1, self.curEventType)])
            else:
                self.mapViewer.updateContext(consts.VC_NOTHING)
            self.mapViewer.refreshMapView()
            
    def OnChangeLayoutPage(self, idx):
        oldVM = self.curViewMode
        self.curViewMode = idx != 0
        self.updateMapViewerContext()

    def OnCheckViewAll(self, state):
        self.viewAll = state == Qt.Checked
        self.updateMapViewerContext()    

    def OnClickLayoutInterRadio(self, checked):
        obj = self.sender()
        if checked and hasattr(obj, 'context'):
            if obj.context == 0x3ff:
                self.blockEditMode = 0
            else:
                self.blockEditMode = 1
            self.updateMapViewerContext()
            self.curInterFlag = obj.context

    def OnChangeBlockPage(self, value):
        obj = self.sender()
        if hasattr(obj, 'context'):
            if obj.context == "edit":
                self.curEditBlockPage = value
                self.changeBlockEditList()
            elif obj.context == "list":
                self.curListBlockPage = value
                self.changeBlockList()

    def OnClickBlockSelPanel(self, obj):
        tmp = self.curListBlockLeft
        self.curListBlockLeft = self.curListBlockRight
        self.curListBlockRight = tmp
        self.blockListLeftPanel.refreshSprite(self.map.blocks[self.curListBlockLeft].pixels)
        self.blockListLeftPanel.update()
        self.blockListRightPanel.refreshSprite(self.map.blocks[self.curListBlockRight].pixels)
        self.blockListRightPanel.update()

    def changeBlockEditList(self):
        maxPages = len(self.map.blocks) // len(self.blockEditPanels)
        self.blockEditSlider.setMaximum(maxPages)
        self.blockEditPosText.setText(str(self.curEditBlockPage))
        self.blockEditMaxText.setText(str(maxPages))
        for idx, p in enumerate(self.blockEditPanels):
            realIdx = self.curEditBlockPage * len(self.blockEditPanels) + idx
            if realIdx < len(self.map.blocks):
                p.index = realIdx
                p.refreshSprite(self.map.blocks[realIdx].pixels)
                p.bg = 17 if realIdx == self.curEditBlock else None
                self.blockEditText[idx].setText(str(realIdx))
            else:
                p.refreshSprite([])
                p.bg = None
                self.blockEditText[idx].setText("")
        self.blockEditSlider.update()

    def changeBlockList(self):
        maxPages = len(self.map.blocks) // len(self.blockListPanels)
        self.blockListSlider.setMaximum(maxPages)
        self.blockListPosText.setText(str(self.curListBlockPage))
        self.blockListMaxText.setText(str(maxPages))
        for idx, p in enumerate(self.blockListPanels):
            realIdx = self.curListBlockPage * len(self.blockListPanels) + idx
            if realIdx < len(self.map.blocks):
                p.index = realIdx
                p.refreshSprite(self.map.blocks[realIdx].pixels)
            else:
                p.index = None
                p.refreshSprite([])
        self.refreshBlockListSelPanels()

    def refreshBlockListSelPanels(self):
        self.blockListLeftPanel.refreshSprite(self.map.blocks[self.curListBlockLeft].pixels)
        self.blockListLeftPanel.update()
        self.blockListLeftText.setText(f"L ({self.curListBlockLeft})")
        self.blockListRightPanel.refreshSprite(self.map.blocks[self.curListBlockRight].pixels)
        self.blockListRightPanel.update()
        self.blockListRightText.setText(f"R ({self.curListBlockRight})")

    def changeColors(self, num):
        palette = self.rom.data["palettes"][num]
        for cp in self.colorPanels:
            cp.setStyleSheet(f"background-color: {palette.colors[cp.num]};")
            cp.update()
        self.blockPanel.palette = palette
        for p in self.blockEditPanels: p.palette = palette
        for p in self.blockListPanels: p.palette = palette
        self.tilesetPanel.palette = palette
        self.blockEditLeftPanel.palette = palette
        self.blockEditRightPanel.palette = palette
        self.blockListLeftPanel.palette = palette
        self.blockListRightPanel.palette = palette

    def refreshPixels(self):
        tsIdx = self.curTilesetIdx
        if not self.tileset.loaded:
            self.rom.getTilesets(tsIdx, tsIdx)
        self.tilesetPanel.pixels = []
        for tRow in range(8):
            for pRow in range(8):
                row = "".join([self.tileset.tiles[tRow*16+to].pixels[pRow] for to in range(16)])
                self.tilesetPanel.pixels.append(row)

        tsAnimIdx = self.curAnimTSIdx
        if not self.animTileset.loaded:
            self.rom.getTilesets(tsAnimIdx, tsAnimIdx)
        self.animTSPanel.pixels = []
        for tRow in range(8):
            for pRow in range(8):
                row = "".join([self.animTileset.tiles[tRow*16+to].pixels[pRow] for to in range(16)])
                self.animTSPanel.pixels.append(row)

        self.blockPanel.refreshSprite(self.map.blocks[self.curEditBlock].pixels)
        self.blockPanel.update()
        self.tilesetPanel.refreshSprite()
        self.tilesetPanel.update()
        self.animTSPanel.refreshSprite()
        self.animTSPanel.update()
        self.refreshTilePanels()

    def refreshTilePanels(self):
        ts = (self.curLeftTile - 0x100) // 0x80
        idx = self.curLeftTile % 0x80
        if ts < len(self.map.tilesetIdxes) and self.map.tilesetIdxes[ts] < len(self.rom.data["tilesets"]):
            self.blockEditLeftPanel.refreshSprite(
                self.rom.data["tilesets"][self.map.tilesetIdxes[ts]].tiles[idx].pixels)
        ts = (self.curRightTile - 0x100) // 0x80
        idx = self.curRightTile % 0x80
        if ts < len(self.map.tilesetIdxes) and self.map.tilesetIdxes[ts] < len(self.rom.data["tilesets"]):
            self.blockEditRightPanel.refreshSprite(
                self.rom.data["tilesets"][self.map.tilesetIdxes[ts]].tiles[idx].pixels)
        self.blockEditLeftPanel.update()
        self.blockEditRightPanel.update()

    def OnSelectPalette(self, idx):
        self.map.paletteIdx = idx
        self.changePalette(idx)
        self.modify()
        if self.mapViewer.inited:
            self.mapViewer.mapViewPanel.palette = self.palette
            self.mapViewer.mapViewPanel.updateBlockBMPs()
            self.mapViewer.refreshMapView()

    def OnSelectTileset(self, idx):
        obj = self.sender()
        for i, tsl in enumerate(self.tilesetLists):
            if obj is tsl:
                self.map.tilesetIdxes[i] = idx
                if not self.rom.data["tilesets"][idx].loaded:
                    self.rom.getTilesets(idx, idx)
                for b in self.map.blocks:
                    if i in b.uniqueTilesetIdxes:
                        for n, tsi in enumerate(b.tilesetIdxes):
                            if tsi == i:
                                b.tiles[n] = self.rom.data["tilesets"][idx].tiles[b.tileIdxes[n] % 128]
                        b.createPixelArray()
                self.updateBlockTSList()
                self.updateTileset()
                self.changeBlockList()
                self.changeBlockEditList()
                self.updateAnimTSList()
                self.updateAnimTileset()
                self.refreshPixels()
                self.modify()
                self.mapViewer.mapViewPanel.updateBlockBMPs()
                break

    def changePalette(self, num):
        self.paletteList.blockSignals(True)
        self.paletteList.setCurrentIndex(num)
        self.paletteList.blockSignals(False)
        self.palette = self.rom.data["palettes"][num]
        self.changeColors(num)

    def updateBlockTSList(self):
        current = self.blockTSList.currentText()
        self.blockTSList.clear()
        for idx in self.map.tilesetIdxes:
            if idx < len(self.rom.data["tilesets"]):
                self.blockTSList.addItem(self.rom.data["tilesets"][idx].name)
        idx = self.blockTSList.findText(current)
        if idx >= 0:
            self.blockTSList.setCurrentIndex(idx)

    def updateTileset(self):
        tsSelect = self.blockTSList.currentIndex()
        for i in range(5):
            if i <= tsSelect and self.map.tilesetIdxes[i] == 255:
                tsSelect += 1
        tsIdx = self.map.tilesetIdxes[tsSelect]
        self.tileset = self.rom.data["tilesets"][tsIdx]
        self.curTilesetIdx = tsIdx

    def OnSelectBlockTileset(self, idx):
        self.updateTileset()
        self.refreshPixels()

    def OnClickBlockTilesetPanel(self, obj):
        x = obj.mouseX // (obj.scale * 8)
        y = obj.mouseY // (obj.scale * 8)
        tsSel = self.blockTSList.currentIndex()
        ofs = 0
        for i in range(len(self.map.tilesetIdxes)):
            if i <= tsSel and self.map.tilesetIdxes[i] == 255:
                ofs += 1
        tsSel += ofs
        if obj.lastButton == Qt.LeftButton:
            self.curLeftTile = 0x100 + tsSel * 0x80 + y*16 + x
            self.refreshTilePanels()
        elif obj.lastButton == Qt.RightButton:
            self.curRightTile = 0x100 + tsSel * 0x80 + y*16 + x
            self.refreshTilePanels()

    def OnChangeBlockTile(self, obj):
        x = obj.mouseX // (obj.scale * 8)
        y = obj.mouseY // (obj.scale * 8)
        blk = self.map.blocks[self.curEditBlock]
        if obj.shift:
            if obj.lastButton == Qt.LeftButton:
                self.curLeftTile = blk.tileIdxes[y*3+x] & 0x7ff
                self.blockEditLeftPanel.refreshSprite(
                    self.rom.data["tilesets"][self.map.tilesetIdxes[self.curLeftTile//0x80]].tiles[self.curLeftTile%0x80].pixels)
                self.blockEditLeftPanel.update()
            elif obj.lastButton == Qt.RightButton:
                self.curRightTile = blk.tileIdxes[y*3+x] & 0x7ff
                self.blockEditRightPanel.refreshSprite(
                    self.rom.data["tilesets"][self.map.tilesetIdxes[self.curRightTile//0x80]].tiles[self.curRightTile%0x80].pixels)
                self.blockEditRightPanel.update()
            return
        elif self.curEditBlock > 2:
            if obj.ctrl and obj.lastButton == Qt.LeftButton:
                blk.tileIdxes[y*3+x] ^= 0x8000
            else:
                tile = self.curLeftTile if obj.lastButton == Qt.LeftButton else self.curRightTile
                idx = y*3 + x
                oldBot = blk.tileIdxes[idx] & 0x7ff
                newBot = tile
                if oldBot == newBot:
                    top = blk.tileIdxes[idx] & 0x1800
                    order = [0x0000, 0x0800, 0x1800, 0x1000]
                    newTop = order[(order.index(top)+1) % len(order)]
                    blk.tileIdxes[idx] = blk.tileIdxes[idx] & 0x8000 | newTop | newBot
                else:
                    blk.tileIdxes[idx] = blk.tileIdxes[idx] & 0x9800 | newBot
                    blk.tiles[idx] = self.rom.data["tilesets"][self.map.tilesetIdxes[(tile-0x100)//0x80]].tiles[tile%0x80]
        else:
            return
        blk.createPixelArray()
        self.modify()
        self.blockPanel.refreshSprite(blk.pixels)
        if self.mapViewer.inited and self.mapViewer.map == self.map:
            self.mapViewer.mapViewPanel.updateBlockBMPs(self.curEditBlock)
        if self.curEditBlock // len(self.blockListPanels) == self.curListBlockPage:
            self.blockListPanels[self.curEditBlock % len(self.blockListPanels)].refreshSprite(blk.pixels)
        for p in self.blockEditPanels:
            if p.index == self.curEditBlock:
                p.refreshSprite(blk.pixels)
                p.update()
                break
        obj.update()

    def OnClickBlockEditPanel(self, obj):
        self.blockPanel.refreshSprite(self.map.blocks[obj.index].pixels)
        self.blockPanel.update()
        self.curEditBlock = obj.index
        for p in self.blockEditPanels:
            p.bg = None
            p.update()
        self.blockEditPanels[obj.index % len(self.blockEditPanels)].bg = 17
        self.blockEditPanels[obj.index % len(self.blockEditPanels)].update()

    def OnClickBlockListPanel(self, obj):
        if obj.index is not None:
            if obj.lastButton == Qt.LeftButton:
                self.curListBlockLeft = obj.index
            elif obj.lastButton == Qt.RightButton:
                self.curListBlockRight = obj.index
            else:
                if int(self.blockListOverText.text()[6:]) != obj.index:
                    self.blockListOverText.setText(f"Block {obj.index:03d}")
                    return
            self.refreshBlockListSelPanels()

    def changeMap(self, num=None):
        if not self.rom.data["maps"][num].loaded:
            self.rom.getMaps(num, num)
        self.curMapIdx = num
        self.map = self.rom.data["maps"][num]
        self.updateModifiedIndicator(self.map.modified)
        for i in range(5):
            isUsed = self.map.tilesetIdxes[i] != 255
            self.layerChecks[i].setChecked(isUsed)
            self.tilesetLists[i].setEnabled(isUsed)
            if isUsed:
                self.tilesetLists[i].blockSignals(True)
                self.tilesetLists[i].setCurrentIndex(self.map.tilesetIdxes[i])
                self.tilesetLists[i].blockSignals(False)
        self.changePalette(self.map.paletteIdx)
        self.areaList.clear()
        self.areaList.addItems([a.name for a in self.map.areas])
        self.areaList.setCurrentIndex(0)
        self.changeArea(0)
        self.updateBlockTSList()
        self.blockTSList.setCurrentIndex(0)
        self.curLeftTile = 0x100
        self.curRightTile = 0x100
        self.curListBlockLeft = 0
        self.curListBlockRight = 0
        self.curListBlockPage = 0
        self.blockListSlider.setValue(0)
        self.curEditBlock = 0
        self.curEditBlockPage = 0
        self.blockEditSlider.setValue(0)
        self.changeBlockEditList()
        self.changeBlockList()
        self.updateTileset()
        self.mapViewer.changeMap(self.map, self.palette)
        self.updateSetupList()
        self.changeEventType(self.curEventType)
        self.animList.clear()
        self.animList.addItems([a.name for a in self.map.anims])
        self.updateAnimTSList()
        self.changeAnim(0)
        if self.animTSList.currentIndex() >= 0:
            self.updateAnimTileset()
        self.refreshPixels()

    # --- Area methods ---
    def OnSelectArea(self, idx):
        self.changeArea(idx)

    def changeArea(self, num):
        self.areaList.blockSignals(True)
        self.areaList.setCurrentIndex(num)
        self.areaList.blockSignals(False)
        self.updateAreaProps()
        self.mapViewer.refreshMapView()

    def updateAreaProps(self):
        area = self.curArea
        hasLayer2 = area.hasLayer2
        self.areaLayer2Check.setChecked(hasLayer2)
        self.areaLayer2ForeRadio.setEnabled(hasLayer2)
        self.areaLayer2BackRadio.setEnabled(hasLayer2)
        self.areaLayer2X1Ctrl.setEnabled(hasLayer2)
        self.areaLayer2Y1Ctrl.setEnabled(hasLayer2)
        self.areaLayer2ParaXCtrl.setEnabled(hasLayer2)
        self.areaLayer2ParaYCtrl.setEnabled(hasLayer2)
        self.areaLayer2ScrXCtrl.setEnabled(hasLayer2)
        self.areaLayer2ScrYCtrl.setEnabled(hasLayer2)
        if area.layerType > 0:
            self.areaLayer2BackRadio.setChecked(True)
        else:
            self.areaLayer2ForeRadio.setChecked(True)
        self.areaLayer1X1Ctrl.setValue(area.l1x1)
        self.areaLayer1Y1Ctrl.setValue(area.l1y1)
        self.areaLayer1X2Ctrl.setValue(area.l1x2)
        self.areaLayer1Y2Ctrl.setValue(area.l1y2)
        self.areaLayer1ParaXCtrl.setValue(area.l1xp)
        self.areaLayer1ParaYCtrl.setValue(area.l1yp)
        self.areaLayer1ScrXCtrl.setValue(area.l1xs)
        self.areaLayer1ScrYCtrl.setValue(area.l1ys)
        self.areaLayer2X1Ctrl.setValue(area.l2x)
        self.areaLayer2Y1Ctrl.setValue(area.l2y)
        self.areaLayer2ParaXCtrl.setValue(area.l2xp)
        self.areaLayer2ParaYCtrl.setValue(area.l2yp)
        self.areaLayer2ScrXCtrl.setValue(area.l2xs)
        self.areaLayer2ScrYCtrl.setValue(area.l2ys)
        if area.music != 255:
            self.areaMusicList.setCurrentIndex(area.music)

    def OnSelectAreaMusic(self, idx):
        self.changeAreaMusic(idx)
        self.modify()

    def changeAreaMusic(self, num):
        self.curArea.music = num

    def OnToggleAreaLayer2Check(self, state):
        self.curArea.hasLayer2 = state
        self.updateAreaProps()
        self.mapViewer.refreshMapView()
        self.modify()

    def OnSelectAreaLayer2Type(self, checked):
        if self.areaLayer2ForeRadio.isChecked():
            self.curArea.layerType = 0
        else:
            self.curArea.layerType = 255
        self.updateAreaProps()
        self.mapViewer.refreshMapView()
        self.modify()

    def OnSelectAreaLayer1X1(self, val): self.changeAreaLayer1X1(val)
    def OnSelectAreaLayer1Y1(self, val): self.changeAreaLayer1Y1(val)
    def OnSelectAreaLayer1X2(self, val): self.changeAreaLayer1X2(val)
    def OnSelectAreaLayer1Y2(self, val): self.changeAreaLayer1Y2(val)
    def OnSelectAreaLayer1XParallax(self, val): self.curArea.l1xp = val; self.modify()
    def OnSelectAreaLayer1YParallax(self, val): self.curArea.l1yp = val; self.modify()
    def OnSelectAreaLayer1XScroll(self, val): self.curArea.l1xs = val; self.modify()
    def OnSelectAreaLayer1YScroll(self, val): self.curArea.l1ys = val; self.modify()
    def OnSelectAreaLayer2X1(self, val): self.changeAreaLayer2X1(val)
    def OnSelectAreaLayer2Y1(self, val): self.changeAreaLayer2Y1(val)
    def OnSelectAreaLayer2XParallax(self, val): self.curArea.l2xp = val; self.modify()
    def OnSelectAreaLayer2YParallax(self, val): self.curArea.l2yp = val; self.modify()
    def OnSelectAreaLayer2XScroll(self, val): self.curArea.l2xs = val; self.modify()
    def OnSelectAreaLayer2YScroll(self, val): self.curArea.l2ys = val; self.modify()

    def changeAreaLayer1X1(self, num): self.curArea.l1x1 = num; self.updateAreaProps(); self.mapViewer.refreshMapView(); self.modify()
    def changeAreaLayer1Y1(self, num): self.curArea.l1y1 = num; self.updateAreaProps(); self.mapViewer.refreshMapView(); self.modify()
    def changeAreaLayer1X2(self, num): self.curArea.l1x2 = num; self.updateAreaProps(); self.mapViewer.refreshMapView(); self.modify()
    def changeAreaLayer1Y2(self, num): self.curArea.l1y2 = num; self.updateAreaProps(); self.mapViewer.refreshMapView(); self.modify()
    def changeAreaLayer2X1(self, num): self.curArea.l2x = num; self.updateAreaProps(); self.mapViewer.refreshMapView(); self.modify()
    def changeAreaLayer2Y1(self, num): self.curArea.l2y = num; self.updateAreaProps(); self.mapViewer.refreshMapView(); self.modify()

    # --- Event methods ---
    def updateSetupList(self):
        enabled = self.curEventType in [3,4,5]
        self.eventNameCtrl.setEnabled(True)
        self.eventConfigList.setEnabled(enabled)
        self.eventConfigAddButton.setEnabled(enabled)
        self.eventConfigCopyButton.setEnabled(enabled)
        self.eventConfigDelButton.setEnabled(enabled)

    def changeSetup(self, num):
        setup = self.map.setups[num]
        self.eventConfigList.setCurrentRow(num)

    def OnSelectEventType(self, idx):
        self.changeEventType(idx)

    def changeEventType(self, num):
        self.eventTypeList.blockSignals(True)
        self.eventTypeList.setCurrentIndex(num)
        self.eventTypeList.blockSignals(False)
        self.curEventType = num
        if num < len(self.vcsEvent) and self.mainNotebook.currentIndex() == 4:
            self.mapViewer.updateContext(self.vcsEvent[num])
        self.updateSetupList()
        if self.curEventProps:
            self.curEventProps.hide()
        if self.curEventType == 0:
            self.curEventProps = self.eventPropWarp
        elif self.curEventType == 1:
            self.curEventProps = self.eventPropCopy
        elif self.curEventType == 2:
            self.curEventProps = self.eventPropItem
        else:
            self.curEventProps = None
        if self.curEventProps:
            self.curEventProps.setEnabled(True)
            self.curEventProps.show()
        self.eventPropBS.update()
        self.updateEventList()
        self.mapViewer.refreshMapView()

    def updateEventList(self):
        items = self.getCurrentEventList()
        self.eventList.clear()
        if items is not None and len(items) > 0:
            self.eventList.addItems([i.name for i in items])
            self.changeEvent(0)
        else:
            self.eventNameCtrl.setText("")
            self.eventNameCtrl.setEnabled(False)
            if self.curEventProps:
                self.curEventProps.setEnabled(False)

    def OnSelectEvent(self, row):
        self.changeEvent(row)

    def changeEvent(self, num):
        self.eventList.setCurrentRow(num)
        self.curEventIdx = num
        event = self.getCurrentEvent()
        if event:
            self.eventNameCtrl.setText(event.getIndexedName())
        else:
            self.eventNameCtrl.setText("")
        t = self.curEventType
        if event:
            if t == 0:
                self.updateWarpProps()
            elif t == 1:
                self.updateCopyProps()
            elif t == 2:
                self.updateItemProps()
        self.mapViewer.refreshMapView()

    def updateWarpProps(self):
        obj = self.map.warps[self.curEventIdx]
        self.eventPropWarpXCtrl.setEnabled(not obj.sameX)
        self.eventPropWarpXCheck.setChecked(not obj.sameX)
        self.eventPropWarpYCtrl.setEnabled(not obj.sameY)
        self.eventPropWarpYCheck.setChecked(not obj.sameY)
        self.eventPropWarpDestXCheck.setChecked(not obj.sameDestX)
        self.eventPropWarpDestXCtrl.setEnabled(not obj.sameDestX)
        self.eventPropWarpDestYCheck.setChecked(not obj.sameDestY)
        self.eventPropWarpDestYCtrl.setEnabled(not obj.sameDestY)
        if obj.sameMap:
            self.eventPropWarpChangeCheck.setChecked(False)
            self.eventPropWarpMapList.setEnabled(False)
        else:
            self.eventPropWarpChangeCheck.setChecked(True)
            self.eventPropWarpMapList.setEnabled(True)
            self.eventPropWarpMapList.setCurrentIndex(obj.destmap)
        self.eventPropWarpXCtrl.setValue(obj.x)
        self.eventPropWarpYCtrl.setValue(obj.y)
        self.eventPropWarpDestXCtrl.setValue(obj.destx)
        self.eventPropWarpDestYCtrl.setValue(obj.desty)
        self.warpFacingRadios[obj.destfacing].setChecked(True)

    def OnChangeWarpXCtrl(self, val): self.changeWarpX(val)
    def changeWarpX(self, num):
        evt = self.getCurrentEvent()
        evt.x = num
        self.eventPropWarpXCtrl.setValue(num)
        self.mapViewer.refreshMapView()
        self.modify()

    def OnChangeWarpYCtrl(self, val): self.changeWarpY(val)
    def changeWarpY(self, num):
        evt = self.getCurrentEvent()
        evt.y = num
        self.eventPropWarpYCtrl.setValue(num)
        self.mapViewer.refreshMapView()
        self.modify()

    def changeWarpMap(self, num):
        event = self.getCurrentEvent()
        diffMap = self.curMapIdx != num
        event.destmap = num
        event.sameMap = not diffMap
        self.eventPropWarpMapList.setCurrentIndex(num)
        self.eventPropWarpChangeCheck.setChecked(diffMap)
        self.eventPropWarpMapList.setEnabled(diffMap)
        self.mapViewer.refreshMapView()
        self.modify()

    def OnChangeWarpDestXCtrl(self, val): self.changeWarpDestX(val)
    def changeWarpDestX(self, num):
        evt = self.getCurrentEvent()
        evt.destx = num
        self.eventPropWarpDestXCtrl.setValue(num)
        self.mapViewer.refreshMapView()
        self.modify()

    def OnChangeWarpDestYCtrl(self, val): self.changeWarpDestY(val)
    def changeWarpDestY(self, num):
        evt = self.getCurrentEvent()
        evt.desty = num
        self.eventPropWarpDestYCtrl.setValue(num)
        self.mapViewer.refreshMapView()
        self.modify()

    def OnToggleWarpLineCheck(self, state):
        event = self.getCurrentEvent()
        obj = self.sender()
        if obj == self.eventPropWarpXCheck:
            event.sameX = not state
            self.eventPropWarpXCtrl.setEnabled(state)
        elif obj == self.eventPropWarpYCheck:
            event.sameY = not state
            self.eventPropWarpYCtrl.setEnabled(state)
        self.mapViewer.refreshMapView()
        self.modify()

    def OnToggleWarpDestLineCheck(self, state):
        event = self.getCurrentEvent()
        obj = self.sender()
        if obj == self.eventPropWarpDestXCheck:
            event.sameDestX = not state
            self.eventPropWarpDestXCtrl.setEnabled(state)
        elif obj == self.eventPropWarpDestYCheck:
            event.sameDestY = not state
            self.eventPropWarpDestYCtrl.setEnabled(state)
        self.mapViewer.refreshMapView()
        self.modify()

    def OnToggleWarpChangeCheck(self, state):
        event = self.getCurrentEvent()
        event.sameMap = not state
        self.eventPropWarpMapList.setEnabled(state)
        self.mapViewer.refreshMapView()
        self.modify()

    def OnSelectWarpMap(self, idx):
        self.changeWarpMap(idx)

    def OnSelectWarpFacing(self, checked):
        if checked:
            obj = self.sender()
            self.map.warps[self.curEventIdx].destfacing = obj.context
            self.modify()

    def updateCopyProps(self):
        obj = self.map.copies[self.curEventIdx]
        [self.eventPropCopyFlagRadio, self.eventPropCopyPermRadio, self.eventPropCopyTempRadio][obj.copyType].setChecked(True)
        self.eventPropCopyFlagCtrl.setValue(obj.flag)
        self.eventPropCopyFlagCtrl.setEnabled(obj.copyType == 0)
        self.eventPropCopyTrigXCtrl.setEnabled(obj.copyType != 0)
        self.eventPropCopyTrigYCtrl.setEnabled(obj.copyType != 0)
        self.eventPropCopyTrigXCtrl.setValue(obj.x)
        self.eventPropCopyTrigYCtrl.setValue(obj.y)
        self.eventPropCopyWidthCtrl.setValue(obj.width)
        self.eventPropCopyHeightCtrl.setValue(obj.height)
        self.eventPropCopyDestXCtrl.setValue(obj.destx)
        self.eventPropCopyDestYCtrl.setValue(obj.desty)
        self.eventPropCopyBlankCheck.setChecked(obj.copyBlank)
        self.eventPropCopySrcXCtrl.setEnabled(not obj.copyBlank)
        self.eventPropCopySrcYCtrl.setEnabled(not obj.copyBlank)
        if not obj.copyBlank:
            self.eventPropCopySrcXCtrl.setValue(obj.srcx)
            self.eventPropCopySrcYCtrl.setValue(obj.srcy)

    def OnToggleCopyBlankCheck(self, state): self.setCopyBlank(state)
    def setCopyBlank(self, val=True):
        evt = self.getCurrentEvent()
        evt.copyBlank = val
        self.eventPropCopySrcXCtrl.setEnabled(not val)
        self.eventPropCopySrcYCtrl.setEnabled(not val)
        self.mapViewer.refreshMapView()
        self.modify()

    def OnChangeCopyTrigXCtrl(self, val): self.changeCopyTrigX(val)
    def changeCopyTrigX(self, num):
        evt = self.getCurrentEvent()
        evt.x = num
        self.eventPropCopyTrigXCtrl.setValue(num)
        self.mapViewer.refreshMapView()
        self.modify()

    def OnChangeCopyTrigYCtrl(self, val): self.changeCopyTrigY(val)
    def changeCopyTrigY(self, num):
        evt = self.getCurrentEvent()
        evt.y = num
        self.eventPropCopyTrigYCtrl.setValue(num)
        self.mapViewer.refreshMapView()
        self.modify()

    def OnChangeCopySrcXCtrl(self, val): self.changeCopySrcX(val)
    def changeCopySrcX(self, num):
        evt = self.getCurrentEvent()
        evt.srcx = num
        self.eventPropCopySrcXCtrl.setValue(num)
        self.mapViewer.refreshMapView()
        self.modify()

    def OnChangeCopySrcYCtrl(self, val): self.changeCopySrcY(val)
    def changeCopySrcY(self, num):
        evt = self.getCurrentEvent()
        evt.srcy = num
        self.eventPropCopySrcYCtrl.setValue(num)
        self.mapViewer.refreshMapView()
        self.modify()

    def OnChangeCopyDestXCtrl(self, val): self.changeCopyDestX(val)
    def changeCopyDestX(self, num):
        evt = self.getCurrentEvent()
        evt.destx = num
        self.eventPropCopyDestXCtrl.setValue(num)
        self.mapViewer.refreshMapView()
        self.modify()

    def OnChangeCopyDestYCtrl(self, val): self.changeCopyDestY(val)
    def changeCopyDestY(self, num):
        evt = self.getCurrentEvent()
        evt.desty = num
        self.eventPropCopyDestYCtrl.setValue(num)
        self.mapViewer.refreshMapView()
        self.modify()

    def OnChangeCopyWidthCtrl(self, val): self.changeCopyWidth(val)
    def changeCopyWidth(self, num):
        evt = self.getCurrentEvent()
        evt.width = num
        self.eventPropCopyWidthCtrl.setValue(num)
        self.mapViewer.refreshMapView()
        self.modify()

    def OnChangeCopyHeightCtrl(self, val): self.changeCopyHeight(val)
    def changeCopyHeight(self, num):
        evt = self.getCurrentEvent()
        evt.height = num
        self.eventPropCopyHeightCtrl.setValue(num)
        self.mapViewer.refreshMapView()
        self.modify()

    def OnClickCopyTypeRadio(self, checked):
        if checked:
            obj = self.sender()
            self.changeCopyType(obj.context)

    def changeCopyType(self, num):
        evt = self.getCurrentEvent()
        evt.copyType = num
        [self.eventPropCopyFlagRadio, self.eventPropCopyPermRadio, self.eventPropCopyTempRadio][num].setChecked(True)
        self.eventPropCopyTrigXCtrl.setEnabled(num != 0)
        self.eventPropCopyTrigYCtrl.setEnabled(num != 0)
        self.eventPropCopyFlagCtrl.setEnabled(num == 0)
        self.mapViewer.refreshMapView()
        self.modify()

    def OnChangeCopyFlagCtrl(self, val): self.changeCopyFlag(val)
    def changeCopyFlag(self, num):
        evt = self.getCurrentEvent()
        evt.flag = num
        self.eventPropCopyFlagCtrl.setValue(num)
        self.modify()

    def updateItemProps(self):
        obj = self.map.items[self.curEventIdx]
        self.eventNameCtrl.setEnabled(False)
        self.eventPropItemXCtrl.setValue(obj.x)
        self.eventPropItemYCtrl.setValue(obj.y)
        self.eventPropItemFlagCtrl.setValue(obj.flag)
        if obj.itemIdx < 127:
            self.eventPropItemItemRadio.setChecked(True)
            self.eventPropItemList.setCurrentIndex(obj.itemIdx)
        elif obj.itemIdx == 127:
            self.eventPropItemNoneRadio.setChecked(True)
        else:
            self.eventPropItemGoldRadio.setChecked(True)
            gold = min(130, (obj.itemIdx-127)*10)
            self.eventPropItemGoldCtrl.setValue(gold)
        self.eventPropItemChestCheck.setChecked(obj.isChest)

    def OnChangeItemXCtrl(self, val): self.changeItemX(val)
    def changeItemX(self, num):
        event = self.getCurrentEvent()
        event.x = num
        self.updateItemProps()
        self.mapViewer.refreshMapView()
        self.modify()

    def OnChangeItemYCtrl(self, val): self.changeItemY(val)
    def changeItemY(self, num):
        event = self.getCurrentEvent()
        event.y = num
        self.updateItemProps()
        self.mapViewer.refreshMapView()
        self.modify()

    def OnChangeItemFlagCtrl(self, val): self.changeItemFlag(val)
    def changeItemFlag(self, num):
        event = self.getCurrentEvent()
        event.flag = num
        self.modify()

    def OnSelectItemType(self, checked):
        if checked:
            obj = self.sender()
            if obj == self.eventPropItemItemRadio or obj == self.eventPropItemList:
                self.changeItemType(self.eventPropItemList.currentIndex())
            elif obj == self.eventPropItemGoldRadio:
                self.changeItemType(self.eventPropItemGoldCtrl.value()//10 + 127)
            elif obj == self.eventPropItemNoneRadio:
                self.changeItemType(127)

    def changeItemType(self, num):
        event = self.getCurrentEvent()
        event.itemIdx = num
        self.updateItemProps()
        self.mapViewer.refreshMapView()
        self.modify()

    def OnToggleItemChestCheck(self, state):
        self.curEvent.isChest = state
        self.modify()

    # --- Animations ---
    def OnChangeAnim(self, row):
        self.changeAnim(row)

    def OnClickAnimTSPanel(self, obj):
        if self.curAnimIdx is not None:
            x = obj.mouseX // (obj.scale * 8)
            y = obj.mouseY // (obj.scale * 8)
            sel = y*16 + x
            if obj.lastButton == Qt.LeftButton:
                if not obj.shift:
                    self.changeAnimStart(sel)
                else:
                    self.changeAnimEnd(sel+1)
                self.modify()

    def OnSelectAnimTS(self, idx):
        self.map.animTSIdx = idx
        self.updateAnimTileset()
        self.refreshPixels()
        self.modify()

    def OnChangeAnimStart(self, val): self.changeAnimStart(val)
    def OnChangeAnimEnd(self, val): self.changeAnimEnd(val)
    def OnChangeAnimDest(self, val): self.changeAnimDest(val)
    def OnChangeAnimDelay(self, val): self.changeAnimDelay(val)

    def changeAnim(self, num):
        if num < len(self.map.anims):
            self.curAnimIdx = num
        else:
            self.curAnimIdx = None
        self.updateAnimProps()

    def changeAnimStart(self, val):
        self.animStart.setValue(val)
        self.map.anims[self.curAnimIdx].start = val
        self.modify()

    def changeAnimEnd(self, val):
        self.animEnd.setValue(val)
        self.map.anims[self.curAnimIdx].end = val
        self.modify()

    def changeAnimDest(self, val):
        self.animDest.setValue(val)
        self.map.anims[self.curAnimIdx].dest = val
        self.modify()

    def changeAnimDelay(self, val):
        self.animDelay.setValue(val)
        self.map.anims[self.curAnimIdx].delay = val
        self.modify()

    def updateAnimProps(self):
        self.animNameCtrl.setText("")
        self.animTSList.setCurrentIndex(0)
        self.animStart.setValue(0); self.animEnd.setValue(0); self.animDest.setValue(0); self.animDelay.setValue(0)
        hasAnim = self.curAnimIdx is not None
        self.animNameCtrl.setEnabled(hasAnim)
        self.animTSList.setEnabled(hasAnim)
        self.animStart.setEnabled(hasAnim); self.animEnd.setEnabled(hasAnim)
        self.animDest.setEnabled(hasAnim); self.animDelay.setEnabled(hasAnim)
        self.animTSPanel.setEnabled(hasAnim)
        if hasAnim:
            anim = self.map.anims[self.curAnimIdx]
            self.animList.setCurrentRow(self.curAnimIdx)
            self.animNameCtrl.setText(anim.name)
            self.animTSList.setCurrentIndex(self.map.animTSIdx)
            self.animStart.setValue(anim.start); self.animEnd.setValue(anim.end)
            self.animDest.setValue(anim.dest); self.animDelay.setValue(anim.delay)

    def updateAnimTSList(self):
        current = self.animTSList.currentText()
        self.animTSList.clear()
        self.animTSList.addItems([ts.name for ts in self.rom.data["tilesets"]])
        idx = self.animTSList.findText(current)
        if idx >= 0:
            self.animTSList.setCurrentIndex(idx)

    def updateAnimTileset(self):
        tsSelect = self.animTSList.currentIndex()
        self.animTileset = self.rom.data["tilesets"][tsSelect]
        self.curAnimTSIdx = tsSelect

    def getCurrentEventList(self):
        if self.curEventType == 0:
            return self.map.warps
        elif self.curEventType == 1:
            return self.map.copies
        elif self.curEventType == 2:
            return self.map.items
        return None

    def getCurrentEvent(self):
        lst = self.getCurrentEventList()
        if lst:
            return lst[self.curEventIdx]
        return None

    def OnChangeEventName(self, text):
        event = self.getCurrentEvent()
        if event:
            event.setIndexedName(text)
            item = self.eventList.currentItem()
            if item:
                item.setText(f"{self.curEventIdx}: {text}")

    def drawMapData(self, obj, painter):
        spec = getattr(obj, 'special', None)
        if not (self.curViewMode or self.viewAll or spec):
            return
        sp = SpritePanel
        painter.setBrush(sp.transBrush)
        if spec is None:
            return
        mask = spec & 0x3c00
        obsMask = spec & 0xc000
        if obsMask == 0xc000:
            painter.setPen(sp.obsPen)
            painter.drawLine(4, 4, 20, 20)
            painter.drawLine(20, 4, 4, 20)
        elif obsMask == 0x8000:
            painter.setPen(sp.stairsPen)
            painter.drawLine(20, 4, 4, 20)
        elif obsMask == 0x4000:
            painter.setPen(sp.stairsPen)
            painter.drawLine(4, 4, 20, 20)
        if mask == 0x1000:
            painter.setPen(sp.zonePen)
            painter.drawRect(4, 4, 16, 16)
        elif mask == 0x1400:
            painter.setPen(sp.eventPen)
            painter.drawRect(4, 4, 16, 16)
        elif mask == 0x1800:
            painter.setPen(sp.chestPen)
            painter.drawEllipse(4, 4, 16, 16)
        elif mask == 0x1c00:
            painter.setPen(sp.floorPen)
            painter.drawEllipse(4, 4, 16, 16)
        elif mask == 0x2c00:
            painter.setPen(sp.vasePen)
            painter.drawEllipse(4, 4, 16, 16)
        elif mask == 0x3000:
            painter.setPen(sp.barrelPen)
            painter.drawEllipse(4, 4, 16, 16)
        elif mask == 0x2800:
            painter.setPen(sp.tablePen)
            painter.drawLine(4, 12, 20, 12)
            painter.drawLine(12, 4, 12, 20)
        elif mask == 0x0800:
            painter.setPen(sp.roofPen1)
            painter.drawEllipse(4, 4, 16, 16)
        elif mask == 0x0c00:
            painter.setPen(sp.roofPen2)
            painter.drawEllipse(4, 4, 16, 16)
        elif mask == 0x0400:
            painter.setPen(sp.roofPen3)
            painter.drawEllipse(4, 4, 16, 16)
        if spec & 0xfc00 and obsMask == 0 and mask == 0:
            painter.setPen(sp.otherPen)
            painter.drawEllipse(4, 4, 16, 16)

    def getCurrentEventCoords(self):
        if self.mapViewer.viewerContext == consts.VC_EVENT_WARP:
            obj = self.getCurrentEvent()
            x = obj.x if not obj.sameX else 0
            y = obj.y if not obj.sameY else 0
            w = 1 if not obj.sameX else self.map.width
            h = 1 if not obj.sameY else self.map.height
            return x, y, w, h
        elif self.mapViewer.viewerContext == consts.VC_AREA:
            obj = self.curArea
            return obj.l1x1, obj.l1y1, obj.l1x2 - obj.l1x1, obj.l1y2 - obj.l1y1
        else:
            obj = self.getCurrentEvent()
            return obj.x, obj.y, 1, 1

    def getCurrentData(self):
        return self.map

    changeSelection = changeMap

    vcsBlock = [consts.VC_BLOCKS, consts.VC_FLAGS]
    vcsEvent = [consts.VC_EVENT_WARP, consts.VC_EVENT_COPY, consts.VC_EVENT_ITEM]

    curAreaIdx = property(lambda self: self.areaList.currentIndex())
    curArea = property(lambda self: self.map.areas[self.curAreaIdx])
    curEvent = property(lambda self: self.getCurrentEvent())