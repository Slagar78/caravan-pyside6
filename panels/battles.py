import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QRadioButton, QCheckBox,
    QScrollArea, QTabWidget, QTableWidget, QTableWidgetItem,
    QGroupBox, QSizePolicy, QSlider, QFrame
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QPixmap, QColor, QBrush, QIcon
import rompanel
import data
import window, consts

h2i = lambda i: int(i, 16)

icons = []
btn_icons = []
iconNames = ["lowsky", "plains", "road", "grass", "forest", "hill", "desert", "sky", "water", "blocked"]
for n in iconNames:
    pixmap = QPixmap("terrain_%s.ico" % n)
    icons.append(pixmap)
    btn_icons.append(QIcon(pixmap))

class BattlePanel(rompanel.ROMPanel):
    canMaximize = True
    frameTitle = "Battle Editor"

    def sizeHint(self):
        return QSize(1280, 800)

    def init(self):
        self.palette = self.rom.getDataByName("palettes", "Sprite & UI Palette")
        self.frame = 0
        self.terrainIcons = icons

        self.curBattleIdx = 0
        self.curUnitContext = 0
        self.curUnitIdx = 0
        self.curOrderSet = 0
        self.curRegionIdx = 0
        self.curPointIdx = 0

        # Тёмная тема
        self.setStyleSheet("""
            QGroupBox { font-weight: bold; border: 1px solid #555; border-radius: 2px; margin-top: 0.5em; padding-top: 0.3em; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }
            QPushButton { background-color: #4A4A4D; color: #E0E0E0; border: none; padding: 2px 6px; border-radius: 2px; }
            QPushButton:hover { background-color: #5A5A5D; }
            QPushButton:pressed { background-color: #3A3A3D; }
            QRadioButton, QCheckBox { color: #E0E0E0; }
            QComboBox, QSpinBox { background-color: #4A4A4D; color: #E0E0E0; border: 1px solid #555; padding: 1px 3px; }
            QTabWidget::pane { border: 1px solid #555; background-color: #3C3C41; }
            QTabBar::tab { background-color: #333337; color: #E0E0E0; padding: 4px 8px; border: 1px solid #555; border-bottom: none; }
            QTabBar::tab:selected { background-color: #4A4A4D; }
            QScrollBar:horizontal, QScrollBar:vertical { background-color: #2D2D30; width: 8px; }
            QScrollBar::handle:horizontal, QScrollBar::handle:vertical { background-color: #555; min-height: 20px; }
            QScrollBar::handle:horizontal:hover, QScrollBar::handle:vertical:hover { background-color: #777; }
        """)

        # Левая панель – только Entities
        leftPanel = QWidget()
        leftLayout = QVBoxLayout(leftPanel)
        leftLayout.setContentsMargins(1, 1, 1, 1)
        leftLayout.setSpacing(1)

        entitiesGroup = QGroupBox("Entities")
        entitiesLayout = QVBoxLayout(entitiesGroup)
        entitiesLayout.setContentsMargins(1, 1, 1, 1)
        entitiesLayout.setSpacing(0)

        self.scrollWnd = QScrollArea()
        self.scrollWnd.setWidgetResizable(True)
        self.scrollWnd.setMinimumWidth(160)
        self.scrollWnd.setMinimumHeight(60)
        self.scrollWnd.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scrollWidget = QWidget()
        scrollSizer = QVBoxLayout(scrollWidget)
        scrollSizer.setContentsMargins(0, 0, 0, 0)
        scrollSizer.setSpacing(0)

        lblMonsters = QLabel("Monsters")
        lblForce = QLabel("Force")
        lblNPCs = QLabel("NPCs")
        lblAdd = QLabel("Add:")

        self.monsterSizer = QGridLayout(); self.monsterSizer.setSpacing(0)
        self.forceSizer    = QGridLayout(); self.forceSizer.setSpacing(0)
        self.npcSizer      = QGridLayout(); self.npcSizer.setSpacing(0)

        self.monsterPanels = []
        self.forcePanels = []
        self.npcPanels = []

        self.allGroupSizers = [self.monsterSizer, self.forceSizer, self.npcSizer]
        self.allGroupPanels = [self.monsterPanels, self.forcePanels, self.npcPanels]

        for con in range(len(self.allGroupPanels)):
            curPanels = self.allGroupPanels[con]
            curSizer = self.allGroupSizers[con]
            rows, cols = 8, 4
            for p in range(rows * cols):
                ap = rompanel.SpritePanel(scrollWidget, None, 24, 24, self.palette,
                                          scale=1, bg=None, func=self.OnClickPanel)
                ap.refreshSprite([])
                ap.context = con
                ap.num = p
                ap.used = False
                curPanels.append(ap)
                curSizer.addWidget(ap, p // cols, p % cols)

        self.animDelays = [250, 150, 50, 50, 50, 50]
        self.animFrame = 0
        self.curAnim = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.OnAnimNext)
        self.changeAnim(0)

        scrollSizer.addWidget(lblMonsters)
        scrollSizer.addLayout(self.monsterSizer)
        scrollSizer.addWidget(lblForce)
        scrollSizer.addLayout(self.forceSizer)
        scrollSizer.addWidget(lblNPCs)
        scrollSizer.addLayout(self.npcSizer)
        scrollSizer.addStretch()

        self.scrollWnd.setWidget(scrollWidget)

        scrollButtonSizer = QHBoxLayout()
        scrollButtonSizer.setSpacing(2)
        self.addMonsterButton = QPushButton("Mstr")
        self.addForceButton = QPushButton("Frc")
        self.addNPCButton = QPushButton("NPC")
        self.addMonsterButton.setFixedSize(35, 16)
        self.addForceButton.setFixedSize(30, 16)
        self.addNPCButton.setFixedSize(30, 16)
        scrollButtonSizer.addWidget(lblAdd)
        scrollButtonSizer.addWidget(self.addMonsterButton)
        scrollButtonSizer.addWidget(self.addForceButton)
        scrollButtonSizer.addWidget(self.addNPCButton)

        entitiesLayout.addWidget(self.scrollWnd)
        entitiesLayout.addLayout(scrollButtonSizer)
        leftLayout.addWidget(entitiesGroup)

        # Центральная область – тулбар + карта
        centralPanel = QWidget()
        centralLayout = QVBoxLayout(centralPanel)
        centralLayout.setContentsMargins(0, 0, 0, 0)
        centralLayout.setSpacing(0)

        toolbar = QFrame()
        toolbar.setFixedHeight(28)
        toolbar.setStyleSheet("background-color: #3C3C41;")
        toolbarLayout = QHBoxLayout(toolbar)
        toolbarLayout.setContentsMargins(4, 2, 4, 2)
        toolbarLayout.setSpacing(4)

        self.smartPathsCheck = QCheckBox("Smart Paths")
        self.gridCheck = QCheckBox("Grid")
        self.gridCheck.setChecked(True)
        self.borderCheck = QCheckBox("Border")
        self.borderCheck.setChecked(True)
        toolbarLayout.addWidget(self.smartPathsCheck)
        toolbarLayout.addWidget(self.gridCheck)
        toolbarLayout.addWidget(self.borderCheck)
        toolbarLayout.addStretch()

        centralLayout.addWidget(toolbar)

        # Правая панель – инспектор
        rightPanel = QTabWidget()
        rightPanel.setFixedWidth(280)

        # Properties
        propTab = QWidget()
        propLayout = QVBoxLayout(propTab)
        propLayout.setContentsMargins(2, 2, 2, 2)
        propLayout.setSpacing(2)

        animRow = QHBoxLayout()
        animRow.setSpacing(2)
        self.modifyAnimPanel = rompanel.SpritePanel(self, None, 24, 24, self.palette, scale=1, bg=None)
        self.modifyFacingUpRadio = QRadioButton()
        self.modifyFacingLeftRadio = QRadioButton()
        self.modifyFacingRightRadio = QRadioButton()
        self.modifyFacingDownRadio = QRadioButton()
        self.modifyFacingRightRadio.setChecked(True)
        self.modifyDeleteButton = QPushButton("Del")
        self.modifyDeleteButton.setFixedSize(22, 16)

        facingGrid = QGridLayout()
        facingGrid.setSpacing(0)
        facingGrid.addWidget(self.modifyFacingUpRadio, 0, 1)
        facingGrid.addWidget(self.modifyFacingLeftRadio, 1, 0)
        facingGrid.addWidget(self.modifyFacingRightRadio, 1, 2)
        facingGrid.addWidget(self.modifyFacingDownRadio, 2, 1)

        animRow.addWidget(self.modifyAnimPanel)
        animRow.addLayout(facingGrid)
        animRow.addWidget(self.modifyDeleteButton)
        propLayout.addLayout(animRow)

        grid = QGridLayout()
        grid.setSpacing(2)

        self.modifyList = QSpinBox(); self.modifyList.setMaximum(175); self.modifyList.setFixedWidth(40)
        self.modifyItemList = QComboBox(); self.modifyItemList.setFixedWidth(50)
        self.modifyXCtrl = QSpinBox(); self.modifyXCtrl.setMaximum(47); self.modifyXCtrl.setFixedWidth(30)
        self.modifyYCtrl = QSpinBox(); self.modifyYCtrl.setMaximum(47); self.modifyYCtrl.setFixedWidth(30)

        grid.addWidget(QLabel("Unit"), 0, 0)
        grid.addWidget(self.modifyList, 0, 1)
        grid.addWidget(QLabel("Item"), 0, 2)
        grid.addWidget(self.modifyItemList, 0, 3)
        grid.addWidget(QLabel("X"), 0, 4)
        grid.addWidget(self.modifyXCtrl, 0, 5)
        grid.addWidget(QLabel("Y"), 0, 6)
        grid.addWidget(self.modifyYCtrl, 0, 7)

        self.modifyAICtrl = QSpinBox(); self.modifyAICtrl.setMaximum(15); self.modifyAICtrl.setFixedWidth(35)
        self.modifyMiscReinforceCheck = QCheckBox("Reinf")
        self.modifyMiscRespawnCheck = QCheckBox("Resp")
        self.modifyMisc1Check = QCheckBox("???")

        grid.addWidget(QLabel("AI"), 1, 0)
        grid.addWidget(self.modifyAICtrl, 1, 1)
        grid.addWidget(self.modifyMiscReinforceCheck, 1, 2, 1, 2)
        grid.addWidget(self.modifyMiscRespawnCheck, 1, 4)
        grid.addWidget(self.modifyMisc1Check, 1, 6)

        self.orderSet1Radio = QRadioButton("Set1"); self.orderSet1Radio.setChecked(True)
        self.orderSet2Radio = QRadioButton("Set2")
        self.targetCheck = QCheckBox("Reg")
        self.targetList = QComboBox(); self.targetList.setFixedWidth(60)

        grid.addWidget(self.orderSet1Radio, 2, 0, 1, 2)
        grid.addWidget(self.orderSet2Radio, 2, 2, 1, 2)
        grid.addWidget(self.targetCheck, 2, 4)
        grid.addWidget(self.targetList, 2, 6)

        self.gotoCheck = QCheckBox("Move")
        self.gotoForceRadio = QRadioButton("Frc"); self.gotoForceRadio.setChecked(True)
        self.gotoPointRadio = QRadioButton("Pnt")
        self.gotoAllyRadio = QRadioButton("Aly")
        self.gotoList = QComboBox(); self.gotoList.setFixedWidth(60)

        grid.addWidget(self.gotoCheck, 3, 0)
        grid.addWidget(self.gotoForceRadio, 3, 1)
        grid.addWidget(self.gotoPointRadio, 3, 2)
        grid.addWidget(self.gotoAllyRadio, 3, 3)
        grid.addWidget(self.gotoList, 3, 6)

        propLayout.addLayout(grid)
        propLayout.addStretch()
        rightPanel.addTab(propTab, "Properties")

        # View
        viewTab = QWidget()
        viewLayout = QVBoxLayout(viewTab)
        viewLayout.setContentsMargins(2, 2, 2, 2)
        viewLayout.setSpacing(2)

        self.mousePosLabel = QLabel("Mouse: (0,0)")
        self.curZoomLabel = QLabel("Zoom: 100%")
        self.curEditLabel = QLabel("Editing: Nothing")

        self.zoomSlider = QSlider(Qt.Horizontal)
        self.zoomSlider.setRange(0, 8)
        self.zoomSlider.setValue(4)

        self.dispBlocksCheck = QCheckBox("Blocks")
        self.dispBlocksCheck.setChecked(True)
        self.dispFlagsCheck = QCheckBox("Flags")
        self.dispFlagsCheck.setChecked(True)
        self.dispGridCheck = QCheckBox("Grid")
        self.dispGridCheck.setChecked(True)
        self.topCheck = QCheckBox("Always on top")
        self.dragCheck = QCheckBox("Alt drag mode")

        viewLayout.addWidget(self.mousePosLabel)
        viewLayout.addWidget(self.curZoomLabel)
        viewLayout.addWidget(self.curEditLabel)
        viewLayout.addWidget(QLabel("Zoom:"))
        viewLayout.addWidget(self.zoomSlider)
        viewLayout.addWidget(QLabel("Display:"))
        viewLayout.addWidget(self.dispBlocksCheck)
        viewLayout.addWidget(self.dispFlagsCheck)
        viewLayout.addWidget(self.dispGridCheck)
        viewLayout.addWidget(self.topCheck)
        viewLayout.addWidget(self.dragCheck)
        viewLayout.addStretch()
        rightPanel.addTab(viewTab, "View")

        # --- Battle Properties (создаём ДО mapViewer) ---
        self.battleNotebook = QTabWidget()
        self.battleNotebook.setFixedHeight(130)

        genWindow = QWidget(); genWndSizer = QVBoxLayout(genWindow); genWndSizer.setContentsMargins(1,1,1,1)
        mapWindow = QWidget(); mapWndSizer = QVBoxLayout(mapWindow); mapWndSizer.setContentsMargins(1,1,1,1)
        zoneWindow = QWidget(); zoneWndSizer = QVBoxLayout(zoneWindow); zoneWndSizer.setContentsMargins(1,1,1,1)
        terrainWindow = QWidget(); terrainWndSizer = QVBoxLayout(terrainWindow); terrainWndSizer.setContentsMargins(1,1,1,1)

        # General
        genRow1 = QHBoxLayout()
        self.winAllRadio = QRadioButton("All"); self.winAllRadio.setChecked(True)
        self.winBossRadio = QRadioButton("Boss")
        self.winCustomRadio = QRadioButton("Custom")
        genRow1.addWidget(QLabel("Win:"))
        genRow1.addWidget(self.winAllRadio)
        genRow1.addWidget(self.winBossRadio)
        genRow1.addWidget(self.winCustomRadio)
        genRow1.addStretch()
        genWndSizer.addLayout(genRow1)

        genRow2 = QHBoxLayout()
        self.defaultBattleGfxRadio = QRadioButton("Def"); self.defaultBattleGfxRadio.setChecked(True)
        self.overrideBattleGfxRadio = QRadioButton("Over")
        self.battleGfxList = QComboBox(); self.battleGfxList.setFixedWidth(60)
        genRow2.addWidget(QLabel("Gfx:"))
        genRow2.addWidget(self.defaultBattleGfxRadio)
        genRow2.addWidget(self.overrideBattleGfxRadio)
        genRow2.addWidget(self.battleGfxList)
        genRow2.addStretch()
        genWndSizer.addLayout(genRow2)

        genRow3 = QHBoxLayout()
        self.propRepeatableCheck = QCheckBox("Repeat")
        self.propMandatoryCheck = QCheckBox("Mand")
        self.propHalfEXPCheck = QCheckBox("HalfXP")
        genRow3.addWidget(self.propRepeatableCheck)
        genRow3.addWidget(self.propMandatoryCheck)
        genRow3.addWidget(self.propHalfEXPCheck)
        genRow3.addStretch()
        genWndSizer.addLayout(genRow3)

        genRow4 = QHBoxLayout()
        self.cutsceneBeforeList = QComboBox()
        self.cutsceneAfterList = QComboBox()
        genRow4.addWidget(QLabel("Cut:"))
        genRow4.addWidget(QLabel("Bef"))
        genRow4.addWidget(self.cutsceneBeforeList)
        genRow4.addWidget(QLabel("Aft"))
        genRow4.addWidget(self.cutsceneAfterList)
        genRow4.addStretch()
        genWndSizer.addLayout(genRow4)

        # Map
        mapRow1 = QHBoxLayout()
        self.mapList = QComboBox(); self.mapList.addItems([s.name for s in self.rom.data["maps"]])
        self.mapList.setCurrentIndex(self.curBattle.map_index)
        mapRow1.addWidget(QLabel("Map:"))
        mapRow1.addWidget(self.mapList)
        mapRow1.addStretch()
        mapWndSizer.addLayout(mapRow1)

        mapRow2 = QHBoxLayout()
        self.boundsXCtrl = QSpinBox(); self.boundsXCtrl.setMaximum(47); self.boundsXCtrl.setFixedWidth(35)
        self.boundsYCtrl = QSpinBox(); self.boundsYCtrl.setMaximum(47); self.boundsYCtrl.setFixedWidth(35)
        self.boundsX2Ctrl = QSpinBox(); self.boundsX2Ctrl.setMaximum(47); self.boundsX2Ctrl.setFixedWidth(35)
        self.boundsY2Ctrl = QSpinBox(); self.boundsY2Ctrl.setMaximum(47); self.boundsY2Ctrl.setFixedWidth(35)
        mapRow2.addWidget(QLabel("X1/Y1"))
        mapRow2.addWidget(self.boundsXCtrl)
        mapRow2.addWidget(self.boundsYCtrl)
        mapRow2.addWidget(QLabel("X2/Y2"))
        mapRow2.addWidget(self.boundsX2Ctrl)
        mapRow2.addWidget(self.boundsY2Ctrl)
        mapRow2.addStretch()
        mapWndSizer.addLayout(mapRow2)

        # AI Zones
        zoneRow1 = QHBoxLayout()
        self.regionList = QComboBox(); self.regionList.setFixedWidth(80)
        self.regionType1Radio = QRadioButton("T1"); self.regionType1Radio.setChecked(True)
        self.regionType2Radio = QRadioButton("T2")
        self.pointList = QComboBox(); self.pointList.setFixedWidth(60)
        zoneRow1.addWidget(QLabel("Reg"))
        zoneRow1.addWidget(self.regionList)
        zoneRow1.addWidget(self.regionType1Radio)
        zoneRow1.addWidget(self.regionType2Radio)
        zoneRow1.addWidget(QLabel("Pt"))
        zoneRow1.addWidget(self.pointList)
        zoneRow1.addStretch()
        zoneWndSizer.addLayout(zoneRow1)

        zoneGrid = QGridLayout()
        zoneGrid.setSpacing(1)
        self.regionXCtrl = QSpinBox(); self.regionXCtrl.setMaximum(47); self.regionXCtrl.setFixedWidth(35)
        self.regionYCtrl = QSpinBox(); self.regionYCtrl.setMaximum(47); self.regionYCtrl.setFixedWidth(35)
        self.regionX2Ctrl = QSpinBox(); self.regionX2Ctrl.setMaximum(47); self.regionX2Ctrl.setFixedWidth(35)
        self.regionY2Ctrl = QSpinBox(); self.regionY2Ctrl.setMaximum(47); self.regionY2Ctrl.setFixedWidth(35)
        self.regionX3Ctrl = QSpinBox(); self.regionX3Ctrl.setMaximum(47); self.regionX3Ctrl.setFixedWidth(35)
        self.regionY3Ctrl = QSpinBox(); self.regionY3Ctrl.setMaximum(47); self.regionY3Ctrl.setFixedWidth(35)
        self.regionX4Ctrl = QSpinBox(); self.regionX4Ctrl.setMaximum(47); self.regionX4Ctrl.setFixedWidth(35)
        self.regionY4Ctrl = QSpinBox(); self.regionY4Ctrl.setMaximum(47); self.regionY4Ctrl.setFixedWidth(35)
        self.pointXCtrl = QSpinBox(); self.pointXCtrl.setMaximum(47); self.pointXCtrl.setFixedWidth(35)
        self.pointYCtrl = QSpinBox(); self.pointYCtrl.setMaximum(47); self.pointYCtrl.setFixedWidth(35)
        zoneGrid.addWidget(QLabel("X1"),0,0); zoneGrid.addWidget(self.regionXCtrl,0,1)
        zoneGrid.addWidget(QLabel("Y1"),1,0); zoneGrid.addWidget(self.regionYCtrl,1,1)
        zoneGrid.addWidget(QLabel("X2"),2,0); zoneGrid.addWidget(self.regionX2Ctrl,2,1)
        zoneGrid.addWidget(QLabel("Y2"),3,0); zoneGrid.addWidget(self.regionY2Ctrl,3,1)
        zoneGrid.addWidget(QLabel("X3"),0,2); zoneGrid.addWidget(self.regionX3Ctrl,0,3)
        zoneGrid.addWidget(QLabel("Y3"),1,2); zoneGrid.addWidget(self.regionY3Ctrl,1,3)
        zoneGrid.addWidget(QLabel("X4"),2,2); zoneGrid.addWidget(self.regionX4Ctrl,2,3)
        zoneGrid.addWidget(QLabel("Y4"),3,2); zoneGrid.addWidget(self.regionY4Ctrl,3,3)
        zoneGrid.addWidget(QLabel("PtX"),4,0); zoneGrid.addWidget(self.pointXCtrl,4,1)
        zoneGrid.addWidget(QLabel("PtY"),4,2); zoneGrid.addWidget(self.pointYCtrl,4,3)
        zoneWndSizer.addLayout(zoneGrid)

        # Terrain
        terRow1 = QHBoxLayout()
        self.terrainIconBtns = []
        terraintypes = ["Low Sky", "Plains", "Road", "Grass", "Forest", "Hill", "Desert", "High Sky", "Water", "Inaccessible"]
        for i, icon in enumerate(btn_icons):
            btn = QPushButton()
            btn.setIcon(icon)
            btn.setFixedSize(20, 20)
            btn.setToolTip(terraintypes[i])
            btn.setProperty("context", i)
            btn.clicked.connect(self.OnSelectTerrainType)
            terRow1.addWidget(btn)
            self.terrainIconBtns.append(btn)
        terRow1.addStretch()
        terrainWndSizer.addLayout(terRow1)

        terRow2 = QHBoxLayout()
        self.curTerrainBmp = QLabel()
        self.curTerrainBmp.setPixmap(icons[0])
        self.curTerrainBmp.setFixedSize(20, 20)
        terRow2.addWidget(QLabel("Cur:"))
        terRow2.addWidget(self.curTerrainBmp)
        terRow2.addStretch()
        terrainWndSizer.addLayout(terRow2)

        diffColors = [QColor(255,255,255), QColor(192,255,192), QColor(128,255,128),
                      QColor(255,255,128), QColor(255,192,128), QColor(255,128,128),
                      QColor(240,112,112), QColor(224,96,96), QColor(208,80,80),
                      QColor(192,64,64), QColor(176,48,48), QColor(160,32,32),
                      QColor(128,16,16), QColor(96,0,0), QColor(64,0,0), QColor(64,64,64)]
        self.terrainInfoGrid = QTableWidget(13, 9)
        self.terrainInfoGrid.horizontalHeader().setVisible(False)
        self.terrainInfoGrid.verticalHeader().setVisible(False)
        self.terrainInfoGrid.setFixedSize(200, 240)
        movetypes = ["Free", "Foot", "Horse", "Fast", "Tires", "Fly", "Float", "Water",
                     "Foot2", "Horse2", "Fast2", "Foot3", "Foot4"]
        for i in range(13):
            self.terrainInfoGrid.setVerticalHeaderItem(i, QTableWidgetItem(movetypes[i]))
        for i in range(9):
            self.terrainInfoGrid.setHorizontalHeaderItem(i, QTableWidgetItem(str(i)))
        for x in range(9):
            for y in range(13):
                mti = self.rom.data["movetypes"][y][x]
                le, diff = int(mti[0], 16), int(mti[1], 16)
                col = diffColors[diff]
                cell = QTableWidgetItem(str(le*15))
                cell.setBackground(QBrush(col))
                cell.setTextAlignment(Qt.AlignCenter)
                self.terrainInfoGrid.setItem(y, x, cell)

        terrainWndSizer.addWidget(self.terrainInfoGrid)

        self.battleNotebook.addTab(genWindow, "General")
        self.battleNotebook.addTab(mapWindow, "Map")
        self.battleNotebook.addTab(zoneWindow, "AI")
        self.battleNotebook.addTab(terrainWindow, "Terrain")

        # Карта (создаём после battleNotebook)
        self.mapViewer = window.BattleMapViewer(self, None, self)
        self.mapViewer.init(None, None)
        self.mapViewer.mapViewPanel.drawFlags = False

        # === ИСПРАВЛЕНИЯ ДЛЯ ГОРИЗОНТАЛЬНОГО ПОЛЗУНКА ===
        if hasattr(self.mapViewer, 'scrollArea') and self.mapViewer.scrollArea:
            sa = self.mapViewer.scrollArea
            sa.setWidgetResizable(False)
            sa.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            sa.setMaximumWidth(999999)          # снимаем искусственное ограничение
            sa.setMaximumHeight(999999)
            sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            sa.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        if hasattr(self.mapViewer, 'mainPanel') and self.mapViewer.mainPanel:
            self.mapViewer.mainPanel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Добавляем карту в центральную панель с растяжением
        centralLayout.addWidget(self.mapViewer, 1)

        # Добавляем battleNotebook в правую панель
        battleTab = QWidget()
        battleTabLayout = QVBoxLayout(battleTab)
        battleTabLayout.setContentsMargins(1, 1, 1, 1)
        battleTabLayout.setSpacing(1)
        battleTabLayout.addWidget(self.battleNotebook)
        rightPanel.addTab(battleTab, "Battle")

        # Сборка главного лейаута
        mainLayout = QHBoxLayout()
        mainLayout.setContentsMargins(1, 1, 1, 1)
        mainLayout.setSpacing(1)
        mainLayout.addWidget(leftPanel)
        mainLayout.addWidget(centralPanel, 1)      # 1 = stretch
        mainLayout.addWidget(rightPanel)
        self.sizer.addLayout(mainLayout, 0, 0, 1, 1)

        # Связываем View и карту
        self.zoomSlider.valueChanged.connect(self.mapViewer.changeZoom)
        self.dispBlocksCheck.stateChanged.connect(
            lambda state: setattr(self.mapViewer.mapViewPanel, 'drawBlocks', state == Qt.Checked))
        self.dispFlagsCheck.stateChanged.connect(
            lambda state: setattr(self.mapViewer.mapViewPanel, 'drawFlags', state == Qt.Checked))
        self.dispGridCheck.stateChanged.connect(self.mapViewer.OnToggleGridCheck)
        self.topCheck.stateChanged.connect(self.mapViewer.OnToggleTopCheck)

        # Подключения сигналов
        self.battleNotebook.currentChanged.connect(self.OnChangePage)
        self.addMonsterButton.clicked.connect(self.OnAddMonsterButton)
        self.addForceButton.clicked.connect(self.OnAddForceButton)
        self.addNPCButton.clicked.connect(self.OnAddNPCButton)
        self.modifyList.valueChanged.connect(self.OnChangeUnitIdx)
        self.modifyXCtrl.valueChanged.connect(self.OnChangeUnitX)
        self.modifyYCtrl.valueChanged.connect(self.OnChangeUnitY)
        self.modifyAICtrl.valueChanged.connect(self.OnChangeUnitAI)
        self.modifyDeleteButton.clicked.connect(self.OnDeleteUnitButton)
        self.mapList.currentIndexChanged.connect(self.OnSelectBattleMap)
        self.winAllRadio.toggled.connect(self.OnSelectWinAll)
        self.winBossRadio.toggled.connect(self.OnSelectWinBoss)
        self.boundsXCtrl.valueChanged.connect(self.OnChangeBoundsX)
        self.boundsYCtrl.valueChanged.connect(self.OnChangeBoundsY)
        self.boundsX2Ctrl.valueChanged.connect(self.OnChangeBoundsX2)
        self.boundsY2Ctrl.valueChanged.connect(self.OnChangeBoundsY2)
        self.regionList.currentIndexChanged.connect(self.OnSelectRegion)
        self.pointList.currentIndexChanged.connect(self.OnSelectPoint)
        self.regionXCtrl.valueChanged.connect(self.OnChangeRegionX)
        self.regionYCtrl.valueChanged.connect(self.OnChangeRegionY)
        self.regionX2Ctrl.valueChanged.connect(self.OnChangeRegionX2)
        self.regionY2Ctrl.valueChanged.connect(self.OnChangeRegionY2)
        self.regionX3Ctrl.valueChanged.connect(self.OnChangeRegionX3)
        self.regionY3Ctrl.valueChanged.connect(self.OnChangeRegionY3)
        self.regionX4Ctrl.valueChanged.connect(self.OnChangeRegionX4)
        self.regionY4Ctrl.valueChanged.connect(self.OnChangeRegionY4)
        self.pointXCtrl.valueChanged.connect(self.OnChangePointX)
        self.pointYCtrl.valueChanged.connect(self.OnChangePointY)
        self.modifyFacingUpRadio.toggled.connect(self.OnSelectFacingUp)
        self.modifyFacingLeftRadio.toggled.connect(self.OnSelectFacingLeft)
        self.modifyFacingRightRadio.toggled.connect(self.OnSelectFacingRight)
        self.modifyFacingDownRadio.toggled.connect(self.OnSelectFacingDown)
        self.orderSet1Radio.toggled.connect(self.OnSelectOrderSet)
        self.orderSet2Radio.toggled.connect(self.OnSelectOrderSet)
        self.targetCheck.toggled.connect(self.OnToggleTriggerRegion)
        self.gotoCheck.toggled.connect(self.OnToggleGotoType)
        self.targetList.currentIndexChanged.connect(self.OnSelectTargetEntry)
        self.gotoList.currentIndexChanged.connect(self.OnSelectGotoEntry)
        self.regionType1Radio.toggled.connect(self.OnSelectRegionType1)
        self.regionType2Radio.toggled.connect(self.OnSelectRegionType2)
        self.defaultBattleGfxRadio.toggled.connect(self.OnSelectGraphicsDefault)
        self.overrideBattleGfxRadio.toggled.connect(self.OnSelectGraphicsOverride)
        self.gotoForceRadio.toggled.connect(self.OnSelectGotoForce)
        self.gotoPointRadio.toggled.connect(self.OnSelectGotoPoint)
        self.gotoAllyRadio.toggled.connect(self.OnSelectGotoAlly)
        self.modifyMiscReinforceCheck.toggled.connect(self.OnToggleReinforce)
        self.modifyMiscRespawnCheck.toggled.connect(self.OnToggleRespawn)
        self.modifyMisc1Check.toggled.connect(self.OnToggleMisc1)

        self.printed = False

    # -------- Остальные методы класса (без изменений) --------
    def OnShow(self, event=None):
        pass

    def OnSelectBattle(self, idx):
        self.changeBattle(idx)

    def OnAnimNext(self):
        self.animFrame ^= 1
        self.refreshAnimPanels()
        self.mapViewer.refreshMapView()

    def OnClickPanel(self, obj):
        if hasattr(obj, 'context') and hasattr(obj, 'num'):
            self.changeUnit(obj.context, obj.num)

    def OnAddMonsterButton(self):
        u = data.BattleUnit()
        u.init(64, 0, 0)
        self.curBattle.enemies.append(u)
        self.updateAnimPanels()
        self.updateModifyEntity()
        self.modify()

    def OnAddForceButton(self):
        u = data.BattleUnit()
        u.init(len(self.curBattle.force), 0, 0)
        self.curBattle.force.append(u)
        self.updateAnimPanels()
        self.updateModifyEntity()
        self.modify()

    def OnAddNPCButton(self):
        u = data.BattleNPC()
        u.init(0, 0, 0)
        self.curBattle.npcs.append(u)
        self.updateAnimPanels()
        self.updateModifyEntity()
        self.modify()

    def OnDeleteUnitButton(self):
        del self.allGroupData[self.curUnitContext][self.curUnitIdx]
        self.curUnitIdx = min(self.curUnitIdx, len(self.allGroupData[self.curUnitContext])-1)
        if self.curUnitIdx == -1:
            self.curUnitContext = 0
            self.curUnitIdx = 0
        self.changeUnit(self.curUnitContext, self.curUnitIdx)
        self.updateAnimPanels()
        self.modify()

    def OnSelectFacingUp(self, checked):
        if checked:
            self.curUnit.facing = 1
            self.updateAnimPanels()
            self.modify()

    def OnSelectFacingLeft(self, checked):
        if checked:
            self.curUnit.facing = 2
            self.updateAnimPanels()
            self.modify()

    def OnSelectFacingRight(self, checked):
        if checked:
            self.curUnit.facing = 0
            self.updateAnimPanels()
            self.modify()

    def OnSelectFacingDown(self, checked):
        if checked:
            self.curUnit.facing = 3
            self.updateAnimPanels()
            self.modify()

    def OnChangeUnitIdx(self, val):
        self.changeUnitIdx(val)

    def changeUnitIdx(self, num):
        if self.curUnitContext == 2:
            self.curUnit.idx = num
        else:
            self.curUnit.idx = num + 64
        self.modifyList.setValue(num)
        self.updateAnimPanels()
        self.modify()

    def OnChangeUnitX(self, val):
        self.curUnit.x = val
        self.modify()

    def OnChangeUnitY(self, val):
        self.curUnit.y = val
        self.modify()

    def OnChangeUnitAI(self, val):
        self.curUnit.ai[0] = val
        self.modify()

    def OnSelectOrderSet(self, checked):
        if self.orderSet1Radio.isChecked():
            self.curOrderSet = 0
        else:
            self.curOrderSet = 1
        self.updateModifyEntity()

    def OnToggleTriggerRegion(self, checked):
        self.curUnit.ai[self.curOrderSet + 1][1] = 15 - (checked * 15)
        self.updateTargetList()
        self.updateModifyEntity()
        self.modify()

    def OnToggleGotoType(self, checked):
        self.curUnit.ai[self.curOrderSet + 1][0] = 255 - (checked * 255)
        self.updateGotoList()
        self.updateModifyEntity()
        self.modify()

    def OnSelectTargetEntry(self, idx):
        if idx >= 0:
            self.curUnit.ai[self.curOrderSet + 1][1] = idx
            self.modify()

    def OnSelectGotoForce(self, checked):
        if checked:
            self.curUnit.ai[self.curOrderSet + 1][0] = 0
            self.updateGotoList()
            self.modify()

    def OnSelectGotoPoint(self, checked):
        if checked:
            self.curUnit.ai[self.curOrderSet + 1][0] = 64
            self.updateGotoList()
            self.modify()

    def OnSelectGotoAlly(self, checked):
        if checked:
            self.curUnit.ai[self.curOrderSet + 1][0] = 128
            self.updateGotoList()
            self.modify()

    def OnSelectGotoEntry(self, idx):
        if idx < 0: return
        type_ = int(self.curUnit.ai[self.curOrderSet + 1][0] / 64)
        if type_ == 2 and idx >= self.curUnitIdx:
            idx += 1
        self.curUnit.ai[self.curOrderSet + 1][0] = type_ * 64 + idx
        self.modify()

    def OnToggleReinforce(self, checked):
        self.curUnit.reinforce = checked
        self.modify()

    def OnToggleRespawn(self, checked):
        self.curUnit.respawn = checked
        self.modify()

    def OnToggleMisc1(self, checked):
        self.curUnit.misc1 = checked
        self.modify()

    def OnSelectWinAll(self, checked):
        if checked:
            self.curBattle.boss = False
            self.modify()

    def OnSelectWinBoss(self, checked):
        if checked:
            self.curBattle.boss = True
            self.modify()

    def OnSelectBattleMap(self, idx):
        self.curBattle.map_index = idx
        self.modify()

    def OnChangeBoundsX(self, val):
        self.curBattle.map_x1 = val
        self.modify()

    def OnChangeBoundsY(self, val):
        self.curBattle.map_y1 = val
        self.modify()

    def OnChangeBoundsX2(self, val):
        self.curBattle.map_x2 = val
        self.modify()

    def OnChangeBoundsY2(self, val):
        self.curBattle.map_y2 = val
        self.modify()

    def OnSelectRegion(self, idx):
        self.changeRegion(idx)

    def OnSelectPoint(self, idx):
        self.changePoint(idx)

    def changeRegion(self, num):
        region = self.curBattle.regions[num]
        self.curRegionIdx = num
        self.regionList.setCurrentIndex(num)
        if region.type == 4:
            self.regionType1Radio.setChecked(True)
        else:
            self.regionType2Radio.setChecked(True)
        self.regionXCtrl.setValue(region.p1[0])
        self.regionYCtrl.setValue(region.p1[1])
        self.regionX2Ctrl.setValue(region.p2[0])
        self.regionY2Ctrl.setValue(region.p2[1])
        self.regionX3Ctrl.setValue(region.p3[0])
        self.regionY3Ctrl.setValue(region.p3[1])
        self.regionX4Ctrl.setValue(region.p4[0])
        self.regionY4Ctrl.setValue(region.p4[1])
        self.mapViewer.refreshMapView()

    def changePoint(self, num):
        point = self.curBattle.points[num]
        self.curPointIdx = num
        self.pointList.setCurrentIndex(num)
        self.pointXCtrl.setValue(point[0])
        self.pointYCtrl.setValue(point[1])
        self.mapViewer.refreshMapView()

    def OnSelectRegionType1(self, checked):
        if checked:
            self.curBattle.regions[self.curRegionIdx].type = 4
            self.modify()

    def OnSelectRegionType2(self, checked):
        if checked:
            self.curBattle.regions[self.curRegionIdx].type = 3
            self.modify()

    def OnChangeRegionX(self, val): self.changeRegionX(val)
    def changeRegionX(self, num):
        self.curBattle.regions[self.curRegionIdx].p1[0] = num
        self.regionXCtrl.setValue(num)
        self.modify()
        self.mapViewer.refreshMapView()

    def OnChangeRegionY(self, val): self.changeRegionY(val)
    def changeRegionY(self, num):
        self.curBattle.regions[self.curRegionIdx].p1[1] = num
        self.regionYCtrl.setValue(num)
        self.modify()
        self.mapViewer.refreshMapView()

    def OnChangeRegionX2(self, val): self.changeRegionX2(val)
    def changeRegionX2(self, num):
        self.curBattle.regions[self.curRegionIdx].p2[0] = num
        self.regionX2Ctrl.setValue(num)
        self.modify()
        self.mapViewer.refreshMapView()

    def OnChangeRegionY2(self, val): self.changeRegionY2(val)
    def changeRegionY2(self, num):
        self.curBattle.regions[self.curRegionIdx].p2[1] = num
        self.regionY2Ctrl.setValue(num)
        self.modify()
        self.mapViewer.refreshMapView()

    def OnChangeRegionX3(self, val): self.changeRegionX3(val)
    def changeRegionX3(self, num):
        self.curBattle.regions[self.curRegionIdx].p3[0] = num
        self.regionX3Ctrl.setValue(num)
        self.modify()
        self.mapViewer.refreshMapView()

    def OnChangeRegionY3(self, val): self.changeRegionY3(val)
    def changeRegionY3(self, num):
        self.curBattle.regions[self.curRegionIdx].p3[1] = num
        self.regionY3Ctrl.setValue(num)
        self.modify()
        self.mapViewer.refreshMapView()

    def OnChangeRegionX4(self, val): self.changeRegionX4(val)
    def changeRegionX4(self, num):
        self.curBattle.regions[self.curRegionIdx].p4[0] = num
        self.regionX4Ctrl.setValue(num)
        self.modify()
        self.mapViewer.refreshMapView()

    def OnChangeRegionY4(self, val): self.changeRegionY4(val)
    def changeRegionY4(self, num):
        self.curBattle.regions[self.curRegionIdx].p4[1] = num
        self.regionY4Ctrl.setValue(num)
        self.modify()
        self.mapViewer.refreshMapView()

    def OnChangePointX(self, val): self.changePointX(val)
    def changePointX(self, num):
        self.curBattle.points[self.curPointIdx][0] = num
        self.pointYCtrl.setValue(num)
        self.modify()
        self.mapViewer.refreshMapView()

    def OnChangePointY(self, val): self.changePointY(val)
    def changePointY(self, num):
        self.curBattle.points[self.curPointIdx][1] = num
        self.pointYCtrl.setValue(num)
        self.modify()
        self.mapViewer.refreshMapView()

    def OnSelectTerrainType(self):
        btn = self.sender()
        context = btn.property("context")
        self.changeTerrainType(context)

    def changeTerrainType(self, num):
        self.curTerrainBmp.setPixmap(icons[num])
        if num == len(icons) - 1:
            self.curTerrainType = 255
        else:
            self.curTerrainType = num

    def OnSelectGraphicsDefault(self, checked):
        if checked:
            self.updateGeneralWindow()

    def OnSelectGraphicsOverride(self, checked):
        if checked:
            self.updateGeneralWindow()

    def changeBattle(self, num):
        self.curBattleIdx = num
        if not self.rom.data["battles"][num].loaded:
            self.rom.getBattles(num, num)
        battle = self.curBattle
        self.updateModifiedIndicator(battle.modified)
        self.setAnimPanelSelected(False)
        self.updateAnimPanels()
        self.changeUnit(0, 0)
        self.curRegionIdx = 0
        self.curPointIdx = 0
        self.regionList.clear()
        self.regionList.addItems(["Region %i" % i for i in range(len(battle.regions))])
        self.regionList.setCurrentIndex(0)
        self.pointList.clear()
        self.pointList.addItems(["Point %i" % i for i in range(len(battle.points))])
        self.pointList.setCurrentIndex(0)
        self.updateGeneralWindow()
        self.updateMapWindow()
        self.updateZoneWindow()
        map_num = battle.map_index
        if not self.rom.data["maps"][map_num].loaded:
            self.rom.getMaps(map_num, map_num)
        battleMap = self.rom.data["maps"][map_num]
        self.mapViewer.changeMap(battleMap, None)
        self.mapViewer.setViewPos(battle.map_x1 * 24, battle.map_y1 * 24)

    def changeUnit(self, con, idx):
        self.setAnimPanelSelected(False)
        self.curUnitContext = con
        self.curUnitIdx = idx
        self.curOrderSet = 0
        unit = self.curUnit
        battle = self.curBattle
        self.setAnimPanelSelected(True)
        self.refreshAnimPanels()
        self.orderSet1Radio.setChecked(True)
        if self.curUnitContext != 2:
            self.updateTargetList()
            self.updateGotoList()
        self.updateModifyEntity()
        self.mapViewer.centerViewPos((battle.map_x1 + unit.x) * 24 + 12, (battle.map_y1 + unit.y) * 24 + 12)
        self.mapViewer.refreshMapView()

    def updateTargetList(self):
        battle = self.curBattle
        self.targetList.clear()
        self.targetList.addItems(["Region %i" % i for i in range(len(battle.regions))])
        self.targetList.setCurrentIndex(0)

    def updateGotoList(self):
        battle = self.curBattle
        self.gotoList.clear()
        type_ = self.curUnit.ai[self.curOrderSet + 1][0] // 64
        text = ["Force Member %i", "Point %i", "Monster %i", ""][type_]
        num = [len(battle.force), len(battle.points), len(battle.enemies), 0][type_]
        items = [text % i for i in range(num)]
        if type_ == 2:
            items.pop(self.curUnitIdx)
        self.gotoList.addItems(items)
        self.gotoList.setCurrentIndex(0)

    def setAnimPanelSelected(self, flag):
        self.curPanel.bg = [None, 17][flag]

    def changeAnim(self, num):
        self.curAnim = num
        self.timer.start(self.animDelays[num])

    def updateAnimPanels(self):
        sprites = self.rom.data["sprites"]
        for con in range(len(self.allGroupData)):
            curPanels = self.allGroupPanels[con]
            curData = self.allGroupData[con]
            for p, ap in enumerate(curPanels):
                if p >= len(curData):
                    ap.used = False
                    ap.hide()
                else:
                    ap.used = True
                    ap.show()
                if ap.used:
                    idx = curData[p].idx * 3
                    if not sprites[idx].loaded:
                        self.rom.getSprites(idx, idx + 2)
                    if con == 2:
                        ap.sprite = sprites[idx + [1, 0, 1, 2][curData[p].facing]]
                        ap.flip = curData[p].facing == 0
                    else:
                        ap.sprite = sprites[idx + 2]
                        ap.flip = False
                    ap.context = con
                    ap.num = p
                else:
                    ap.sprite = None
                    ap.refreshSprite([])
        scrollWidget = self.scrollWnd.widget()
        scrollWidget.resize(scrollWidget.sizeHint())

    def refreshAnimPanels(self):
        for con in range(len(self.allGroupPanels)):
            for i, ap in enumerate(self.allGroupPanels[con]):
                if ap.sprite:
                    if self.animFrame == 0:
                        ap.refreshSprite(ap.sprite.pixels)
                    else:
                        ap.refreshSprite(ap.sprite.pixels2)
                else:
                    ap.refreshSprite([])
                ap.update()
        if self.curPanel.sprite:
            sprite = self.curPanel.sprite
            self.modifyAnimPanel.flip = self.curPanel.flip
            if self.animFrame == 0:
                self.modifyAnimPanel.refreshSprite(sprite.pixels)
            else:
                self.modifyAnimPanel.refreshSprite(sprite.pixels2)
            self.modifyAnimPanel.update()

    def updateModifyEntity(self):
        unit = self.curUnit
        battle = self.curBattle
        hasAI = (self.curUnitContext == 0)
        isNPC = (self.curUnitContext == 2)
        if isNPC:
            self.modifyList.setRange(0, 239)
            self.modifyList.setValue(unit.idx)
            self.modifyFacingRightRadio.setChecked(unit.facing == 0)
            self.modifyFacingUpRadio.setChecked(unit.facing == 1)
            self.modifyFacingLeftRadio.setChecked(unit.facing == 2)
            self.modifyFacingDownRadio.setChecked(unit.facing == 3)
        else:
            self.modifyList.setValue(unit.idx - 64)
            self.modifyList.setRange(0, 173)
        self.modifyFacingUpRadio.setEnabled(isNPC)
        self.modifyFacingLeftRadio.setEnabled(isNPC)
        self.modifyFacingRightRadio.setEnabled(isNPC)
        self.modifyFacingDownRadio.setEnabled(isNPC)
        self.modifyXCtrl.setValue(unit.x)
        self.modifyYCtrl.setValue(unit.y)
        if isNPC or len(self.allGroupData[self.curUnitContext]) > 1:
            self.modifyDeleteButton.setEnabled(True)
        else:
            self.modifyDeleteButton.setEnabled(False)
        if hasAI:
            self.modifyAICtrl.setValue(unit.ai[0])
        self.orderSet1Radio.setChecked(self.curOrderSet == 0)
        self.orderSet2Radio.setChecked(self.curOrderSet == 1)
        if hasAI:
            order = unit.ai[self.curOrderSet + 1]
            orderType = order[0] // 64
            orderRegion = order[1]
        else:
            orderType = 3
            orderRegion = 15
        hasRegion = (orderRegion != 15 and len(battle.regions))
        hasMoveOrder = (orderType != 3)
        self.targetCheck.setChecked(hasRegion)
        self.targetList.setEnabled(hasRegion)
        if orderType == 0:
            self.gotoForceRadio.setChecked(True)
        elif orderType == 1:
            self.gotoPointRadio.setChecked(True)
        elif orderType == 2:
            self.gotoAllyRadio.setChecked(True)
        self.gotoCheck.setChecked(hasMoveOrder)
        self.gotoForceRadio.setEnabled(hasMoveOrder)
        self.gotoPointRadio.setEnabled(hasMoveOrder)
        self.gotoAllyRadio.setEnabled(hasMoveOrder)
        self.gotoList.setEnabled(hasMoveOrder)
        if hasAI:
            self.modifyMiscReinforceCheck.setChecked(unit.reinforce)
            self.modifyMiscRespawnCheck.setChecked(unit.respawn)
            self.modifyMisc1Check.setChecked(unit.misc1)
        self.orderSet1Radio.setEnabled(hasAI)
        self.orderSet2Radio.setEnabled(hasAI)
        self.gotoCheck.setEnabled(hasAI)
        self.modifyMiscReinforceCheck.setEnabled(hasAI)
        self.modifyMiscRespawnCheck.setEnabled(hasAI)
        self.modifyMisc1Check.setEnabled(hasAI)
        if hasAI:
            orderNum = unit.ai[self.curOrderSet + 1][0] % 32
            if orderType == 2 and orderNum > self.curUnitIdx:
                orderNum -= 1
            self.gotoList.setCurrentIndex(orderNum)
            self.targetList.setCurrentIndex(unit.ai[self.curOrderSet + 1][1])

    def updateGeneralWindow(self):
        battle = self.curBattle
        if battle.boss:
            self.winBossRadio.setChecked(True)
        else:
            self.winAllRadio.setChecked(True)
        self.battleGfxList.setEnabled(self.overrideBattleGfxRadio.isChecked())

    def updateMapWindow(self):
        battle = self.curBattle
        self.mapList.setCurrentIndex(battle.map_index)
        self.boundsXCtrl.setValue(battle.map_x1)
        self.boundsYCtrl.setValue(battle.map_y1)
        self.boundsX2Ctrl.setValue(battle.map_x2)
        self.boundsY2Ctrl.setValue(battle.map_y2)

    def updateZoneWindow(self):
        battle = self.curBattle
        hasRegions = (len(battle.regions) != 0)
        hasPoints = (len(battle.points) != 0)
        self.regionType1Radio.setEnabled(hasRegions)
        self.regionType2Radio.setEnabled(hasRegions)
        self.regionList.setEnabled(hasRegions)
        self.regionXCtrl.setEnabled(hasRegions)
        self.regionYCtrl.setEnabled(hasRegions)
        self.regionX2Ctrl.setEnabled(hasRegions)
        self.regionY2Ctrl.setEnabled(hasRegions)
        self.regionX3Ctrl.setEnabled(hasRegions)
        self.regionY3Ctrl.setEnabled(hasRegions)
        self.regionX4Ctrl.setEnabled(hasRegions)
        self.regionY4Ctrl.setEnabled(hasRegions)
        self.pointList.setEnabled(hasPoints)
        self.pointXCtrl.setEnabled(hasPoints)
        self.pointYCtrl.setEnabled(hasPoints)
        if hasRegions:
            self.changeRegion(self.curRegionIdx)
        if hasPoints:
            self.changePoint(self.curPointIdx)

    def OnChangePage(self, idx):
        self.updateMapViewerContext()

    def updateMapViewerContext(self):
        if self.mapViewer.inited:
            pg = self.battleNotebook.currentIndex()
            if pg == 0:
                self.mapViewer.updateContext(consts.VC_BATTLE_UNITS)
            elif pg == 1:
                self.mapViewer.updateContext(consts.VC_BATTLE_BOUNDS)
            elif pg == 2:
                self.mapViewer.updateContext(consts.VC_BATTLE_AI_ZONES)
            elif pg == 3:
                self.mapViewer.updateContext(consts.VC_BATTLE_TERRAIN)
            else:
                self.mapViewer.updateContext(consts.VC_NOTHING)
            self.mapViewer.refreshMapView()

    def disableUnimplemented(self):
        self.winCustomRadio.setEnabled(False)
        self.cutsceneBeforeList.setEnabled(False)
        self.cutsceneAfterList.setEnabled(False)
        self.overrideBattleGfxRadio.setEnabled(False)
        self.defaultBattleGfxRadio.setEnabled(False)
        self.propRepeatableCheck.setEnabled(False)
        self.propMandatoryCheck.setEnabled(False)
        self.propHalfEXPCheck.setEnabled(False)
        self.modifyMiscItemBrokenCheck.setEnabled(False)
        self.modifyItemList.setEnabled(False)

    def getCurrentData(self):
        return self.curBattle

    changeSelection = changeBattle

    curBattle = property(lambda self: self.rom.data["battles"][self.curBattleIdx])
    curPanel = property(lambda self: self.allGroupPanels[self.curUnitContext][self.curUnitIdx])
    curUnit = property(lambda self: self.allGroupData[self.curUnitContext][self.curUnitIdx])
    allGroupData = property(lambda self: [self.curBattle.enemies, self.curBattle.force, self.curBattle.npcs])