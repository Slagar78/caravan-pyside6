import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QMdiSubWindow, QLabel, QPushButton, QTextEdit, QListWidget, QListWidgetItem,
    QStyleFactory, QFrame
)
from PySide6.QtCore import Qt, QTimer, QEvent, QSize
from PySide6.QtGui import (
    QPainter, QPixmap, QImage, QColor, QPen, QBrush, QMouseEvent,
    QFont
)
import util
import shiboken6

# ------------------ ROMFrame ------------------
class ROMFrame(QMdiSubWindow):
    def __init__(self, parent, id, rpc, *args, **kwargs):
        super().__init__(parent)
        self.parent = parent
        self.outerPanel = QWidget()
        self.outerPanel.parent = parent
        self.outerPanel.setLayout(QVBoxLayout())
        self.outerPanel.layout().setContentsMargins(0, 0, 0, 0)
        self.setWidget(self.outerPanel)
        self.setWindowTitle(rpc.frameTitle)
        self.contentPanel = rpc(self.outerPanel, id, self.parent.rom)
        self.contentPanel.updateModifiedIndicator(False)
        self.outerPanel.layout().addWidget(self.contentPanel)
        if not self.contentPanel.canMaximize:
            self.setMaximumSize(self.sizeHint())

    def OnClose(self, event):
        if self in self.parent.frames:
            self.parent.frames.remove(self)
        super().closeEvent(event)


# ------------------ ROMPanel ------------------
class ROMPanel(QWidget):
    frameTitle = "Editor"
    canMaximize = False

    def __init__(self, parent, id, rom, **kwargs):
        super().__init__(parent)
        self.parent = parent.parent if hasattr(parent, 'parent') else parent
        self.rom = rom
        self.sizer = QGridLayout()
        self.sizer.setHorizontalSpacing(4)
        self.sizer.setVerticalSpacing(4)
        self.setLayout(self.sizer)
        self.hide()
        self.init()
        self.show()

    def showEvent(self, event):
        super().showEvent(event)
        self.OnShow()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.OnHide(event)

    def init(self):
        pass

    def modify(self, obj=None):
        if not obj:
            obj = self.getCurrentData()
        obj.modified = True
        self.modified = True
        self.parent.modify()

    def commit(self, action):
        us = self.parent.tempUndoStack
        rs = self.parent.tempRedoStack
        if self not in us:
            us[self] = []
        us[self].append(action)
        if self in rs:
            rs[self] = []

    def updateModifiedIndicator(self, val):
        pass

    def OnShow(self, event=None):
        pass

    def OnHide(self, event):
        pass

    def changeEditColor(self, button, num):
        pass

    def getCurrentData(self):
        return None


# ------------------ HexBox, HexListBox ------------------
class HexBox(QTextEdit):
    def __init__(self, parent, id, **kwargs):
        super().__init__(parent)
        self.setFont(QFont("Courier New", 12, QFont.Bold))
        self.setStyleSheet("color: #B0B0B0;")
        self.setReadOnly(True)


class HexListBox(QListWidget):
    def __init__(self, parent, id, **kwargs):
        super().__init__(parent)
        self.setFont(QFont("Courier New", 12, QFont.Bold))
        self.setStyleSheet("color: #B0B0B0;")

    def SetContents(self, text):
        self.clear()
        t2s = lambda t: util.tabs2spaces(t, 8)
        for line in text.splitlines():
            self.addItem(QListWidgetItem(t2s(line)))


# ------------------ ColorPanel, ColorPanel2 ------------------
class ColorPanel(QFrame):
    def __init__(self, parent, id, color, size=(20, 20), num=None, enable=True):
        super().__init__(parent)
        self.color = color
        self.num = num
        self.setFixedSize(QSize(*size))
        self.setStyleSheet(f"background-color: {color};")
        if enable:
            self.mousePressEvent = self.OnClick

    def OnClick(self, event):
        if event.button() == Qt.LeftButton:
            p = self.parent()
            while p and not hasattr(p, 'changeEditColor'):
                p = p.parent()
            if p:
                p.changeEditColor(0, self.num)


class ColorPanel2(QFrame):
    def __init__(self, parent, id, color, size=(20, 20), num=None, enable=True):
        super().__init__(parent)
        self.color = color
        self.num = num
        self.setFixedSize(QSize(*size))
        self.setStyleSheet(f"background-color: {color};")
        if enable:
            self.mousePressEvent = self.OnClick

    def OnClick(self, event):
        p = self.parent()
        while p and not hasattr(p, 'changeEditColor'):
            p = p.parent()
        if p:
            if event.button() == Qt.LeftButton:
                p.changeEditColor(0, self.num)
            elif event.button() == Qt.RightButton:
                p.changeEditColor(1, self.num)


# ------------------ SpritePanel (виджет отображения спрайта) ------------------
class SpritePanel(QWidget):
    alphaPixmap = None
    selectBrush = None
    selectBrush2 = None
    selectBrush3 = None
    magentaBrush = None
    transPen = None
    transBrush = None
    gridPen = None

    obsPen = None
    zonePen = None
    eventPen = None
    stairsPen = None
    chestPen = None
    barrelPen = None
    vasePen = None
    floorPen = None
    tablePen = None
    roofPen1 = None
    roofPen2 = None
    roofPen3 = None
    otherPen = None
    eventCoordPen = None
    warpCoordPen = None
    copySrcPen = None
    copyDestPen = None
    darkBGBrush = None

    @classmethod
    def _initStatic(cls):
        if cls.alphaPixmap is None:
            cls.alphaPixmap = QPixmap("alpha.png")
            cls.selectBrush = QBrush(QColor(0, 0, 128))
            cls.selectBrush2 = QBrush(QColor(0, 128, 0))
            cls.selectBrush3 = QBrush(QColor(192, 192, 192))
            cls.magentaBrush = QBrush(QColor(255, 0, 255))
            cls.transPen = QPen(Qt.NoPen)
            cls.transBrush = QBrush(Qt.NoBrush)
            cls.gridPen = QPen(QColor(0, 0, 0, 128), 1)

            thinW = 3
            thickW = 5
            cls.obsPen = QPen(QColor(255, 0, 0), thinW)
            cls.zonePen = QPen(QColor(0, 0, 255), thinW)
            cls.eventPen = QPen(QColor(0, 255, 0), thinW)
            cls.stairsPen = QPen(QColor(0, 255, 255), thinW)
            cls.chestPen = QPen(QColor(255, 255, 0), thickW)
            cls.barrelPen = QPen(QColor(255, 128, 64), thickW)
            cls.vasePen = QPen(QColor(224, 224, 255), thickW)
            cls.floorPen = QPen(QColor(0, 255, 0), thickW)
            cls.tablePen = QPen(QColor(255, 255, 255), thinW)
            cls.roofPen1 = QPen(QColor(255, 255, 255), thinW)
            cls.roofPen2 = QPen(QColor(128, 128, 128), thinW)
            cls.roofPen3 = QPen(QColor(255, 128, 128), thinW)
            cls.otherPen = QPen(QColor(255, 255, 0), thinW)
            cls.eventCoordPen = QPen(QColor(255, 255, 0), thickW)
            cls.warpCoordPen = QPen(QColor(255, 128, 0), thickW)
            cls.copySrcPen = QPen(QColor(0, 255, 255), thickW)
            cls.copyDestPen = QPen(QColor(192, 192, 192), thickW)
            cls.darkBGBrush = QBrush(QColor(32, 32, 32))

    def __init__(self, parent, id, width, height, palette, pixels=None, scale=1,
                 edit=False, bg=15, xpad=0, ypad=0, func=None, grid=False, draw=None, **kwargs):
        super().__init__(parent)
        self._initStatic()

        self.width = width
        self.height = height
        self.xpad = xpad
        self.ypad = ypad
        self.palette = palette
        self.pixels = pixels if pixels is not None else []
        self.scale = scale
        self.bg = bg
        self.buffer = None
        self.func = func
        self.grid = grid
        self.drawFunc = draw
        self.flip = False

        self.pixelsStack = []
        self.bmpStack = []

        if self.__class__.__name__ == 'MapViewPanel':
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16777215, 16777215)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        else:
            self.setFixedSize(int(width * scale + xpad * 2), int(height * scale + ypad * 2))
        
        self.setAttribute(Qt.WA_OpaquePaintEvent, False)

        self.refreshSprite(self.pixels)

        if func == "edit":
            self.setMouseTracking(True)
            self.mousePressEvent = self.OnEdit
            self.mouseMoveEvent = self.OnEdit
            self.mouseReleaseEvent = self.OnEdit
        elif edit:
            self.setMouseTracking(True)
            self.mouseX = 0
            self.mouseY = 0
            self.lastButton = Qt.NoButton
            self.shift = False
            self.ctrl = False
            self.func = func
            self.mousePressEvent = self._onEditMouse
            self.mouseMoveEvent = self._onEditMouse
            self.mouseReleaseEvent = self._onEditMouse
        else:
            self.mousePressEvent = func if func is not None else lambda event: None
            self.setCursor(Qt.PointingHandCursor)

    def refreshSprite(self, pixels=None, force=False):
        if not shiboken6.isValid(self):
            return
        if self.palette is None:
            return
        rt = self.palette.rgbaTuples()
        if pixels is not None:
            self.pixels = pixels
        if self.flip:
            self.pixels = [p[::-1] for p in self.pixels]

        if force:
            self.pixelsStack.clear()
            self.bmpStack.clear()

        if self.pixels not in self.pixelsStack:
            buf = b""
            for row in self.pixels:
                for p in row:
                    for t in rt[int(p, 16)]:
                        buf += bytes([t])
            extra = max(0, self.width * self.height * 4 - len(buf))
            buf += b'\x00' * extra
            image = QImage(buf, self.width, self.height, QImage.Format_RGBA8888)
            self.bmp = QPixmap.fromImage(image)
            self.pixelsStack.append(self.pixels[:])
            self.bmpStack.append(self.bmp)
        else:
            self.bmp = self.bmpStack[self.pixelsStack.index(self.pixels)]
        self.update()
        
    def _onEditMouse(self, event):
        self.mouseX = event.pos().x()
        self.mouseY = event.pos().y()
        self.lastButton = event.button()
        self.shift = bool(event.modifiers() & Qt.ShiftModifier)
        self.ctrl = bool(event.modifiers() & Qt.ControlModifier)
        if event.type() == QEvent.MouseButtonPress and self.func:
            self.func(self)

    def paintEvent(self, event):
        painter = QPainter(self)
        s = self.scale
        w = int(self.width * s + self.xpad * 2)
        h = int(self.height * s + self.ypad * 2)
        if self.bg == 16:
            painter.fillRect(0, 0, w, h, QBrush(self.alphaPixmap.scaled(w, h)))
        elif self.bg == 17:
            painter.fillRect(0, 0, w, h, self.selectBrush)
        elif self.bg == 18:
            painter.fillRect(0, 0, w, h, self.selectBrush2)
        elif self.bg == 19:
            painter.fillRect(0, 0, w, h, self.selectBrush3)
        elif self.bg == 20:
            painter.fillRect(0, 0, w, h, self.magentaBrush)
        elif self.bg is not None:
            painter.fillRect(0, 0, w, h, QColor(self.palette.colors[self.bg]))
        painter.scale(s, s)
        painter.drawPixmap(self.xpad // 2, self.ypad // 2, self.bmp)
        if self.drawFunc:
            painter.resetTransform()
            self.drawFunc(self, painter)
        if self.grid:
            painter.resetTransform()
            painter.setPen(self.gridPen)
            painter.setBrush(Qt.NoBrush)
            gs = int(self.grid * s)
            for y in range(0, h, gs):
                for x in range(0, w, gs):
                    painter.drawRect(x - 1, y - 1, gs + 1, gs + 1)
        painter.end()

    def OnEdit(self, event):
        if isinstance(event, QMouseEvent):
            if event.buttons() & (Qt.LeftButton | Qt.RightButton):
                # Ищем настоящую панель редактора (с атрибутом color_left)
                parent = self
                while parent is not None and not hasattr(parent, 'color_left'):
                    parent = parent.parent()
                if parent is None:
                    return

                color1 = parent.color_left
                color2 = parent.color_right
                x = int(event.pos().x() // self.scale)
                y = int(event.pos().y() // self.scale)

                if x < 0 or x >= self.width or y < 0 or y >= self.height:
                    return

                spr = parent.getCurrentSpriteObject()
                oldpix = spr.raw_pixels[:] if hasattr(spr, 'raw_pixels') else ""
                oldpix2 = spr.raw_pixels2[:] if (hasattr(spr, 'raw_pixels2') and hasattr(parent, 'frame')) else ""

                if event.modifiers() & Qt.ShiftModifier:
                    col = int(self.pixels[y][x], 16)
                    if event.buttons() & Qt.LeftButton:
                        parent.color_left = col
                    else:
                        parent.color_right = col
                    # Обновляем индикаторы выбранных цветов
                    if hasattr(parent, 'selectedColorLeft'):
                        parent.selectedColorLeft.color = col
                        parent.selectedColorLeft.setStyleSheet(f"background-color: {parent.palette.colors[col]};")
                    if hasattr(parent, 'selectedColorRight'):
                        parent.selectedColorRight.color = col
                        parent.selectedColorRight.setStyleSheet(f"background-color: {parent.palette.colors[col]};")
                elif parent.mode == 0:  # Пиксель
                    col = hex(color1 if event.buttons() & Qt.LeftButton else color2)[2:]
                    if self.pixels[y][x] != col:
                        self.pixels[y] = self.pixels[y][:x] + col + self.pixels[y][x+1:]
                        parent.modify()
                        # Обновляем сырые данные
                        raw = spr.convertFromPixelRows(self.pixels) if hasattr(spr, 'convertFromPixelRows') else None
                        if raw is not None:
                            if not hasattr(parent, 'frame') or parent.frame == 0:
                                spr.raw_pixels = raw
                            else:
                                spr.raw_pixels2 = raw
                        self.refreshSprite()
                        self.update()
                        parent.refreshPixels()
                elif parent.mode == 1:  # Заливка
                    col = hex(color1 if event.buttons() & Qt.LeftButton else color2)[2:]
                    target = self.pixels[y][x]
                    queue = [(x, y)]
                    visited = set()
                    w = self.width
                    h = self.height
                    while queue:
                        cx, cy = queue.pop(0)
                        if (cx, cy) in visited:
                            continue
                        if cx < 0 or cx >= w or cy < 0 or cy >= h:
                            continue
                        if self.pixels[cy][cx] != target:
                            continue
                        visited.add((cx, cy))
                        self.pixels[cy] = self.pixels[cy][:cx] + col + self.pixels[cy][cx+1:]
                        queue.extend([(cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)])
                    parent.modify()
                    raw = spr.convertFromPixelRows(self.pixels) if hasattr(spr, 'convertFromPixelRows') else None
                    if raw is not None:
                        if not hasattr(parent, 'frame') or parent.frame == 0:
                            spr.raw_pixels = raw
                        else:
                            spr.raw_pixels2 = raw
                    self.refreshSprite()
                    self.update()
                    parent.refreshPixels()
                elif parent.mode == 2:  # Замена
                    col = hex(color1 if event.buttons() & Qt.LeftButton else color2)[2:]
                    repl = self.pixels[y][x]
                    if repl != col:
                        for i in range(len(self.pixels)):
                            self.pixels[i] = self.pixels[i].replace(repl, col)
                        parent.modify()
                        frame = 0 if not hasattr(parent, 'frame') or parent.frame == 0 else 1
                        if frame == 0:
                            spr.raw_pixels = spr.raw_pixels.replace(repl, col)
                        else:
                            spr.raw_pixels2 = spr.raw_pixels2.replace(repl, col)
                        self.refreshSprite()
                        self.update()
                        parent.refreshPixels()

                # Undo/Redo
                if hasattr(spr, 'raw_pixels') and (oldpix != spr.raw_pixels or (hasattr(parent, 'frame') and oldpix2 != spr.raw_pixels2)):
                    if not hasattr(parent, 'frame'):
                        parent.commit([[oldpix], [spr.raw_pixels[:]]])
                    else:
                        parent.commit([[oldpix, oldpix2], [spr.raw_pixels[:], spr.raw_pixels2[:]]])


# ------------------ MapViewPanel ------------------
class MapViewPanel(QWidget):
    def __init__(self, parent, id, width, height, palette, pixels=None, scale=1,
                 edit=False, bg=15, xpad=0, ypad=0, func=None, grid=False, draw=None, **kwargs):
        super().__init__(parent)
        SpritePanel._initStatic()

        self.width = width
        self.height = height
        self.xpad = xpad
        self.ypad = ypad
        self.palette = palette
        self.pixels = pixels if pixels is not None else []
        self.scale = scale
        self.bg = bg
        self.buffer = None
        self.func = func
        self.grid = grid
        self.drawFunc = draw

        self.drawBlocks = True
        self.drawFlags = True

        self.curViewX = 0
        self.curViewY = 0

        self.setAttribute(Qt.WA_OpaquePaintEvent, False)

        if func == "edit":
            self.setMouseTracking(True)
            self.mousePressEvent = self.OnEdit
            self.mouseMoveEvent = self.OnEdit
            self.mouseReleaseEvent = self.OnEdit
        elif edit:
            self.setMouseTracking(True)
            self.func = func
            self.mouseX = 0
            self.mouseY = 0
            self.lastButton = Qt.NoButton
            self.shift = False
            self.ctrl = False
            self.mousePressEvent = self._onEditMouse
            self.mouseMoveEvent = self._onEditMouse
            self.mouseReleaseEvent = self._onEditMouse
        else:
            self.mousePressEvent = func

    def changeMap(self, map, palette):
        self.map = map
        self.palette = palette
        self.blockBMPs = []
        self.updateBlockBMPs()

    def updateBlockBMPs(self, idx=None):
        if idx is not None:
            redo = [idx]
        else:
            redo = range(len(self.map.blocks))
        if not self.blockBMPs:
            self.blockBMPs = [None] * len(self.map.blocks)
        rt = self.palette.rgbaTuples()
        for i in redo:
            blk = self.map.blocks[i]
            buf = b""
            for row in blk.pixels:
                for p in row:
                    for t in rt[int(p, 16)]:
                        buf += bytes([t])
            image = QImage(buf, 24, 24, QImage.Format_RGBA8888)
            self.blockBMPs[i] = QPixmap.fromImage(image)
        self.update()

    def _onEditMouse(self, event):
        self.mouseX = event.pos().x()
        self.mouseY = event.pos().y()
        self.lastButton = event.button()
        self.shift = bool(event.modifiers() & Qt.ShiftModifier)
        self.ctrl = bool(event.modifiers() & Qt.ControlModifier)
        if event.type() == QEvent.MouseButtonPress and self.func:
            self.func(self)

    def paintEvent(self, event):
        painter = QPainter(self)
        s = self.scale
        w = self.size().width()
        h = self.size().height()
        blockW = int(24 * s)
        blockH = int(24 * s)

        if self.bg == 16:
            painter.fillRect(0, 0, w, h, QBrush(SpritePanel.alphaPixmap.scaled(w, h)))
        elif self.bg is not None:
            painter.fillRect(0, 0, w, h, QColor(self.palette.colors[self.bg]))

        painter.scale(s, s)
        tWidth = w // blockW + 2
        tHeight = h // blockH + 2
        tViewX = int(self.curViewX) // 24
        tViewY = int(self.curViewY) // 24
        xofs = self.curViewX % 24
        yofs = self.curViewY % 24

        if self.drawBlocks:
            for y in range(tHeight):
                for x in range(tWidth):
                    if tViewX + x < 64 and tViewY + y < 64:
                        idx = (tViewY + y) * 64 + (tViewX + x)
                        blk_idx = self.map.layoutData[idx] & 0x3ff
                        bmp = self.blockBMPs[blk_idx]
                        painter.drawPixmap(x * 24 - xofs, y * 24 - yofs, bmp)
        else:
            painter.setBrush(SpritePanel.darkBGBrush)
            painter.setPen(Qt.NoPen)
            for y in range(tHeight):
                for x in range(tWidth):
                    if tViewX + x < 64 and tViewY + y < 64:
                        painter.drawRect(x * 24 - xofs, y * 24 - yofs, 24, 24)

        if self.drawFlags:
            painter.setBrush(Qt.NoBrush)
            for y in range(tHeight):
                for x in range(tWidth):
                    if tViewX + x < 64 and tViewY + y < 64:
                        idx = (tViewY + y) * 64 + (tViewX + x)
                        blk = self.map.layoutData[idx]
                        flags = blk & 0xfc00
                        if flags:
                            px = x * 24 - xofs
                            py = y * 24 - yofs
                            obs = flags & 0xc000
                            evt = flags & 0x3c00
                            if obs == 0xc000:
                                painter.setPen(SpritePanel.obsPen)
                                painter.drawLine(px + 4, py + 4, px + 20, py + 20)
                                painter.drawLine(px + 20, py + 4, px + 4, py + 20)
                            elif obs == 0x8000:
                                painter.setPen(SpritePanel.stairsPen)
                                painter.drawLine(px + 20, py + 4, px + 4, py + 20)
                            elif obs == 0x4000:
                                painter.setPen(SpritePanel.stairsPen)
                                painter.drawLine(px + 4, py + 4, px + 20, py + 20)
                            elif evt == 0x1000:
                                painter.setPen(SpritePanel.zonePen)
                                painter.drawRect(px + 4, py + 4, 16, 16)
                            elif evt == 0x1400:
                                painter.setPen(SpritePanel.eventPen)
                                painter.drawRect(px + 4, py + 4, 16, 16)
                            elif evt == 0x1800:
                                painter.setPen(SpritePanel.chestPen)
                                painter.drawEllipse(px + 4, py + 4, 16, 16)
                            elif evt == 0x1c00:
                                painter.setPen(SpritePanel.floorPen)
                                painter.drawEllipse(px + 4, py + 4, 16, 16)
                            elif evt == 0x2c00:
                                painter.setPen(SpritePanel.vasePen)
                                painter.drawEllipse(px + 4, py + 4, 16, 16)
                            elif evt == 0x3000:
                                painter.setPen(SpritePanel.barrelPen)
                                painter.drawEllipse(px + 4, py + 4, 16, 16)
                            elif evt == 0x2800:
                                painter.setPen(SpritePanel.tablePen)
                                painter.drawLine(px + 4, py + 12, px + 20, py + 12)
                                painter.drawLine(px + 12, py + 4, px + 12, py + 20)
                            elif evt == 0x0800:
                                painter.setPen(SpritePanel.roofPen1)
                                painter.drawEllipse(px + 4, py + 4, 16, 16)
                            elif evt == 0x0c00:
                                painter.setPen(SpritePanel.roofPen2)
                                painter.drawEllipse(px + 4, py + 4, 16, 16)
                            elif evt == 0x0400:
                                painter.setPen(SpritePanel.roofPen3)
                                painter.drawEllipse(px + 4, py + 4, 16, 16)
                            else:
                                if obs == 0 and evt == 0:
                                    painter.setPen(SpritePanel.otherPen)
                                    painter.drawEllipse(px + 4, py + 4, 16, 16)

        painter.resetTransform()
        if self.grid:
            painter.setPen(SpritePanel.gridPen)
            painter.setBrush(Qt.NoBrush)
            for y in range(tHeight):
                for x in range(tWidth):
                    px = int(x * blockW - xofs * s)
                    py = int(y * blockH - yofs * s)
                    painter.drawRect(px, py, blockW, blockH)

        if self.drawFunc:
            painter.scale(s, s)
            self.drawFunc(painter, tViewX, tViewY, xofs, yofs)

        painter.end()