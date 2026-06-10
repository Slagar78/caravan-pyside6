import sys
from PySide6.QtWidgets import (
    QMainWindow, QMdiSubWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QScrollBar, QSlider, QCheckBox, QLabel, QComboBox, QApplication,
    QScrollArea
)
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QIcon, QFont, QWheelEvent, QMouseEvent, QResizeEvent, QCloseEvent
from PySide6.QtWidgets import QSizePolicy
import rompanel, consts


caravanIcon = QIcon("caravan.ico")

class CaravanParentFrame(QMainWindow):
    """Базовый класс главного окна, аналог wx.MDIParentFrame"""
    def __init__(self, parent=None, id=None, subTitle=None, *args, **kwargs):
        super().__init__(parent)
        self.baseTitle = "The Caravan v0.6 UNSTABLE"
        if subTitle:
            self.baseTitle += " -- " + subTitle
        self.setWindowTitle(self.baseTitle)
        self.resize(1024, 768)
        self.setWindowIcon(caravanIcon)
        # Вместо CreateStatusBar()
        self.statusBar().showMessage("Ready")
        self.id = id  # сохраняем для совместимости, но не используется

class CaravanChildFrame(QMdiSubWindow):
    """Базовый класс дочернего MDI-окна, аналог wx.MDIChildFrame"""
    def __init__(self, parent=None, id=None, title="", *args, **kwargs):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowIcon(caravanIcon)
        self.id = id

class MapViewer(QWidget):
    def __init__(self, parent, id, mainFrame, *args, **kwargs):
        super().__init__(parent)
        self.parent = parent
        self.mainFrame = mainFrame
        self.inited = False
        self.map = None
        self.palette = None
        self.viewerContext = 0
        self.curZoom = 5
        self.isDragging = False
        self.dragX1 = self.dragY1 = self.dragX2 = self.dragY2 = 0
        self.curMapIdx = None
        self.viewPageWidth = self.viewPageHeight = 5
        self.viewDownX = self.viewDownY = 0
        self.mouseBlockX = self.mouseBlockY = 0
        self.scales = [.25, .33, .5, .75, 1, 1.5, 2, 3, 5]
        self.vcTexts = ["Nothing", "Blocks", "Flags", "Event:Warp", "Event:Copy", "Event:Item", "Area"]
        self.mainPanel = self.mainSizer = self.viewGrid = None
        self.mapViewPanel = None
        self.scrollArea = None
        self.gridCheck = None
        self.sideSizer = QVBoxLayout()
        self.mousePosText = QLabel("(0,0)")
        self.curZoomText = QLabel("100%")
        self.curEditText = QLabel("Blocks")
        self.zoomSlider = QSlider(Qt.Vertical)
        self.dispLayersCheck = QCheckBox(" Blocks")
        self.dispFlagsCheck = QCheckBox(" Flags")
        self.topCheck = QCheckBox("Always on top")
        self.dragCheck = QCheckBox("Alternate drag mode")

    def init(self, map, palette):
        if self.inited: return
        self.inited = True
        if map is None:
            self.curMapIdx = 0
            map = self.mainFrame.rom.data["maps"][0]
        if palette is None:
            palette = self.mainFrame.rom.data["palettes"][map.paletteIdx]
        self.mainPanel = QWidget(self)
        self.mainSizer = QHBoxLayout(self.mainPanel)
        self.mainSizer.setContentsMargins(0, 0, 0, 0)

        # Панель карты
        self.mapViewPanel = rompanel.MapViewPanel(
            self.mainPanel, None, 24*64, 24*64, self.palette,
            scale=1, bg=16, func=self.OnClickViewPanel, edit=True, grid=24
        )
        self.mapViewPanel.id = 0

        from PySide6.QtGui import QPen, QColor
        self.mapViewPanel.eventCoordPen = QPen(QColor(255, 0, 0), 2)
        self.mapViewPanel.copySrcPen = QPen(QColor(0, 255, 0), 2)
        self.mapViewPanel.copyDestPen = QPen(QColor(0, 0, 255), 2)
        self.mapViewPanel.warpCoordPen = QPen(QColor(255, 255, 0), 2)
        self.mapViewPanel.eventPen = QPen(QColor(255, 0, 255), 2)
        self.mapViewPanel.tablePen = QPen(QColor(0, 255, 255), 2)
        self.mapViewPanel.floorPen = QPen(QColor(128, 128, 128), 2)

        # QScrollArea с принудительным отключением растягивания
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(False)
        self.scrollArea.setWidget(self.mapViewPanel)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # Запрещаем QScrollArea растягиваться шире, чем нужно для скроллбаров
        self.scrollArea.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        # Чекбокс сетки
        self.gridCheck = QCheckBox(self.mainPanel)
        self.gridCheck.setChecked(True)
        self.gridCheck.stateChanged.connect(self.OnToggleGridCheck)

        # Компоновка
        self.viewGrid = QGridLayout()
        self.viewGrid.setColumnStretch(0, 1)
        self.viewGrid.setRowStretch(0, 1)
        self.viewGrid.addWidget(self.scrollArea, 0, 0)
        self.viewGrid.addWidget(self.gridCheck, 1, 0, Qt.AlignRight)
        self.mainSizer.addLayout(self.viewGrid, 1)

        frmSizer = QVBoxLayout(self)
        frmSizer.setContentsMargins(0, 0, 0, 0)
        frmSizer.addWidget(self.mainPanel, 1)
        self.setLayout(frmSizer)
        self.installEventFilter(self)
        self.setMouseTracking(True)
        if map is not None or palette is not None:
            self.changeMap(map, palette)
                      
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.inited:
            self.updateScrollbars()
            self.refreshMapView()

    def OnResize(self, event):
        self.updateScrollbars()
        self.refreshMapView()

    def OnSelectMap(self, idx):
        map = self.getContentPanel().rom.data["maps"][idx]
        palette = self.getContentPanel().rom.data["palettes"][map.paletteIdx]
        self.changeMap(map, palette)

    def OnChangeZoom(self, value):
        self.changeZoom(value)

    def changeZoom(self, zoom):
        self.curZoom = zoom
        self.zoomSlider.setValue(zoom)
        s = self.scales[self.curZoom]
        if self.mapViewPanel.scale != s:
            self.mapViewPanel.scale = s
            self.mapViewPanel.setFixedSize(self.map.width * 24 * s, self.map.height * 24 * s)
            self.curZoomText.setText(f"{int(s * 100)}%")
            self.setViewPos(self.curViewX * s, self.curViewY * s)
            self.refreshMapView()

    def OnToggleGridCheck(self, state):
        self.mapViewPanel.grid = 24 if state == Qt.Checked else False
        self.refreshMapView()

    def OnToggleDispCheck(self, state):
        self.mapViewPanel.drawBlocks = (state == Qt.Checked)
        self.mapViewPanel.update()
        self.refreshMapView()

    def OnToggleFlagCheck(self, state):
        self.mapViewPanel.drawFlags = (state == Qt.Checked)
        self.mapViewPanel.update()
        self.refreshMapView()

    def OnToggleTopCheck(self, state):
        flags = self.windowFlags()
        if flags & Qt.WindowStaysOnTopHint:
            flags &= ~Qt.WindowStaysOnTopHint
        else:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    def wheelEvent(self, event: QWheelEvent):
        rt = event.angleDelta().y()
        if event.modifiers() & Qt.ShiftModifier:
            if rt > 0:
                zoom = min(len(self.scales)-1, self.curZoom+1)
            elif rt < 0:
                zoom = max(0, self.curZoom-1)
            if zoom != self.curZoom:
                self.changeZoom(zoom)
        elif event.modifiers() & Qt.ControlModifier:
            self.setViewPos(self.curViewX - rt, self.curViewY)
        else:
            self.setViewPos(self.curViewX, self.curViewY - rt)
        self.refreshMapView()
        event.accept()

    def OnChangeMapView(self, value):
        pass

    def OnClickViewPanel(self, event):
        pass

    def setViewPos(self, x, y):
        self.scrollArea.horizontalScrollBar().setValue(int(x))
        self.scrollArea.verticalScrollBar().setValue(int(y))

    def centerViewPos(self, x, y):
        sizeX = self.scrollArea.viewport().width()
        sizeY = self.scrollArea.viewport().height()
        self.setViewPos(x - sizeX/2, y - sizeY/2)

    def refreshMapView(self):
        if self.inited:
            self.mapViewPanel.update()

    def changeMap(self, map, palette):
        if map != self.map or palette != self.palette:
            if map is not None:
                self.map = map
            if palette is not None:
                self.palette = palette
            if hasattr(self.getContentPanel(), "updateMapViewerContext"):
                self.getContentPanel().updateMapViewerContext()
            else:
                self.updateContext(self.viewerContext)
            if not self.map.loaded:
                self.getContentPanel().rom.getMaps(self.curMapIdx, self.curMapIdx)
            self.mapViewPanel.changeMap(self.map, self.palette)
            s = self.scales[self.curZoom]
            self.mapViewPanel.setFixedSize(self.map.width * 24 * s, self.map.height * 24 * s)
            self.mapViewPanel.curViewX = 0
            self.mapViewPanel.curViewY = 0
            self.mapViewPanel.update()
            self.setViewPos(0, 0)
            self.updateScrollbars()

    def updateScrollbars(self):
        pass

    curViewX = property(lambda self: self.mapViewPanel.curViewX)
    curViewY = property(lambda self: self.mapViewPanel.curViewY)

    def getContentPanel(self):
        return self.parent

    def drawDraggingRect(self, painter, tx, ty, ox, oy):
        pass
    def drawWarpPoints(self, painter, tx, ty, ox, oy):
        pass
    def drawEventPoint(self, painter, tx, ty, ox, oy):
        pass
    def updateContext(self, context=None):
        pass

class BattleMapViewer(QWidget):
    def __init__(self, parent, id, mainFrame, *args, **kwargs):
        super().__init__(parent)
        self.parent = parent
        self.mainFrame = mainFrame
        self.inited = False
        self.map = None
        self.palette = None
        self.viewerContext = 0
        self.curZoom = 5
        self.isDragging = False
        self.dragX1 = self.dragY1 = self.dragX2 = self.dragY2 = 0
        self.curMapIdx = None
        self.viewPageWidth = self.viewPageHeight = 5
        self.viewDownX = self.viewDownY = 0
        self.mouseBlockX = self.mouseBlockY = 0
        self.scales = [.25, .33, .5, .75, 1, 1.5, 2, 3, 5]
        self.vcTexts = ["Nothing", "Units", "Map Bounds", "AI Zones", "Terrain"]
        self.mainPanel = None
        self.mapViewPanel = None
        self.mapViewBarX = None
        self.mapViewBarY = None
        self.gridCheck = None
        self.mousePosText = QLabel("(0,0)")
        self.curZoomText = QLabel("100%")
        self.curEditText = QLabel("Nothing")
        self.zoomSlider = QSlider(Qt.Vertical)
        self.dispLayersCheck = QCheckBox(" Blocks")
        self.dispFlagsCheck = QCheckBox(" Flags")
        self.topCheck = QCheckBox("Always on top")
        self.dragCheck = QCheckBox("Alternate drag mode")
        self.sideSizer = QVBoxLayout()

    def init(self, map, palette):
        if self.inited:
            return
        self.inited = True

        if map is None:
            self.curMapIdx = 0
            map = self.mainFrame.rom.data["maps"][0]
        if palette is None:
            palette = self.mainFrame.rom.data["palettes"][map.paletteIdx]

        self.mainPanel = QWidget(self)
        mainLayout = QVBoxLayout(self.mainPanel)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)

        # ==================== GRID ====================
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)

        self.mapViewPanel = rompanel.MapViewPanel(
            self.mainPanel, None, 24*64, 24*64, self.palette,
            scale=1, bg=16, func=self.OnClickViewPanel, edit=True, grid=24
        )
        self.mapViewPanel.id = 0
        self.mapViewPanel.setMinimumSize(0, 0)
        self.mapViewPanel.setMaximumSize(16777215, 16777215)
        self.mapViewPanel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        from PySide6.QtGui import QPen, QColor
        self.mapViewPanel.eventCoordPen = QPen(QColor(255, 0, 0), 2)
        self.mapViewPanel.copySrcPen = QPen(QColor(0, 255, 0), 2)
        self.mapViewPanel.copyDestPen = QPen(QColor(0, 0, 255), 2)
        self.mapViewPanel.warpCoordPen = QPen(QColor(255, 255, 0), 2)
        self.mapViewPanel.eventPen = QPen(QColor(255, 0, 255), 2)
        self.mapViewPanel.tablePen = QPen(QColor(0, 255, 255), 2)
        self.mapViewPanel.floorPen = QPen(QColor(128, 128, 128), 2)

        # Скроллбары
        self.mapViewBarX = QScrollBar(Qt.Horizontal, self.mainPanel)
        self.mapViewBarX.setFixedHeight(18)                    # ← ФИКСИРОВАННАЯ ВЫСОТА
        self.mapViewBarX.setPageStep(self.viewPageWidth * 2)
        self.mapViewBarX.setMaximum(63)
        self.mapViewBarX.setTracking(True)
        self.mapViewBarX.setProperty("context", "mapx")
        self.mapViewBarX.valueChanged.connect(self.OnChangeMapView)

        self.mapViewBarY = QScrollBar(Qt.Vertical, self.mainPanel)
        self.mapViewBarY.setFixedWidth(18)                     # ← ФИКСИРОВАННАЯ ШИРИНА
        self.mapViewBarY.setPageStep(self.viewPageHeight * 2)
        self.mapViewBarY.setMaximum(63)
        self.mapViewBarY.setTracking(True)
        self.mapViewBarY.setProperty("context", "mapy")
        self.mapViewBarY.valueChanged.connect(self.OnChangeMapView)

        self.gridCheck = QCheckBox(self.mainPanel)
        self.gridCheck.setChecked(True)
        self.gridCheck.stateChanged.connect(self.OnToggleGridCheck)

        grid.addWidget(self.mapViewPanel, 0, 0)
        grid.addWidget(self.mapViewBarY, 0, 1)
        grid.addWidget(self.mapViewBarX, 1, 0)
        grid.addWidget(self.gridCheck, 1, 1, Qt.AlignCenter)

        grid.setRowStretch(0, 1)
        grid.setColumnStretch(0, 1)
        grid.setRowStretch(1, 0)
        grid.setRowMinimumHeight(1, 20)
        grid.setColumnMinimumWidth(1, 20)

        mainLayout.addLayout(grid)

        frmLayout = QVBoxLayout(self)
        frmLayout.setContentsMargins(0, 0, 0, 0)
        frmLayout.addWidget(self.mainPanel, 1)
        self.setLayout(frmLayout)

        self.installEventFilter(self)
        self.setMouseTracking(True)

        if map is not None or palette is not None:
            self.changeMap(map, palette)
            
        self.mapViewBarX.raise_()
        self.mapViewBarY.raise_()

    def OnClickViewPanel(self, event):
        """Пустая заглушка — обязательна для MapViewPanel"""
        pass

    def OnToggleTopCheck(self, state):
        """Для чекбокса Always on top"""
        flags = self.windowFlags()
        if flags & Qt.WindowStaysOnTopHint:
            flags &= ~Qt.WindowStaysOnTopHint
        else:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()            

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.inited:
            self.updateScrollbars()
            self.refreshMapView()

    def OnResize(self, event):
        self.updateScrollbars()
        self.refreshMapView()

    def changeZoom(self, zoom):
        self.curZoom = zoom
        s = self.scales[self.curZoom]
        if self.mapViewPanel.scale != s:
            self.mapViewPanel.scale = s
            if self.map:
                self.mapViewPanel.setMaximumWidth(int(self.map.width * 24 * s))
            self.updateScrollbars()
            self.setViewPos(self.curViewX, self.curViewY)
            self.refreshMapView()

    def OnToggleGridCheck(self, state):
        self.mapViewPanel.grid = 24 if state == Qt.Checked else False
        self.refreshMapView()

    def wheelEvent(self, event: QWheelEvent):
        rt = event.angleDelta().y()
        if event.modifiers() & Qt.ShiftModifier:
            if rt > 0:
                zoom = min(len(self.scales)-1, self.curZoom+1)
            elif rt < 0:
                zoom = max(0, self.curZoom-1)
            if zoom != self.curZoom:
                self.changeZoom(zoom)
        elif event.modifiers() & Qt.ControlModifier:
            self.setViewPos(self.curViewX - rt, self.curViewY)
        else:
            self.setViewPos(self.curViewX, self.curViewY - rt)
        self.refreshMapView()
        event.accept()

    def OnChangeMapView(self, value):
        obj = self.sender()
        print("SCROLL:", obj, obj.property("context"), value)

        context = obj.property("context")

        if context == "mapx":
            self.mapViewPanel.curViewX = value

        elif context == "mapy":
            self.mapViewPanel.curViewY = value

        self.refreshMapView()

    def setViewPos(self, x, y):
        if not self.map or not self.mapViewPanel:
            return
            
        s = self.mapViewPanel.scale
        maxX = self.map.width * 24
        maxY = self.map.height * 24
        sizeX = self.mapViewPanel.size().width()
        sizeY = self.mapViewPanel.size().height()

        newX = max(0, min(maxX - sizeX / s, x))
        newY = max(0, min(maxY - sizeY / s, y))

        self.mapViewPanel.curViewX = newX
        self.mapViewPanel.curViewY = newY

        # Обновляем скроллбары
        self.mapViewBarX.setValue(int(newX))
        self.mapViewBarY.setValue(int(newY))

        self.refreshMapView()

    def centerViewPos(self, x, y):
        sizeX = self.mapViewPanel.size().width()
        sizeY = self.mapViewPanel.size().height()
        self.setViewPos(x - sizeX/2, y - sizeY/2)

    def refreshMapView(self):
        if self.inited:
            self.mapViewPanel.update()

    def changeMap(self, map, palette):
        if map != self.map or palette != self.palette:
            if map is not None:
                self.map = map
            if palette is not None:
                self.palette = palette
            if hasattr(self.getContentPanel(), "updateMapViewerContext"):
                self.getContentPanel().updateMapViewerContext()
            else:
                self.updateContext(self.viewerContext)
            if not self.map.loaded:
                self.getContentPanel().rom.getMaps(self.curMapIdx, self.curMapIdx)
            self.mapViewPanel.changeMap(self.map, self.palette)
            s = self.scales[self.curZoom]
            self.mapViewPanel.setMaximumWidth(int(self.map.width * 24 * s))
            self.mapViewPanel.curViewX = 0
            self.mapViewPanel.curViewY = 0
            self.mapViewPanel.update()
            self.setViewPos(0, 0)
            self.updateScrollbars()

    def updateScrollbars(self):
        if not hasattr(self, 'map') or self.map is None or not self.mapViewPanel:
            return
        s = self.mapViewPanel.scale
        viewport_w = self.mapViewPanel.size().width()
        viewport_h = self.mapViewPanel.size().height()

        # Горизонтальный
        h_max = max(0, int(self.map.width * 24 - viewport_w / s))
        self.mapViewBarX.setMaximum(h_max)
        self.mapViewBarX.setPageStep(max(10, int(viewport_w / s)))
        self.mapViewBarX.setValue(int(self.mapViewPanel.curViewX))
        self.mapViewBarX.setVisible(h_max > 0)

        # Вертикальный
        v_max = max(0, int(self.map.height * 24 - viewport_h / s))
        self.mapViewBarY.setMaximum(v_max)
        self.mapViewBarY.setPageStep(max(10, int(viewport_h / s)))
        self.mapViewBarY.setValue(int(self.mapViewPanel.curViewY))
        self.mapViewBarY.setVisible(v_max > 0)
        
        self.mapViewBarX.raise_()
        self.mapViewBarY.raise_()

    def getContentPanel(self):
        return self.parent

    # ---------- Битвенные методы ----------
    def mousePressEvent(self, event: QMouseEvent):
        if not self.inited:
            return

        # === ПРИОРИТЕТ СКРОЛЛБАРАМ ===
        widget = self.childAt(event.pos())
        if widget is self.mapViewBarX or widget is self.mapViewBarY:
            if widget is self.mapViewBarX:
                self.mapViewBarX.mousePressEvent(event)
            else:
                self.mapViewBarY.mousePressEvent(event)
            return

        # === ОБРАБОТКА КЛИКА ПО КАРТЕ ===
        obj = self.mapViewPanel
        x = event.pos().x()
        y = event.pos().y()
        blockX = int(max(0, min(self.map.width-1, (x / obj.scale + self.curViewX) / 24)))
        blockY = int(max(0, min(self.map.height-1, (y / obj.scale + self.curViewY) / 24)))

        cont = self.getContentPanel()
        if blockX != self.mouseBlockX or blockY != self.mouseBlockY:
            self.mouseBlockX = blockX
            self.mouseBlockY = blockY
            self.mousePosText.setText(f"({blockX},{blockY})")

        button = event.button()
        modifiers = event.modifiers()

        if button == Qt.MiddleButton:
            self.viewDownX = x
            self.viewDownY = y
            obj.setFocus()
            event.accept()
            return

        battle = cont.curBattle

        if self.viewerContext == consts.VC_BATTLE_UNITS:
            if button == Qt.LeftButton:
                bx = blockX - battle.map_x1
                by = blockY - battle.map_y1
                if modifiers & Qt.ShiftModifier:
                    for g, con in enumerate(cont.allGroupData):
                        for i, u in enumerate(con):
                            if u.x == bx and u.y == by and u is not cont.curUnit:
                                cont.changeUnit(g, i)
                                event.accept()
                                return
                else:
                    cont.curUnit.x = bx
                    cont.curUnit.y = by
                    cont.modifyXCtrl.setValue(bx)
                    cont.modifyYCtrl.setValue(by)
                    cont.modify()
                    self.refreshMapView()
            elif button == Qt.RightButton:
                bx = blockX - battle.map_x1
                by = blockY - battle.map_y1
                swap = None
                for con_ in cont.allGroupData:
                    for u in con_:
                        if u.x == bx and u.y == by and u is not cont.curUnit:
                            swap = u
                            break
                    if swap: break
                if swap:
                    if modifiers & Qt.ShiftModifier:
                        if cont.curUnitContext == 2:
                            cont.changeUnitIdx(swap.idx)
                        elif cont.curUnitContext == 0:
                            cont.changeUnitIdx(swap.idx - 64)
                        else:
                            event.ignore()
                            return
                    else:
                        swap.x = cont.curUnit.x
                        swap.y = cont.curUnit.y
                        cont.curUnit.x = bx
                        cont.curUnit.y = by
                        cont.modifyXCtrl.setValue(bx)
                        cont.modifyYCtrl.setValue(by)
                    cont.modify()
                    self.refreshMapView()
            event.accept()

        elif self.viewerContext == consts.VC_BATTLE_BOUNDS:
            if button == Qt.LeftButton:
                diffX = blockX - battle.map_x1
                diffY = blockY - battle.map_y1
                battle.map_x1 = blockX
                battle.map_y1 = blockY
                if not (modifiers & Qt.ShiftModifier):
                    for con in cont.allGroupData:
                        for unit in con:
                            unit.x -= diffX
                            unit.y -= diffY
                    cont.modifyXCtrl.setValue(cont.curUnit.x)
                    cont.modifyYCtrl.setValue(cont.curUnit.y)
                if modifiers & Qt.ControlModifier:
                    battle.map_x2 += diffX
                    battle.map_y2 += diffY
            elif button == Qt.RightButton:
                diffX = blockX - battle.map_x2 + 1
                diffY = blockY - battle.map_y2 + 1
                battle.map_x2 = blockX + 1
                battle.map_y2 = blockY + 1
                if modifiers & Qt.ShiftModifier:
                    for con in cont.allGroupData:
                        for unit in con:
                            unit.x += diffX
                            unit.y += diffY
                    cont.modifyXCtrl.setValue(cont.curUnit.x)
                    cont.modifyYCtrl.setValue(cont.curUnit.y)
                if modifiers & Qt.ControlModifier:
                    for con in cont.allGroupData:
                        for unit in con:
                            unit.x -= diffX
                            unit.y -= diffY
                    battle.map_x1 += diffX
                    battle.map_y1 += diffY
            else:
                event.ignore()
                return
            cont.boundsXCtrl.setValue(battle.map_x1)
            cont.boundsYCtrl.setValue(battle.map_y1)
            cont.boundsX2Ctrl.setValue(battle.map_x2)
            cont.boundsY2Ctrl.setValue(battle.map_y2)
            obj.update()
            cont.modify()
            self.refreshMapView()
            event.accept()

        elif self.viewerContext == consts.VC_BATTLE_AI_ZONES:
            if battle.regions:
                if button == Qt.LeftButton:
                    region = battle.regions[cont.curRegionIdx]
                    bpt = [blockX - battle.map_x1, blockY - battle.map_y1]
                    if bpt == region.p1:
                        self.isDragging = 1
                    elif bpt == region.p2:
                        self.isDragging = 2
                    elif bpt == region.p3:
                        self.isDragging = 3
                    elif bpt == region.p4:
                        self.isDragging = 4
                    else:
                        self.isDragging = False
                else:
                    self.isDragging = False
                if self.isDragging:
                    region = battle.regions[cont.curRegionIdx]
                    bpt = [blockX - battle.map_x1, blockY - battle.map_y1]
                    if self.isDragging == 1:
                        cont.changeRegionX(bpt[0])
                        cont.changeRegionY(bpt[1])
                    elif self.isDragging == 2:
                        cont.changeRegionX2(bpt[0])
                        cont.changeRegionY2(bpt[1])
                    elif self.isDragging == 3:
                        cont.changeRegionX3(bpt[0])
                        cont.changeRegionY3(bpt[1])
                    elif self.isDragging == 4:
                        cont.changeRegionX4(bpt[0])
                        cont.changeRegionY4(bpt[1])
            if battle.points and button == Qt.RightButton:
                bpt = [blockX - battle.map_x1, blockY - battle.map_y1]
                cont.changePointX(bpt[0])
                cont.changePointY(bpt[1])
            event.accept()

        elif self.viewerContext == consts.VC_BATTLE_TERRAIN:
            if button == Qt.LeftButton:
                if battle.map_x1 <= blockX <= battle.map_x2 and battle.map_y1 <= blockY <= battle.map_y2:
                    realX = blockX - battle.map_x1
                    realY = blockY - battle.map_y1
                    rawIdx = realY * 48 + realX
                    tileIdx = rawIdx // 32
                    rowIdx = (rawIdx % 32) // 4
                    strIdx = (rawIdx % 4) * 2
                    if not (modifiers & Qt.ShiftModifier):
                        row = battle.terrain.tiles[tileIdx].pixels[rowIdx]
                        row = row[:strIdx] + hex(cont.curTerrainType)[2:].zfill(2) + row[strIdx+2:]
                        battle.terrain.tiles[tileIdx].pixels[rowIdx] = row
                        obj.update()
                        cont.modify()
                        self.refreshMapView()
                    else:
                        tt = int(battle.terrain.tiles[tileIdx].pixels[rowIdx][strIdx:strIdx+2], 16)
                        cont.changeTerrainType(min(len(cont.terrainIcons)-1, tt))
            event.accept()

        else:
            QWidget.mousePressEvent(self, event)

    def mouseMoveEvent(self, event: QMouseEvent):
            if not self.inited:
                return

            widget = self.childAt(event.pos())
            if widget is self.mapViewBarX or widget is self.mapViewBarY:
                if widget is self.mapViewBarX:
                    self.mapViewBarX.mouseMoveEvent(event)
                else:
                    self.mapViewBarY.mouseMoveEvent(event)
                return

            if event.buttons() & Qt.MiddleButton:
                QWidget.mouseMoveEvent(self, event)
                return

            if self.viewerContext in [consts.VC_BATTLE_AI_ZONES, consts.VC_AREA] and self.isDragging:
                pass
            else:
                QWidget.mouseMoveEvent(self, event)

    def drawBattleUnits(self, painter, tx, ty, ox, oy):
        cont = self.getContentPanel(); battle = cont.curBattle
        btx = tx - battle.map_x1; bty = ty - battle.map_y1
        sx = -btx * 24 - ox; sy = -bty * 24 - oy
        painter.setPen(self.mapViewPanel.eventCoordPen)
        painter.drawRoundedRect(sx+8, sy+8, (battle.map_x2 - battle.map_x1) * 24 - 16,
                               (battle.map_y2 - battle.map_y1) * 24 - 16, 8, 8)
        for con in range(len(cont.allGroupData)):
            curPanels = cont.allGroupPanels[con]; curData = cont.allGroupData[con]
            for idx in range(min(len(curData), len(curPanels))):
                cp = curPanels[idx]; cd = curData[idx]
                if hasattr(cp, 'bmp') and cp.bmp is not None:
                    painter.drawPixmap((cd.x - btx) * 24 - ox, (cd.y - bty) * 24 - oy, cp.bmp)
        if self.viewerContext == consts.VC_BATTLE_UNITS:
            x = cont.curUnit.x - btx; y = cont.curUnit.y - bty
            painter.setPen(self.mapViewPanel.tablePen)
            painter.drawRoundedRect(x * 24 - ox - 2, y * 24 - oy - 2, 28, 28, 8, 8)
        elif self.viewerContext == consts.VC_BATTLE_TERRAIN:
            if battle.terrain is None or not hasattr(battle.terrain, 'tiles'): return
            mw = battle.map_x2 - battle.map_x1; mh = battle.map_y2 - battle.map_y1
            for y in range(mh):
                for x in range(mw):
                    dx = (x - tx + battle.map_x1) * 32 - ox * 4 / 3
                    dy = (y - ty + battle.map_y1) * 32 - oy * 4 / 3
                    rawIdx = y * 48 + x; tileIdx = rawIdx // 32
                    rowIdx = (rawIdx % 32) // 4; strIdx = (rawIdx % 4) * 2
                    t = int(battle.terrain.tiles[tileIdx].pixels[rowIdx][strIdx:strIdx+2], 16)
                    if t < 9: painter.drawPixmap(dx, dy, cont.terrainIcons[t])
                    else: painter.drawPixmap(dx, dy, cont.terrainIcons[-1])
        elif self.viewerContext == consts.VC_BATTLE_AI_ZONES:
            if battle.regions:
                region = battle.regions[cont.curRegionIdx]
                p1x = (region.p1[0] - btx) * 24 - ox + 12; p1y = (region.p1[1] - bty) * 24 - oy + 12
                p2x = (region.p2[0] - btx) * 24 - ox + 12; p2y = (region.p2[1] - bty) * 24 - oy + 12
                p3x = (region.p3[0] - btx) * 24 - ox + 12; p3y = (region.p3[1] - bty) * 24 - oy + 12
                p4x = (region.p4[0] - btx) * 24 - ox + 12; p4y = (region.p4[1] - bty) * 24 - oy + 12
                painter.setPen(self.mapViewPanel.eventPen)
                painter.drawLine(p1x, p1y, p2x, p2y); painter.drawLine(p2x, p2y, p3x, p3y)
                painter.drawLine(p3x, p3y, p4x, p4y); painter.drawLine(p4x, p4y, p1x, p1y)
                painter.drawEllipse(p1x-8, p1y-8, 16, 16); painter.drawEllipse(p2x-8, p2y-8, 16, 16)
                painter.drawEllipse(p3x-8, p3y-8, 16, 16); painter.drawEllipse(p4x-8, p4y-8, 16, 16)
            if battle.points:
                point = battle.points[cont.curPointIdx]
                painter.setPen(self.mapViewPanel.copySrcPen)
                painter.drawRoundedRect((point[0] - btx) * 24 - ox + 4, (point[1] - bty) * 24 - oy + 4, 16, 16, 4, 4)

    def updateContext(self, context=None):
        if context is None: context = self.viewerContext
        self.viewerContext = context
        if self.inited:
            self.mapViewPanel.drawFunc = self.drawBattleUnits
            self.passes = []
            self.curEditText.setText(self.vcTexts[self.viewerContext])

    # === КРИТИЧНЫЕ СВОЙСТВА ===
    curViewX = property(lambda self: self.mapViewPanel.curViewX)
    curViewY = property(lambda self: self.mapViewPanel.curViewY)