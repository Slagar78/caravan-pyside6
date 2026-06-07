import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QRadioButton, QCheckBox,
    QScrollArea, QTabWidget, QTableWidget, QTableWidgetItem,
    QStyleFactory, QMessageBox, QFileDialog, QFrame, QSizePolicy,
    QAbstractItemView, QHeaderView, QGroupBox
)
from PySide6.QtCore import Qt, QTimer, QEvent, QSize
from PySide6.QtGui import QPixmap, QColor, QBrush, QPen, QFont, QIcon
import rompanel
import data
import window, consts

h2i = lambda i: int(i, 16)

icons = []
iconNames = ["lowsky", "plains", "road", "grass", "forest", "hill", "desert", "sky", "water", "blocked"]
for n in iconNames:
    pixmap = QPixmap("terrain_%s.ico" % n)
    icons.append(QIcon(pixmap))

class BattlePanel(rompanel.ROMPanel):
    frameTitle = "Battle Editor"

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

        # --- Entities (scroll area) ---
        self.scrollWnd = QScrollArea()
        self.scrollWnd.setWidgetResizable(True)
        self.scrollWnd.setFixedSize(210, 180)
        self.scrollWnd.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollWnd.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        scrollWidget = QWidget()
        scrollSizer = QVBoxLayout(scrollWidget)
        scrollWidget.setLayout(scrollSizer)

        text4 = QLabel("Monsters")
        text5 = QLabel("Shining Force Placeholder Entities")
        text7 = QLabel("NPCs")
        text8 = QLabel("Add:")

        self.monsterSizer = QGridLayout()
        self.forceSizer = QGridLayout()
        self.npcSizer = QGridLayout()

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
                ap = rompanel.SpritePanel(scrollWidget, None, 24, 24, self.palette, scale=2, bg=None, func=self.OnClickPanel)
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

        scrollSizer.addWidget(text4)
        scrollSizer.addLayout(self.monsterSizer)
        scrollSizer.addWidget(text5)
        scrollSizer.addLayout(self.forceSizer)
        scrollSizer.addWidget(text7)
        scrollSizer.addLayout(self.npcSizer)
        scrollSizer.addStretch()

        self.scrollWnd.setWidget(scrollWidget)

        scrollButtonSizer = QHBoxLayout()
        self.addMonsterButton = QPushButton("Monster")
        self.addForceButton = QPushButton("Member")
        self.addNPCButton = QPushButton("NPC")
        self.addMonsterButton.setFixedSize(55, 20)
        self.addForceButton.setFixedSize(55, 20)
        self.addNPCButton.setFixedSize(40, 20)
        scrollButtonSizer.addWidget(text8)
        scrollButtonSizer.addWidget(self.addMonsterButton)
        scrollButtonSizer.addWidget(self.addForceButton)
        scrollButtonSizer.addWidget(self.addNPCButton)

        # --- Entity Properties ---
        modifySizer = QHBoxLayout()
        modifyAnimSizer = QVBoxLayout()

        self.modifyAnimPanel = rompanel.SpritePanel(self, None, 24, 24, self.palette, scale=2, bg=None)
        self.modifyFacingUpRadio = QRadioButton()
        self.modifyFacingLeftRadio = QRadioButton()
        self.modifyFacingRightRadio = QRadioButton()
        self.modifyFacingDownRadio = QRadioButton()
        self.modifyFacingRightRadio.setChecked(True)
        self.modifyDeleteButton = QPushButton("Delete")
        self.modifyDeleteButton.setFixedSize(40, 20)

        modifyAnimFacingMidSizer = QHBoxLayout()
        modifyAnimFacingMidSizer.addWidget(self.modifyFacingLeftRadio)
        modifyAnimFacingMidSizer.addWidget(self.modifyFacingRightRadio)

        modifyAnimSizer.addWidget(self.modifyAnimPanel)
        modifyAnimSizer.addWidget(self.modifyFacingUpRadio, 0, Qt.AlignCenter)
        modifyAnimSizer.addLayout(modifyAnimFacingMidSizer)
        modifyAnimSizer.addWidget(self.modifyFacingDownRadio, 0, Qt.AlignCenter)
        modifyAnimSizer.addWidget(self.modifyDeleteButton)

        modifyMainSizer = QVBoxLayout()
        modifyTopSizer = QHBoxLayout()

        text_unit = QLabel("    Unit (temp.)")
        self.modifyList = QSpinBox()
        self.modifyList.setMaximum(175)
        self.modifyItemList = QComboBox()
        self.modifyXCtrl = QSpinBox()
        self.modifyXCtrl.setMaximum(47)
        self.modifyYCtrl = QSpinBox()
        self.modifyYCtrl.setMaximum(47)

        modifyTopSizer.addWidget(text_unit)
        modifyTopSizer.addWidget(self.modifyList)
        modifyTopSizer.addWidget(QLabel("Item"))
        modifyTopSizer.addWidget(self.modifyItemList)
        modifyTopSizer.addWidget(QLabel("X"))
        modifyTopSizer.addWidget(self.modifyXCtrl)
        modifyTopSizer.addWidget(QLabel("Y"))
        modifyTopSizer.addWidget(self.modifyYCtrl)

        modifyMainSizer.addLayout(modifyTopSizer)

        # AI sub-panels
        blankText = QLabel(" ")
        self.orderSet1Radio = QRadioButton(" Edit Order Set 1")
        self.orderSet2Radio = QRadioButton(" Edit Order Set 2")
        self.orderSet1Radio.setChecked(True)

        self.targetCheck = QCheckBox(" Use trigger region...")
        self.targetList = QComboBox()
        self.gotoCheck = QCheckBox(" Use spec. move order...")
        self.gotoForceRadio = QRadioButton(" Follow force member...")
        self.gotoPointRadio = QRadioButton(" Move towards point...")
        self.gotoAllyRadio = QRadioButton(" Follow ally...")
        self.gotoForceRadio.setChecked(True)
        self.gotoList = QComboBox()

        aiText = QLabel("AI:")
        self.modifyAICtrl = QSpinBox()
        self.modifyAICtrl.setMaximum(15)

        modifyMiscSizer = QVBoxLayout()
        self.modifyMiscItemBrokenCheck = QCheckBox(" Extra item is broken")
        self.modifyMiscReinforceCheck = QCheckBox(" Region-triggered spawn")
        self.modifyMiscRespawnCheck = QCheckBox(" Continually respawn")
        self.modifyMisc1Check = QCheckBox(" ???")
        modifyMiscSizer.addWidget(aiText)
        modifyMiscSizer.addWidget(self.modifyAICtrl)
        modifyMiscSizer.addWidget(self.modifyMiscItemBrokenCheck)
        modifyMiscSizer.addWidget(self.modifyMiscReinforceCheck)
        modifyMiscSizer.addWidget(self.modifyMiscRespawnCheck)
        modifyMiscSizer.addWidget(self.modifyMisc1Check)

        modifyTargetSizer = QVBoxLayout()
        modifyTargetSizer.addWidget(self.orderSet1Radio)
        modifyTargetSizer.addWidget(self.orderSet2Radio)
        modifyTargetSizer.addWidget(blankText)
        modifyTargetSizer.addWidget(self.targetCheck)
        modifyTargetSizer.addWidget(self.targetList)

        modifyGotoSizer = QVBoxLayout()
        modifyGotoSizer.addWidget(self.gotoCheck)
        modifyGotoSizer.addWidget(self.gotoForceRadio)
        modifyGotoSizer.addWidget(self.gotoPointRadio)
        modifyGotoSizer.addWidget(self.gotoAllyRadio)
        modifyGotoSizer.addWidget(self.gotoList)

        modifyBottomSizer = QHBoxLayout()
        modifyBottomSizer.addLayout(modifyMiscSizer)
        modifyBottomSizer.addLayout(modifyTargetSizer)
        modifyBottomSizer.addLayout(modifyGotoSizer)

        modifyMainSizer.addLayout(modifyBottomSizer)

        modifySizer.addLayout(modifyAnimSizer)
        modifySizer.addLayout(modifyMainSizer)

        # ====== Battle properties (tab widget) ======
        self.battleNotebook = QTabWidget()

        genWindow = QWidget()
        mapWindow = QWidget()
        zoneWindow = QWidget()
        terrainWindow = QWidget()

        genWndSizer = QVBoxLayout(genWindow)
        mapWndSizer = QVBoxLayout(mapWindow)
        zoneWndSizer = QVBoxLayout(zoneWindow)
        terrainWndSizer = QVBoxLayout(terrainWindow)

        # --- General tab ---
        winCondText = QLabel("Win Condition")
        battleGfxText = QLabel("Battle Graphics")
        self.winAllRadio = QRadioButton(" All enemies")
        self.winBossRadio = QRadioButton(" First enemy (boss)")
        self.winCustomRadio = QRadioButton(" Custom condition")
        self.winAllRadio.setChecked(True)
        self.defaultBattleGfxRadio = QRadioButton(" Based on terrain")
        self.overrideBattleGfxRadio = QRadioButton(" Use one set for all tiles")
        self.defaultBattleGfxRadio.setChecked(True)
        self.battleGfxList = QComboBox()

        winLeft = QVBoxLayout()
        winLeft.addWidget(winCondText)
        winLeft.addWidget(self.winAllRadio)
        winLeft.addWidget(self.winBossRadio)
        winLeft.addWidget(self.winCustomRadio)
        winRight = QVBoxLayout()
        winRight.addWidget(battleGfxText)
        winRight.addWidget(self.defaultBattleGfxRadio)
        winRight.addWidget(self.overrideBattleGfxRadio)
        winRight.addWidget(self.battleGfxList)
        winSizer = QHBoxLayout()
        winSizer.addLayout(winLeft)
        winSizer.addLayout(winRight)

        genPropText = QLabel("Other Properties")
        self.propRepeatableCheck = QCheckBox(" Battle is repeatable by entering retrigger region")
        self.propMandatoryCheck = QCheckBox(" Completion of battle not dependent upon outcome")
        self.propHalfEXPCheck = QCheckBox(" Enemies give half EXP")
        propSizer = QVBoxLayout()
        propSizer.addWidget(genPropText)
        propSizer.addWidget(self.propRepeatableCheck)
        propSizer.addWidget(self.propMandatoryCheck)
        propSizer.addWidget(self.propHalfEXPCheck)

        cutsceneText = QLabel("Cutscenes")
        self.cutsceneBeforeList = QComboBox()
        self.cutsceneAfterList = QComboBox()
        cutSizer = QVBoxLayout()
        cutSizer.addWidget(cutsceneText)
        cutGrid = QGridLayout()
        cutGrid.addWidget(QLabel("Before"), 0, 0)
        cutGrid.addWidget(self.cutsceneBeforeList, 0, 1)
        cutGrid.addWidget(QLabel("After"), 1, 0)
        cutGrid.addWidget(self.cutsceneAfterList, 1, 1)
        cutSizer.addLayout(cutGrid)

        genWndSizer.addLayout(winSizer)
        genWndSizer.addLayout(propSizer)
        genWndSizer.addLayout(cutSizer)

        # --- Map tab ---
        mapText = QLabel("Map")
        self.mapList = QComboBox()
        self.mapList.addItems([s.name for s in self.rom.data["maps"]])
        self.mapList.setCurrentIndex(self.curBattle.map_index)
        mapSizer = QHBoxLayout()
        mapSizer.addWidget(mapText)
        mapSizer.addWidget(self.mapList)

        boundsText = QLabel("Camera Bounds")
        self.boundsXCtrl = QSpinBox(); self.boundsXCtrl.setMaximum(47)
        self.boundsYCtrl = QSpinBox(); self.boundsYCtrl.setMaximum(47)
        self.boundsX2Ctrl = QSpinBox(); self.boundsX2Ctrl.setMaximum(47)
        self.boundsY2Ctrl = QSpinBox(); self.boundsY2Ctrl.setMaximum(47)
        triggerXCtrl = QSpinBox(); triggerXCtrl.setMaximum(47); triggerXCtrl.setEnabled(False)
        triggerYCtrl = QSpinBox(); triggerYCtrl.setMaximum(47); triggerYCtrl.setEnabled(False)
        triggerX2Ctrl = QSpinBox(); triggerX2Ctrl.setMaximum(47); triggerX2Ctrl.setEnabled(False)
        triggerY2Ctrl = QSpinBox(); triggerY2Ctrl.setMaximum(47); triggerY2Ctrl.setEnabled(False)

        coordGrid1 = QGridLayout()
        coordGrid1.addWidget(QLabel("X1"), 0, 0)
        coordGrid1.addWidget(self.boundsXCtrl, 0, 1)
        coordGrid1.addWidget(QLabel("Y1"), 1, 0)
        coordGrid1.addWidget(self.boundsYCtrl, 1, 1)
        coordGrid1.addWidget(QLabel("X2"), 0, 2)
        coordGrid1.addWidget(self.boundsX2Ctrl, 0, 3)
        coordGrid1.addWidget(QLabel("Y2"), 1, 2)
        coordGrid1.addWidget(self.boundsY2Ctrl, 1, 3)

        coordGrid2 = QGridLayout()
        coordGrid2.addWidget(QLabel("X1"), 0, 0)
        coordGrid2.addWidget(triggerXCtrl, 0, 1)
        coordGrid2.addWidget(QLabel("Y1"), 1, 0)
        coordGrid2.addWidget(triggerYCtrl, 1, 1)
        coordGrid2.addWidget(QLabel("X2"), 0, 2)
        coordGrid2.addWidget(triggerX2Ctrl, 0, 3)
        coordGrid2.addWidget(QLabel("Y2"), 1, 2)
        coordGrid2.addWidget(triggerY2Ctrl, 1, 3)

        coordCol1 = QVBoxLayout()
        coordCol1.addWidget(boundsText)
        coordCol1.addLayout(coordGrid1)
        coordCol2 = QVBoxLayout()
        coordCol2.addWidget(QLabel("Retrigger Region"))
        coordCol2.addLayout(coordGrid2)

        coordSizer = QHBoxLayout()
        coordSizer.addLayout(coordCol1)
        coordSizer.addLayout(coordCol2)

        mapWndSizer.addLayout(mapSizer)
        mapWndSizer.addLayout(coordSizer)

        # --- AI Zones tab ---
        self.regionList = QComboBox()
        self.pointList = QComboBox()
        self.regionType1Radio = QRadioButton(" Type 1")
        self.regionType2Radio = QRadioButton(" Type 2")
        self.regionType1Radio.setChecked(True)
        self.addRegionButton = QPushButton("New Region"); self.addRegionButton.setEnabled(False)
        self.deleteRegionButton = QPushButton("Delete"); self.deleteRegionButton.setEnabled(False)
        self.addPointButton = QPushButton("New Point"); self.addPointButton.setEnabled(False)
        self.deletePointButton = QPushButton("Delete"); self.deletePointButton.setEnabled(False)

        self.regionXCtrl = QSpinBox(); self.regionXCtrl.setMaximum(47)
        self.regionYCtrl = QSpinBox(); self.regionYCtrl.setMaximum(47)
        self.regionX2Ctrl = QSpinBox(); self.regionX2Ctrl.setMaximum(47)
        self.regionY2Ctrl = QSpinBox(); self.regionY2Ctrl.setMaximum(47)
        self.regionX3Ctrl = QSpinBox(); self.regionX3Ctrl.setMaximum(47)
        self.regionY3Ctrl = QSpinBox(); self.regionY3Ctrl.setMaximum(47)
        self.regionX4Ctrl = QSpinBox(); self.regionX4Ctrl.setMaximum(47)
        self.regionY4Ctrl = QSpinBox(); self.regionY4Ctrl.setMaximum(47)

        self.pointXCtrl = QSpinBox(); self.pointXCtrl.setMaximum(47)
        self.pointYCtrl = QSpinBox(); self.pointYCtrl.setMaximum(47)

        regionGrid = QGridLayout()
        regionGrid.addWidget(QLabel("X1"), 0, 0); regionGrid.addWidget(self.regionXCtrl, 0, 1)
        regionGrid.addWidget(QLabel("Y1"), 1, 0); regionGrid.addWidget(self.regionYCtrl, 1, 1)
        regionGrid.addWidget(QLabel("X2"), 2, 0); regionGrid.addWidget(self.regionX2Ctrl, 2, 1)
        regionGrid.addWidget(QLabel("Y2"), 3, 0); regionGrid.addWidget(self.regionY2Ctrl, 3, 1)
        regionGrid.addWidget(QLabel("X3"), 2, 2); regionGrid.addWidget(self.regionX3Ctrl, 2, 3)
        regionGrid.addWidget(QLabel("Y3"), 3, 2); regionGrid.addWidget(self.regionY3Ctrl, 3, 3)
        regionGrid.addWidget(QLabel("X4"), 0, 2); regionGrid.addWidget(self.regionX4Ctrl, 0, 3)
        regionGrid.addWidget(QLabel("Y4"), 1, 2); regionGrid.addWidget(self.regionY4Ctrl, 1, 3)

        pointGrid = QGridLayout()
        pointGrid.addWidget(QLabel("X"), 0, 0); pointGrid.addWidget(self.pointXCtrl, 0, 1)
        pointGrid.addWidget(QLabel("Y"), 1, 0); pointGrid.addWidget(self.pointYCtrl, 1, 1)

        regionSizer = QVBoxLayout()
        regionSizer.addWidget(QLabel("Regions"))
        regionSizer.addWidget(self.regionList)
        regionSizer.addWidget(self.regionType1Radio)
        regionSizer.addWidget(self.regionType2Radio)
        regionSizer.addLayout(regionGrid)

        pointSizer = QVBoxLayout()
        pointSizer.addWidget(QLabel("Points"))
        pointSizer.addWidget(self.pointList)
        pointSizer.addLayout(pointGrid)

        zoneSizer = QHBoxLayout()
        zoneSizer.addLayout(regionSizer)
        zoneSizer.addLayout(pointSizer)

        zoneWndSizer.addLayout(zoneSizer)

        # --- Terrain tab ---
        diffColors = [QColor(255,255,255), QColor(192,255,192), QColor(128,255,128),
                      QColor(255,255,128), QColor(255,192,128), QColor(255,128,128),
                      QColor(240,112,112), QColor(224,96,96), QColor(208,80,80),
                      QColor(192,64,64), QColor(176,48,48), QColor(160,32,32),
                      QColor(128,16,16), QColor(96,0,0), QColor(64,0,0), QColor(64,64,64)]
        self.terrainInfoGrid = QTableWidget(13, 9)
        self.terrainInfoGrid.horizontalHeader().setVisible(False)
        self.terrainInfoGrid.verticalHeader().setVisible(False)
        self.terrainInfoGrid.setFixedSize(340, 400)
        movetypes = ["Free", "Foot", "Horse", "Fast", "Tires", "Fly", "Float", "Water", "Foot2", "Horse2", "Fast2", "Foot3", "Foot4"]
        terraintypes = ["Low Sky", "Plains", "Road", "Grass", "Forest", "Hill", "Desert", "High Sky", "Water", "Inaccessible"]
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

        bmpWidget = QWidget()
        bmpLayout = QHBoxLayout(bmpWidget)
        self.terrainIconBtns = []
        for i, bmp in enumerate(icons):
            btn = QPushButton()
            btn.setIcon(bmp)
            btn.setToolTip(terraintypes[i])
            btn.setProperty("context", i)
            btn.clicked.connect(self.OnSelectTerrainType)
            bmpLayout.addWidget(btn)
            self.terrainIconBtns.append(btn)
        self.curTerrainBmp = QLabel()
        self.curTerrainBmp.setPixmap(icons[0].pixmap(32,32))
        self.curTerrainType = 0

        terrainSizer = QVBoxLayout()
        terrainSizer.addWidget(QLabel("^ Click"))
        terrainSizer.addWidget(bmpWidget)
        terrainSizer.addWidget(QLabel("Current:"))
        terrainSizer.addWidget(self.curTerrainBmp)
        terrainSizer.addWidget(self.terrainInfoGrid)

        terrainWndSizer.addLayout(terrainSizer)

        # Map viewer
        self.mapViewer = window.BattleMapViewer(self, None, self)
        self.mapViewer.init(None, None)
        self.mapViewer.mapViewPanel.drawFlags = False

        self.battleNotebook.addTab(genWindow, "General")
        self.battleNotebook.addTab(mapWindow, "Map")
        self.battleNotebook.addTab(zoneWindow, "AI Zones")
        self.battleNotebook.addTab(terrainWindow, "Terrain")

        # Main layout
        self.sizer.addWidget(self.scrollWnd, 0, 0)
        self.sizer.addLayout(scrollButtonSizer, 1, 0)
        self.sizer.addWidget(self.battleNotebook, 0, 1)
        self.sizer.addLayout(modifySizer, 1, 1)
        self.sizer.addWidget(self.mapViewer, 0, 2, 3, 1)

        self.changeBattle(0)
        self.updateAnimPanels()
        self.setAnimPanelSelected(True)
        self.refreshAnimPanels()
        self.disableUnimplemented()

        # Connections
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
        self.gotoForceRadio.toggled.connect(self.OnSelectGotoForce)
        self.gotoPointRadio.toggled.connect(self.OnSelectGotoPoint)
        self.gotoAllyRadio.toggled.connect(self.OnSelectGotoAlly)
        self.modifyMiscReinforceCheck.toggled.connect(self.OnToggleReinforce)
        self.modifyMiscRespawnCheck.toggled.connect(self.OnToggleRespawn)
        self.modifyMisc1Check.toggled.connect(self.OnToggleMisc1)

        self.printed = False
        
    # ========== Обработчики и вспомогательные методы ==========
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
            self.curUnit.idx = num+64
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
        self.curUnit.ai[self.curOrderSet+1][1] = 15 - (checked * 15)
        self.updateTargetList()
        self.updateModifyEntity()
        self.modify()

    def OnToggleGotoType(self, checked):
        self.curUnit.ai[self.curOrderSet+1][0] = 255 - (checked * 255)
        self.updateGotoList()
        self.updateModifyEntity()
        self.modify()

    def OnSelectTargetEntry(self, idx):
        if idx >= 0:
            self.curUnit.ai[self.curOrderSet+1][1] = idx
            self.modify()

    def OnSelectGotoForce(self, checked):
        if checked:
            self.curUnit.ai[self.curOrderSet+1][0] = 0
            self.updateGotoList()
            self.modify()

    def OnSelectGotoPoint(self, checked):
        if checked:
            self.curUnit.ai[self.curOrderSet+1][0] = 64
            self.updateGotoList()
            self.modify()

    def OnSelectGotoAlly(self, checked):
        if checked:
            self.curUnit.ai[self.curOrderSet+1][0] = 128
            self.updateGotoList()
            self.modify()

    def OnSelectGotoEntry(self, idx):
        if idx < 0: return
        type = int(self.curUnit.ai[self.curOrderSet+1][0] / 64)
        if type == 2 and idx >= self.curUnitIdx:
            idx += 1
        self.curUnit.ai[self.curOrderSet+1][0] = type*64 + idx
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

    def OnChangeBoundsX(self, val): self.curBattle.map_x1 = val; self.modify()
    def OnChangeBoundsY(self, val): self.curBattle.map_y1 = val; self.modify()
    def OnChangeBoundsX2(self, val): self.curBattle.map_x2 = val; self.modify()
    def OnChangeBoundsY2(self, val): self.curBattle.map_y2 = val; self.modify()

    def OnSelectRegion(self, idx): self.changeRegion(idx)
    def OnSelectPoint(self, idx): self.changePoint(idx)

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
        if checked: self.curBattle.regions[self.curRegionIdx].type = 4; self.modify()
    def OnSelectRegionType2(self, checked):
        if checked: self.curBattle.regions[self.curRegionIdx].type = 3; self.modify()

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
        self.curTerrainBmp.setPixmap(icons[num].pixmap(32,32))
        if num == len(icons)-1:
            self.curTerrainType = 255
        else:
            self.curTerrainType = num

    def OnSelectGraphicsDefault(self, checked):
        if checked: self.updateGeneralWindow()
    def OnSelectGraphicsOverride(self, checked):
        if checked: self.updateGeneralWindow()

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
        type = self.curUnit.ai[self.curOrderSet+1][0] // 64
        text = ["Force Member %i", "Point %i", "Monster %i", ""][type]
        num = [len(battle.force), len(battle.points), len(battle.enemies), 0][type]
        items = [text % i for i in range(num)]
        if type == 2:
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
                        self.rom.getSprites(idx, idx+2)
                    if con == 2:
                        ap.sprite = sprites[idx+[1,0,1,2][curData[p].facing]]
                        ap.flip = curData[p].facing == 0
                    else:
                        ap.sprite = sprites[idx+2]
                        ap.flip = False
                    ap.context = con
                    ap.num = p
                else:
                    ap.sprite = None
                    ap.refreshSprite([])
        self.scrollWnd.widget().adjustSize()

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
            self.modifyList.setValue(unit.idx-64)
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
            order = unit.ai[self.curOrderSet+1]
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
            orderNum = unit.ai[self.curOrderSet+1][0] % 32
            if orderType == 2 and orderNum > self.curUnitIdx:
                orderNum -= 1
            self.gotoList.setCurrentIndex(orderNum)
            self.targetList.setCurrentIndex(unit.ai[self.curOrderSet+1][1])

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