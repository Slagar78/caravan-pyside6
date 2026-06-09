import sys
from PySide6.QtWidgets import (
    QMainWindow, QMdiSubWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QScrollBar, QSlider, QCheckBox, QLabel, QComboBox, QApplication
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
        self.dragX1 = 0
        self.dragY1 = 0
        self.dragX2 = 0
        self.dragY2 = 0
        self.curMapIdx = None

        self.viewPageWidth = 5
        self.viewPageHeight = 5
        self.viewDownX = 0
        self.viewDownY = 0
        self.mouseBlockX = 0
        self.mouseBlockY = 0
        self.viewDelay = 0
        self.maxViewDelay = 100
        self.curViewMode = 0
        self.viewAll = 0
        self.viewerContext = 0

        self.mainPanel = None
        self.mainSizer = None
        self.viewGrid = None
        self.mapViewPanel = None
        self.mapViewBarX = None
        self.mapViewBarY = None
        self.gridCheck = None
        self.sideSizer = None
        self.mousePosText = None
        self.curZoomText = None
        self.zoomSlider = None
        self.dispLayersCheck = None
        self.dispFlagsCheck = None
        self.dispEventCheck = None
        self.dispNPCCheck = None
        self.curEditText = None
        self.topCheck = None
        self.dragCheck = None
        self.scales = [.25, .33, .5, .75, 1, 1.5, 2, 3, 5]
        self.vcTexts = ["Nothing", "Blocks", "Flags", "Event:Warp", "Event:Copy", "Event:Item", "Area"]

    def init(self, map, palette):
        if not self.inited:
            self.inited = True
            if map is None:
                self.curMapIdx = 0
                map = self.mainFrame.rom.data["maps"][0]
            if palette is None:
                palette = self.mainFrame.rom.data["palettes"][map.paletteIdx]

            self.mainPanel = QWidget(self)
            self.mainSizer = QHBoxLayout(self.mainPanel)
            self.mainSizer.setContentsMargins(0, 0, 0, 0)

            self.viewGrid = QGridLayout()
            self.viewGrid.setColumnStretch(0, 1)
            self.viewGrid.setRowStretch(0, 1)

            self.mapViewPanel = rompanel.MapViewPanel(
                self.mainPanel, None, 24*64, 24*64, self.palette,
                scale=1, bg=16, func=self.OnClickViewPanel, edit=True, grid=24
            )
            self.mapViewPanel.id = 0

            self.mapViewPanel.setMinimumSize(0, 0)
            self.mapViewPanel.setMaximumSize(16777215, 16777215)
            self.mapViewPanel.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

            from PySide6.QtGui import QPen, QColor
            self.mapViewPanel.eventCoordPen = QPen(QColor(255, 0, 0), 2)
            self.mapViewPanel.copySrcPen = QPen(QColor(0, 255, 0), 2)
            self.mapViewPanel.copyDestPen = QPen(QColor(0, 0, 255), 2)
            self.mapViewPanel.warpCoordPen = QPen(QColor(255, 255, 0), 2)
            self.mapViewPanel.eventPen = QPen(QColor(255, 0, 255), 2)
            self.mapViewPanel.tablePen = QPen(QColor(0, 255, 255), 2)
            self.mapViewPanel.floorPen = QPen(QColor(128, 128, 128), 2)

            self.mapViewBarX = QScrollBar(Qt.Horizontal, self.mainPanel)
            self.mapViewBarX.setPageStep(self.viewPageWidth*2)
            self.mapViewBarX.setMaximum(63)
            self.mapViewBarX.setValue(0)
            self.mapViewBarX.setProperty("context", "mapx")
            self.mapViewBarX.valueChanged.connect(self.OnChangeMapView)

            self.mapViewBarY = QScrollBar(Qt.Vertical, self.mainPanel)
            self.mapViewBarY.setPageStep(self.viewPageHeight*2)
            self.mapViewBarY.setMaximum(63)
            self.mapViewBarY.setValue(0)
            self.mapViewBarY.setProperty("context", "mapy")
            self.mapViewBarY.valueChanged.connect(self.OnChangeMapView)

            self.gridCheck = QCheckBox(self.mainPanel)
            self.gridCheck.setChecked(True)
            self.gridCheck.stateChanged.connect(self.OnToggleGridCheck)

            self.viewGrid.addWidget(self.mapViewPanel, 0, 0)
            self.viewGrid.addWidget(self.mapViewBarY, 0, 1)
            self.viewGrid.addWidget(self.mapViewBarX, 1, 0)
            self.viewGrid.addWidget(self.gridCheck, 1, 1, Qt.AlignCenter)
            self.viewGrid.setRowStretch(0, 1)
            self.viewGrid.setColumnStretch(0, 1)

            # Фальшивые переменные для обратной совместимости
            self.sideSizer = QVBoxLayout()
            self.mousePosText = QLabel("(0,0)")
            self.curZoomText = QLabel("100%")
            self.curEditText = QLabel("Blocks")
            self.zoomSlider = QSlider(Qt.Vertical)
            self.dispLayersCheck = QCheckBox(" Blocks")
            self.dispFlagsCheck = QCheckBox(" Flags")
            self.dispEventCheck = QCheckBox(" Events")
            self.dispNPCCheck = QCheckBox(" NPCs")
            self.topCheck = QCheckBox("Always on top")
            self.dragCheck = QCheckBox("Alternate drag mode")

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
            self.updateScrollbars()
            self.curZoomText.setText(f"{int(s * 100)}%")
            self.setViewPos(self.curViewX, self.curViewY)
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
        obj = self.sender()
        if hasattr(obj, 'context'):
            if obj.context == "mapx":
                self.oldViewX = self.curViewX
                self.mapViewPanel.curViewX = value
            elif obj.context == "mapy":
                self.oldViewY = self.curViewY
                self.mapViewPanel.curViewY = value
            self.refreshMapView()

    def OnClickViewPanel(self, event):
        pass

    def setViewPos(self, x, y):
        s = self.mapViewPanel.scale
        maxX = self.map.width * 24
        maxY = self.map.height * 24
        sizeX = self.mapViewPanel.size().width()
        sizeY = self.mapViewPanel.size().height()
        self.mapViewPanel.curViewX = max(0, min(maxX - sizeX / s, x))
        self.mapViewPanel.curViewY = max(0, min(maxY - sizeY / s, y))
        self.mapViewBarX.setValue(x)
        self.mapViewBarY.setValue(y)

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
            self.mapViewPanel.curViewX = 0
            self.mapViewPanel.curViewY = 0
            self.mapViewPanel.update()
            self.setViewPos(0, 0)
            self.updateScrollbars()

    def updateScrollbars(self):
        s = self.mapViewPanel.scale
        x = self.mapViewPanel.size().width() / s
        y = self.mapViewPanel.size().height() / s
        self.mapViewBarX.setPageStep(x)
        self.mapViewBarX.setMaximum(self.map.width * 24 - x)
        self.mapViewBarY.setPageStep(y)
        self.mapViewBarY.setMaximum(self.map.height * 24 - y)

    curViewX = property(lambda self: self.mapViewPanel.curViewX)
    curViewY = property(lambda self: self.mapViewPanel.curViewY)

    def getContentPanel(self):
        return self.parent

    # --- Полные mousePressEvent и mouseMoveEvent из твоего кода ---
    def mousePressEvent(self, event: QMouseEvent):
        if not self.inited: return
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

        idx = blockY*64 + blockX
        blk = self.map.layoutData[idx]

        if self.viewerContext == consts.VC_BLOCKS:
            if modifiers & Qt.ShiftModifier:
                if button == Qt.LeftButton:
                    cont.curListBlockLeft = blk & 0x3ff
                elif button == Qt.RightButton:
                    cont.curListBlockRight = blk & 0x3ff
                cont.refreshBlockListSelPanels()
            else:
                if button == Qt.LeftButton:
                    bot = cont.curListBlockLeft & 0x3ff
                elif button == Qt.RightButton:
                    bot = cont.curListBlockRight & 0x3ff
                else:
                    event.ignore()
                    return
                top = blk & 0xfc00
                if (blk & 0x3ff) != bot:
                    self.map.layoutData[idx] = top | bot
                    obj.pixels = self.map.blocks[bot].pixels
                    obj.update()
                    cont.modify()
            event.accept()

        elif self.viewerContext == consts.VC_FLAGS:
            val = cont.curInterFlag
            if button == Qt.LeftButton:
                newObs = val & 0xc000
                newEvent = val & 0x3c00
                oldObs = blk & 0xc000
                oldEvent = blk & 0x3c00
                bot = blk & 0x3ff
                if newObs and oldObs != newObs:
                    self.map.layoutData[idx] = bot | newObs | oldEvent
                elif newObs == 0x4000:
                    self.map.layoutData[idx] ^= 0xc000
                elif newEvent and oldEvent != newEvent:
                    self.map.layoutData[idx] = bot | oldObs | newEvent
                else:
                    event.ignore(); return
            elif button == Qt.RightButton:
                if blk & 0xfc00:
                    if modifiers & Qt.ShiftModifier:
                        self.map.layoutData[idx] = blk & 0x3ff
                    else:
                        newObs = val & 0xc000
                        newEvent = val & 0x3c00
                        if newObs:
                            self.map.layoutData[idx] = blk & 0x3fff
                        if newEvent:
                            self.map.layoutData[idx] = blk & 0xc3ff
                else:
                    event.ignore(); return
            else:
                event.ignore(); return
            obj.update()
            cont.modify()

        elif self.viewerContext == consts.VC_EVENT_WARP:
            event_ = cont.getCurrentEvent()
            if event_:
                if button == Qt.LeftButton and self.map == cont.map:
                    cont.changeWarpX(blockX)
                    cont.changeWarpY(blockY)
                elif button == Qt.RightButton:
                    cont.changeWarpDestX(blockX)
                    cont.changeWarpDestY(blockY)
                    idx_map = 0
                    for i, m in enumerate(cont.rom.data["maps"]):
                        if self.map == m:
                            idx_map = i
                            break
                    cont.changeWarpMap(idx_map)
                cont.modify()
            event.accept()

        elif self.viewerContext == consts.VC_EVENT_COPY:
            event_ = cont.getCurrentEvent()
            if event_ and self.map == cont.map:
                altDrag = self.dragCheck.isChecked()
                shift = modifiers & Qt.ShiftModifier
                ctrl = modifiers & Qt.ControlModifier
                if altDrag:
                    if shift and not self.isDragging:
                        if button == Qt.LeftButton:
                            self.isDragging = "l"
                            cont.setCopyBlank(False)
                        elif button == Qt.RightButton:
                            self.isDragging = "r"
                        else:
                            event.ignore(); return
                        self.dragX1 = blockX
                        self.dragY1 = blockY
                    elif self.isDragging and button == Qt.LeftButton:
                        self.isDragging = False
                    elif self.isDragging and button == Qt.RightButton:
                        self.isDragging = False
                else:
                    if shift:
                        if button == Qt.LeftButton and not self.isDragging:
                            self.isDragging = "l"
                            cont.setCopyBlank(False)
                            self.dragX1 = blockX
                            self.dragY1 = blockY
                        elif button == Qt.RightButton and not self.isDragging:
                            self.isDragging = "r"
                            self.dragX1 = blockX
                            self.dragY1 = blockY
                if not self.isDragging:
                    if button == Qt.RightButton:
                        cont.eventPropCopyDestXCtrl.SetValue(blockX)
                        cont.eventPropCopyDestYCtrl.SetValue(blockY)
                        event_.destx = blockX
                        event_.desty = blockY
                    elif button == Qt.LeftButton:
                        if ctrl and event_.copyType != 0:
                            cont.eventPropCopyTrigXCtrl.SetValue(blockX)
                            cont.eventPropCopyTrigYCtrl.SetValue(blockY)
                            event_.x = blockX
                            event_.y = blockY
                        else:
                            cont.eventPropCopySrcXCtrl.SetValue(blockX)
                            cont.eventPropCopySrcYCtrl.SetValue(blockY)
                            event_.srcx = blockX
                            event_.srcy = blockY
                    cont.modify()
                    obj.update()
            event.accept()

        elif self.viewerContext == consts.VC_EVENT_ITEM:
            event_ = cont.getCurrentEvent()
            if event_ and self.map == cont.map:
                if button == Qt.LeftButton:
                    cont.changeItemX(blockX)
                    cont.changeItemY(blockY)
            event.accept()

        elif self.viewerContext == consts.VC_AREA:
            event_ = cont.curArea
            altDrag = self.dragCheck.isChecked()
            shift = modifiers & Qt.ShiftModifier
            if altDrag:
                if shift and not self.isDragging:
                    if button == Qt.LeftButton:
                        self.isDragging = "l"
                        cont.changeAreaLayer1X1(blockX)
                        cont.changeAreaLayer1Y1(blockY)
                    elif button == Qt.RightButton:
                        self.isDragging = "r"
                    self.dragX1 = blockX
                    self.dragY1 = blockY
                elif self.isDragging and button == Qt.LeftButton:
                    self.isDragging = False
                elif self.isDragging and button == Qt.RightButton:
                    self.isDragging = False
            else:
                if shift:
                    if button == Qt.LeftButton and not self.isDragging:
                        self.isDragging = "l"
                        cont.changeAreaLayer1X1(blockX)
                        cont.changeAreaLayer1Y1(blockY)
                        self.dragX1 = blockX
                        self.dragY1 = blockY
                    elif button == Qt.RightButton and not self.isDragging:
                        self.isDragging = "r"
                        self.dragX1 = blockX
                        self.dragY1 = blockY
            if not self.isDragging:
                if button == Qt.RightButton:
                    cont.changeAreaLayer2X1(blockX)
                    cont.changeAreaLayer2Y1(blockY)
                elif button == Qt.LeftButton:
                    width = event_.l1x2 - event_.l1x1
                    height = event_.l1y2 - event_.l1y1
                    cont.changeAreaLayer1X1(blockX)
                    cont.changeAreaLayer1Y1(blockY)
                    cont.changeAreaLayer1X2(blockX+width)
                    cont.changeAreaLayer1Y2(blockY+height)
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if not self.inited or not event.buttons(): return
        obj = self.mapViewPanel
        x = event.pos().x()
        y = event.pos().y()
        if event.buttons() & Qt.MiddleButton:
            xd = int((x - self.viewDownX) / obj.scale)
            yd = int((y - self.viewDownY) / obj.scale)
            self.oldViewX = self.curViewX
            self.oldViewY = self.curViewY
            self.setViewPos(self.curViewX - xd, self.curViewY - yd)
            if xd or yd:
                self.viewDownX = x
                self.viewDownY = y
                if self.oldViewX != self.curViewX or self.oldViewY != self.curViewY:
                    self.refreshMapView()
            event.accept()
            return

        cont = self.getContentPanel()
        blockX = int(max(0, min(self.map.width-1, (x / obj.scale + self.curViewX) / 24)))
        blockY = int(max(0, min(self.map.height-1, (y / obj.scale + self.curViewY) / 24)))

        if self.viewerContext == consts.VC_EVENT_COPY and self.isDragging:
            self.dragX2 = blockX
            self.dragY2 = blockY
            x1, x2 = sorted([blockX, self.dragX1])
            y1, y2 = sorted([blockY, self.dragY1])
            event_ = cont.getCurrentEvent()
            if event_:
                if self.isDragging == "l":
                    cont.eventPropCopySrcXCtrl.SetValue(x1)
                    cont.eventPropCopySrcYCtrl.SetValue(y1)
                    event_.srcx = x1
                    event_.srcy = y1
                else:
                    cont.eventPropCopyDestXCtrl.SetValue(x1)
                    cont.eventPropCopyDestYCtrl.SetValue(y1)
                    event_.destx = x1
                    event_.desty = y1
                cont.eventPropCopyWidthCtrl.SetValue(x2 - x1 + 1)
                cont.eventPropCopyHeightCtrl.SetValue(y2 - y1 + 1)
                event_.width = x2 - x1 + 1
                event_.height = y2 - y1 + 1
                cont.modify()
                obj.update()
        elif self.viewerContext == consts.VC_AREA and self.isDragging:
            self.dragX2 = blockX
            self.dragY2 = blockY
            x1, x2 = sorted([blockX, self.dragX1])
            y1, y2 = sorted([blockY, self.dragY1])
            if self.isDragging == "l":
                cont.changeAreaLayer1X2(x2)
                cont.changeAreaLayer1Y2(y2)
            cont.changeAreaLayer2X2(x2 - x1 + 1)
            cont.changeAreaLayer2Y2(y2 - y1 + 1)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        pass

    # Заглушки рисования (при необходимости замени на реальные)
    def drawDraggingRect(self, painter, tx, ty, ox, oy):
        pass
    def drawWarpPoints(self, painter, tx, ty, ox, oy):
        pass
    def drawEventPoint(self, painter, tx, ty, ox, oy):
        pass
    def updateContext(self, context=None):
        pass


class BattleMapViewer(MapViewer):
    def mousePressEvent(self, event: QMouseEvent):
        if not self.inited: return
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
        idx = blockY*64 + blockX
        blk = self.map.layoutData[idx]

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
                for con in cont.allGroupData:
                    for u in con:
                        if u.x == bx and u.y == by and u is not cont.curUnit:
                            swap = u
                            break
                    if swap: break
                if swap:
                    if modifiers & Qt.ShiftModifier:
                        if cont.curUnitContext == 2:
                            cont.changeUnitIdx(swap.idx)
                        elif cont.curUnitContext == 0:
                            cont.changeUnitIdx(swap.idx-64)
                        else:
                            event.ignore(); return
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
                battle.map_x2 = blockX+1
                battle.map_y2 = blockY+1
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
                event.ignore(); return
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
                    if bpt == region.p1:   self.isDragging = 1
                    elif bpt == region.p2: self.isDragging = 2
                    elif bpt == region.p3: self.isDragging = 3
                    elif bpt == region.p4: self.isDragging = 4
                    else: self.isDragging = False
                else:
                    self.isDragging = False
                if self.isDragging:
                    region = battle.regions[cont.curRegionIdx]
                    bpt = [blockX - battle.map_x1, blockY - battle.map_y1]
                    if self.isDragging == 1:
                        cont.changeRegionX(bpt[0]); cont.changeRegionY(bpt[1])
                    elif self.isDragging == 2:
                        cont.changeRegionX2(bpt[0]); cont.changeRegionY2(bpt[1])
                    elif self.isDragging == 3:
                        cont.changeRegionX3(bpt[0]); cont.changeRegionY3(bpt[1])
                    elif self.isDragging == 4:
                        cont.changeRegionX4(bpt[0]); cont.changeRegionY4(bpt[1])
            if battle.points and button == Qt.RightButton:
                bpt = [blockX - battle.map_x1, blockY - battle.map_y1]
                cont.changePointX(bpt[0]); cont.changePointY(bpt[1])
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
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if not self.inited: return
        if event.buttons() & Qt.MiddleButton:
            super().mouseMoveEvent(event)
            return
        if self.viewerContext in [consts.VC_BATTLE_AI_ZONES, consts.VC_AREA] and self.isDragging:
            pass
        else:
            super().mouseMoveEvent(event)

    def drawBattleUnits(self, painter, tx, ty, ox, oy):
        cont = self.getContentPanel()
        battle = cont.curBattle
        btx = tx - battle.map_x1
        bty = ty - battle.map_y1
        sx = -btx * 24 - ox
        sy = -bty * 24 - oy
        painter.setPen(self.mapViewPanel.eventCoordPen)
        painter.drawRoundedRect(sx+8, sy+8, (battle.map_x2 - battle.map_x1) * 24 - 16,
                               (battle.map_y2 - battle.map_y1) * 24 - 16, 8, 8)

        for con in range(len(cont.allGroupData)):
            curPanels = cont.allGroupPanels[con]
            curData = cont.allGroupData[con]
            for idx in range(len(curData)):
                cp = curPanels[idx]
                cd = curData[idx]
                if hasattr(cp, 'bmp') and cp.bmp is not None:
                    painter.drawPixmap((cd.x - btx) * 24 - ox, (cd.y - bty) * 24 - oy, cp.bmp)

        if self.viewerContext == consts.VC_BATTLE_UNITS:
            x = cont.curUnit.x - btx
            y = cont.curUnit.y - bty
            painter.setPen(self.mapViewPanel.tablePen)
            painter.drawRoundedRect(x * 24 - ox - 2, y * 24 - oy - 2, 28, 28, 8, 8)

        elif self.viewerContext == consts.VC_BATTLE_TERRAIN:
            if battle.terrain is None or not hasattr(battle.terrain, 'tiles'):
                return
            mw = battle.map_x2 - battle.map_x1
            mh = battle.map_y2 - battle.map_y1
            for y in range(mh):
                for x in range(mw):
                    dx = (x - tx + battle.map_x1) * 32 - ox * 4 / 3
                    dy = (y - ty + battle.map_y1) * 32 - oy * 4 / 3
                    rawIdx = y * 48 + x
                    tileIdx = rawIdx // 32
                    rowIdx = (rawIdx % 32) // 4
                    strIdx = (rawIdx % 4) * 2
                    t = int(battle.terrain.tiles[tileIdx].pixels[rowIdx][strIdx:strIdx+2], 16)
                    if t < 9:
                        painter.drawPixmap(dx, dy, cont.terrainIcons[t])
                    else:
                        painter.drawPixmap(dx, dy, cont.terrainIcons[-1])

        elif self.viewerContext == consts.VC_BATTLE_AI_ZONES:
            if battle.regions:
                region = battle.regions[cont.curRegionIdx]
                p1x = (region.p1[0] - btx) * 24 - ox + 12
                p1y = (region.p1[1] - bty) * 24 - oy + 12
                p2x = (region.p2[0] - btx) * 24 - ox + 12
                p2y = (region.p2[1] - bty) * 24 - oy + 12
                p3x = (region.p3[0] - btx) * 24 - ox + 12
                p3y = (region.p3[1] - bty) * 24 - oy + 12
                p4x = (region.p4[0] - btx) * 24 - ox + 12
                p4y = (region.p4[1] - bty) * 24 - oy + 12
                painter.setPen(self.mapViewPanel.eventPen)
                painter.drawLine(p1x, p1y, p2x, p2y)
                painter.drawLine(p2x, p2y, p3x, p3y)
                painter.drawLine(p3x, p3y, p4x, p4y)
                painter.drawLine(p4x, p4y, p1x, p1y)
                painter.drawEllipse(p1x-8, p1y-8, 16, 16)
                painter.drawEllipse(p2x-8, p2y-8, 16, 16)
                painter.drawEllipse(p3x-8, p3y-8, 16, 16)
                painter.drawEllipse(p4x-8, p4y-8, 16, 16)
            if battle.points:
                point = battle.points[cont.curPointIdx]
                painter.setPen(self.mapViewPanel.copySrcPen)
                painter.drawRoundedRect((point[0] - btx) * 24 - ox + 4, (point[1] - bty) * 24 - oy + 4, 16, 16, 4, 4)

    def updateContext(self, context=None):
        if context is None:
            context = self.viewerContext
        self.viewerContext = context
        if self.inited:
            self.mapViewPanel.drawFunc = self.drawBattleUnits
            self.passes = []
            self.curEditText.setText(self.vcTexts[self.viewerContext])

    vcTexts = ["Nothing", "Units", "Map Bounds", "AI Zones", "Terrain"]