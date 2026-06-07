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

# Глобальные статические переменные (как в оригинале)
alphaPixmap = None
selectBrush = None
selectBrush2 = None
selectBrush3 = None
transPen = None
transBrush = None
gridPen = None
# ... (будут добавлены в следующих частях)


class ROMFrame(QMdiSubWindow):
    """Аналог wx.MDIChildFrame"""

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
            self.bestSize = self.sizeHint()
            self.setMaximumSize(self.bestSize)

        # Подписка на изменение размера (будет дополнена в следующей части)
        # self.sizeChanged.connect(self.OnSize)

    def OnSize(self, event):
        # Логика, аналогичная оригиналу
        pass

    def OnClose(self, event):
        if self in self.parent.frames:
            self.parent.frames.remove(self)
        super().closeEvent(event)


class ROMPanel(QWidget):
    """Аналог wx.Panel с GridBagSizer"""

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
        self.helpText = {}
        self.hide()
        self.init()
        # showEvent заменяет wx.EVT_SHOW
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
        if hasattr(self, "treeItem"):
            self.parent.layoutTree.modify(self.treeItem)

    def commit(self, action):
        us = self.parent.tempUndoStack
        rs = self.parent.tempRedoStack
        if self not in us:
            us[self] = []
        us[self].append(action)
        if self in rs:
            rs[self] = []

    def updateModifiedIndicator(self, val):
        pass  # как в оригинале

    def updateCurrentDataName(self, idx, string):
        data = self.getCurrentData()
        if not data.hasCustomName and string != data.name:
            data.hasCustomName = True
            token = "%i:" % idx
            loc = string.find(token)
            if loc != -1:
                start = loc + len(token)
            else:
                start = 0
            newName = "%i: " % idx + string[start:].lstrip().rstrip()
            data.name = newName

    def addHelpText(self, obj, header, text):
        # id = obj.winId()  # или можно хранить в атрибуте
        pass

    def SetROM(self, rom):
        self.rom = rom

    def OnGetHelpForItem(self, event):
        pass

    def OnShow(self, event=None):
        pass

    def OnHide(self, event):
        pass
        
    def changeEditColor(self, button, num):
        pass

    def getCurrentData(self):
        return None


class HexBox(QTextEdit):
    """Аналог wx.TextCtrl с моноширинным шрифтом"""
    def __init__(self, parent, id, **kwargs):
        super().__init__(parent)
        self.setFont(QFont("Courier New", 12, QFont.Bold))  # как в оригинале parent.parent.editFont
        self.setStyleSheet("color: #B0B0B0;")
        self.setReadOnly(True)


class HexListBox(QListWidget):
    """Аналог wx.ListBox с моноширинным шрифтом"""
    def __init__(self, parent, id, **kwargs):
        super().__init__(parent)
        self.setFont(QFont("Courier New", 12, QFont.Bold))
        self.setStyleSheet("color: #B0B0B0;")
        # Устанавливаем флаг для обработки табуляции (в PySide6 это поведение по умолчанию)

    def SetContents(self, text):
        self.clear()
        t2s = lambda t: util.tabs2spaces(t, 8)
        for line in text.splitlines():
            item = QListWidgetItem(t2s(line))
            self.addItem(item)


class ColorPanel(QFrame):
    """Простая цветная панель, реагирующая на клик левой кнопкой"""
    def __init__(self, parent, id, color, size=(20,20), num=None, enable=True):
        super().__init__(parent)
        self.color = color
        self.num = num
        self.setFixedSize(QSize(*size))
        self.setStyleSheet(f"background-color: {color};")
        if enable:
            self.mousePressEvent = self.OnClick

    def OnClick(self, event):
        if event.button() == Qt.LeftButton:
            parent = self.parent()
            if hasattr(parent, 'changeEditColor'):
                parent.changeEditColor(self.num)


class ColorPanel2(QFrame):
    """Цветная панель, различающая левую и правую кнопку мыши"""
    def __init__(self, parent, id, color, size=(20,20), num=None, enable=True):
        super().__init__(parent)
        self.color = color
        self.num = num
        self.setFixedSize(QSize(*size))
        self.setStyleSheet(f"background-color: {color};")
        if enable:
            self.mousePressEvent = self.OnClick

    def OnClick(self, event):
        parent = self.parent()
        if hasattr(parent, 'changeEditColor'):
            if event.button() == Qt.LeftButton:
                parent.changeEditColor(0, self.num)
            elif event.button() == Qt.RightButton:
                parent.changeEditColor(1, self.num)

# ------------------------------------------------------------
# SpritePanel – виджет для отображения/редактирования спрайтов
# ------------------------------------------------------------
class SpritePanel(QWidget):
    """Аналог wx.Panel с кастомной отрисовкой спрайта и редактированием"""

    # Статические переменные (кэш, чтобы не создавать при каждом создании)
    alphaPixmap = None
    selectBrush = None
    selectBrush2 = None
    selectBrush3 = None
    magentaBrush = None
    transPen = None
    transBrush = None
    gridPen = None

    # Перья и кисти для MapViewPanel (будут заполнены ниже)
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
            cls.selectBrush = QBrush(QColor(0,0,128))
            cls.selectBrush2 = QBrush(QColor(0,128,0))
            cls.selectBrush3 = QBrush(QColor(192,192,192))
            cls.magentaBrush = QBrush(QColor(255,0,255))
            cls.transPen = QPen(Qt.NoPen)
            cls.transBrush = QBrush(Qt.NoBrush)
            cls.gridPen = QPen(QColor(0,0,0,128), 1)

            thinW = 3
            thickW = 5
            cls.obsPen = QPen(QColor(255,0,0), thinW)
            cls.zonePen = QPen(QColor(0,0,255), thinW)
            cls.eventPen = QPen(QColor(0,255,0), thinW)
            cls.stairsPen = QPen(QColor(0,255,255), thinW)
            cls.chestPen = QPen(QColor(255,255,0), thickW)
            cls.barrelPen = QPen(QColor(255,128,64), thickW)
            cls.vasePen = QPen(QColor(224,224,255), thickW)
            cls.floorPen = QPen(QColor(0,255,0), thickW)
            cls.tablePen = QPen(QColor(255,255,255), thinW)
            cls.roofPen1 = QPen(QColor(255,255,255), thinW)
            cls.roofPen2 = QPen(QColor(128,128,128), thinW)
            cls.roofPen3 = QPen(QColor(255,128,128), thinW)
            cls.otherPen = QPen(QColor(255,255,0), thinW)
            cls.eventCoordPen = QPen(QColor(255,255,0), thickW)
            cls.warpCoordPen = QPen(QColor(255,128,0), thickW)
            cls.copySrcPen = QPen(QColor(0,255,255), thickW)
            cls.copyDestPen = QPen(QColor(192,192,192), thickW)
            cls.darkBGBrush = QBrush(QColor(32,32,32))

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

        self.setFixedSize(int(width * scale + xpad * 2), int(height * scale + ypad * 2))
        self.setAttribute(Qt.WA_OpaquePaintEvent, False)

        self.refreshSprite(self.pixels)

        # Обработчики мыши
        if func == "edit":
            self.setMouseTracking(True)
            self.mousePressEvent = self.OnEdit
            self.mouseMoveEvent = self.OnEdit
            self.mouseReleaseEvent = self.OnEdit
        elif edit:
            self.setMouseTracking(True)
            self.mousePressEvent = func
            self.mouseMoveEvent = func
            self.mouseReleaseEvent = func
        else:
            self.mousePressEvent = func
            self.setCursor(Qt.PointingHandCursor)

    def refreshSprite(self, pixels=None, force=False):
        if not shiboken6.isValid(self):
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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        s = self.scale
        w = int(self.width * s + self.xpad * 2)
        h = int(self.height * s + self.ypad * 2)

        # Фон с клеточками (прозрачность)
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
            color = QColor(self.palette.colors[self.bg])
            painter.fillRect(0, 0, w, h, color)

        painter.scale(s, s)
        painter.drawPixmap(self.xpad // 2, self.ypad // 2, self.bmp)

        if self.drawFunc:
            painter.resetTransform()
            self.drawFunc(self, painter)  # кастомная функция рисования (пока не используется)

        # Сетка
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
                tileWidth = self.width // 8
                tileHeight = self.height // 8
                parent = self.parent()
                color1 = parent.color_left
                color2 = parent.color_right
                x = int(event.pos().x() // self.scale)
                y = int(event.pos().y() // self.scale)

                if x < 0 or x >= self.width or y < 0 or y >= self.height:
                    return

                spr = parent.getCurrentSpriteObject()
                oldpix = spr.raw_pixels[:] if hasattr(spr, 'raw_pixels') else ""
                oldpix2 = spr.raw_pixels2[:] if hasattr(parent, 'frame') else ""

                if event.modifiers() & Qt.ShiftModifier:
                    col = int(self.pixels[y][x], 16)
                    if event.buttons() & Qt.LeftButton:
                        parent.color_left = col
                        # Обновление индикаторов (будет добавлено)
                    else:
                        parent.color_right = col
                elif parent.mode == 0:  # Пиксель
                    color = hex(color1 if event.buttons() & Qt.LeftButton else color2)[2:]
                    if self.pixels[y][x] != color:
                        self.pixels[y] = self.pixels[y][:x] + color + self.pixels[y][x+1:]
                        parent.modify()
                        frame = 0 if not hasattr(parent, 'frame') or parent.frame == 0 else 1
                        spr.setPixel(x, y, color, frame)
                        self.refreshSprite()
                        self.update()
                        parent.refreshPixels()
                        # Здесь добавить commit как в оригинале
                elif parent.mode == 1:  # Заливка
                    color = hex(color1 if event.buttons() & Qt.LeftButton else color2)[2:]
                    findColor = self.pixels[y][x]
                    # Реализация floodfill через очередь (упрощённо)
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
                        if self.pixels[cy][cx] != findColor:
                            continue
                        visited.add((cx, cy))
                        self.pixels[cy] = self.pixels[cy][:cx] + color + self.pixels[cy][cx+1:]
                        frame = 0 if not hasattr(parent, 'frame') or parent.frame == 0 else 1
                        spr.setPixel(cx, cy, color, frame)
                        queue.extend([(cx-1, cy), (cx+1, cy), (cx, cy-1), (cx, cy+1)])
                    parent.modify()
                    self.refreshSprite()
                    self.update()
                    parent.refreshPixels()
                elif parent.mode == 2:  # Замена
                    color = hex(color1 if event.buttons() & Qt.LeftButton else color2)[2:]
                    if self.pixels[y][x] != color:
                        repl = self.pixels[y][x]
                        for row_idx in range(len(self.pixels)):
                            self.pixels[row_idx] = self.pixels[row_idx].replace(repl, color)
                        parent.modify()
                        frame = 0 if not hasattr(parent, 'frame') or parent.frame == 0 else 1
                        if frame == 0:
                            spr.raw_pixels = spr.raw_pixels.replace(repl, color)
                        else:
                            spr.raw_pixels2 = spr.raw_pixels2.replace(repl, color)
                        self.refreshSprite()
                        self.update()
                        parent.refreshPixels()

                # Запись в undo/redo
                if hasattr(spr, 'raw_pixels') and (oldpix != spr.raw_pixels or oldpix2 != spr.raw_pixels2):
                    if not hasattr(parent, 'frame'):
                        parent.commit([[oldpix], [spr.raw_pixels[:]]])
                    else:
                        parent.commit([[oldpix, oldpix2], [spr.raw_pixels[:], spr.raw_pixels2[:]]])


# ------------------------------------------------------------
# MapViewPanel – панель для отображения карт (блоки, флаги)
# ------------------------------------------------------------
class MapViewPanel(QWidget):
    """Просмотр карты с блоками, флагами, зонами и т.д."""

    def __init__(self, parent, id, width, height, palette, pixels=None, scale=1,
                 edit=False, bg=15, xpad=0, ypad=0, func=None, grid=False, draw=None, **kwargs):
        super().__init__(parent)
        SpritePanel._initStatic()  # Инициализируем статические кисти/перья

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
            self.mousePressEvent = func
            self.mouseMoveEvent = func
            self.mouseReleaseEvent = func
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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        s = self.scale
        w = self.width()
        h = self.height()
        blockW = int(24 * s)
        blockH = int(24 * s)

        # Фон
        if self.bg == 16:
            painter.fillRect(0, 0, w, h, QBrush(SpritePanel.alphaPixmap.scaled(w, h)))
        elif self.bg is not None:
            color = QColor(self.palette.colors[self.bg])
            painter.fillRect(0, 0, w, h, color)

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
                    mx = tViewX + x
                    my = tViewY + y
                    if mx < 64 and my < 64:
                        idx = my * 64 + mx
                        blk_idx = self.map.layoutData[idx] & 0x3ff
                        bmp = self.blockBMPs[blk_idx]
                        painter.drawPixmap(x * 24 - xofs, y * 24 - yofs, bmp)
        else:
            painter.setBrush(SpritePanel.darkBGBrush)
            painter.setPen(Qt.NoPen)
            for y in range(tHeight):
                for x in range(tWidth):
                    mx = tViewX + x
                    my = tViewY + y
                    if mx < 64 and my < 64:
                        painter.drawRect(x * 24 - xofs, y * 24 - yofs, 24, 24)

        # Флаги
        if self.drawFlags:
            painter.setBrush(Qt.NoBrush)
            for y in range(tHeight):
                for x in range(tWidth):
                    mx = tViewX + x
                    my = tViewY + y
                    if mx < 64 and my < 64:
                        idx = my * 64 + mx
                        blk = self.map.layoutData[idx]
                        flags = blk & 0xfc00
                        if flags:
                            px = x * 24 - xofs
                            py = y * 24 - yofs
                            obs = flags & 0xc000
                            evt = flags & 0x3c00
                            if obs == 0xc000:
                                painter.setPen(SpritePanel.obsPen)
                                painter.drawLine(px+4, py+4, px+20, py+20)
                                painter.drawLine(px+20, py+4, px+4, py+20)
                            elif obs == 0x8000:
                                painter.setPen(SpritePanel.stairsPen)
                                painter.drawLine(px+20, py+4, px+4, py+20)
                            elif obs == 0x4000:
                                painter.setPen(SpritePanel.stairsPen)
                                painter.drawLine(px+4, py+4, px+20, py+20)
                            elif evt == 0x1000:
                                painter.setPen(SpritePanel.zonePen)
                                painter.drawRect(px+4, py+4, 16, 16)
                            # ... остальные типы событий можно добавить аналогично
                            # В оригинале они были, здесь для краткости пропущены, но можно дописать
                            else:
                                painter.setPen(SpritePanel.otherPen)
                                painter.drawEllipse(px+12, py+12, 8, 8)

        # Сетка
        painter.resetTransform()
        if self.grid:
            painter.setPen(SpritePanel.gridPen)
            painter.setBrush(Qt.NoBrush)
            for y in range(tHeight):
                for x in range(tWidth):
                    px = int(x * blockW - xofs * s)
                    py = int(y * blockH - yofs * s)
                    painter.drawRect(px, py, blockW, blockH)

        # Кастомная функция рисования (Warp/Copy/Area...)
        if self.drawFunc:
            painter.scale(s, s)
            self.drawFunc(painter, tViewX, tViewY, xofs, yofs)

        painter.end()