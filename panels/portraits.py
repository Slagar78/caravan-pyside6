import binascii
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QComboBox, QFileDialog, QMessageBox,
    QDialog, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QCheckBox, QHeaderView, QStyledItemDelegate, QSpinBox
)
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QPixmap, QImage, QColor, QPainter, QPen, QFont
import data
from PIL import Image
import rompanel
import shiboken6

h2i = lambda i: int(i, 16)

# =============================================================================
# CRAM color conversion (Sega Mega Drive) – точный аналог PaletteDecoder.java
# =============================================================================
CRAM_VALUE_MAP = {
    0: 0,
    2: 52,
    4: 87,
    6: 116,
    8: 144,
    10: 172,
    12: 206,
    14: 255
}

CRAM_OFFSET_ARRAY = [17, 63, 96, 125, 153, 183, 222, 999]

def brightness_to_cram_index(brightness):
    for cram, value in CRAM_VALUE_MAP.items():
        if brightness <= value:
            return cram
    return 0

def brightness_to_cram_value(brightness):
    for i, offset in enumerate(CRAM_OFFSET_ARRAY):
        if brightness <= offset:
            return CRAM_VALUE_MAP[i * 2]
    return 0

def cram_index_to_brightness(cram):
    return CRAM_VALUE_MAP.get(cram, 0)

def conform_color_to_cram(r, g, b):
    return brightness_to_cram_value(r), brightness_to_cram_value(g), brightness_to_cram_value(b)

# =============================================================================
# Парсер сырых eyeBytes/mouthBytes из ROM.py
# =============================================================================
def parse_anim_bytes(hex_str):
    if not hex_str or len(hex_str) < 4:
        return []
    num = int(hex_str[:4], 16)
    entries = []
    rest = hex_str[4:]
    for i in range(num):
        if (i+1)*8 > len(rest):
            break
        chunk = rest[i*8:(i+1)*8]
        x = int(chunk[0:2], 16)
        y = int(chunk[2:4], 16)
        xp = int(chunk[4:6], 16)
        yp = int(chunk[6:8], 16)
        entries.append([x, y, xp, yp])
    return entries

def pack_anim_bytes(entries):
    num = len(entries)
    header = f"{num:04x}"
    body = ""
    for e in entries:
        body += f"{e[0]:02x}{e[1]:02x}{e[2]:02x}{e[3]:02x}"
    return header + body

# =============================================================================
# Делегат со спин-боксами для таблиц анимации
# =============================================================================
class TileCoordDelegate(QStyledItemDelegate):
    def __init__(self, max_value=7, parent=None):
        super().__init__(parent)
        self.max_value = max_value

    def createEditor(self, parent, option, index):
        editor = QSpinBox(parent)
        editor.setRange(0, self.max_value)
        editor.setFrame(False)
        editor.setAlignment(Qt.AlignCenter)
        editor.setButtonSymbols(QSpinBox.UpDownArrows)
        editor.setMinimumWidth(30)
        return editor

    def setEditorData(self, editor, index):
        value = index.data(Qt.EditRole)
        if value is None:
            value = 0
        editor.setValue(int(value))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.value(), Qt.EditRole)
        model.setData(index, str(editor.value()), Qt.DisplayRole)

# =============================================================================
# Виджет для отображения портрета с сеткой и возможностью клика по тайлам
# =============================================================================
class PortraitTileWidget(QWidget):
    tileClicked = Signal(int, int)  # x, y – координаты тайла (0-7)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.portrait_pixmap = None
        self.eye_entries = []
        self.mouth_entries = []
        self.selected_eye_idx = -1
        self.selected_mouth_idx = -1
        self.tile_size = 8
        self.scale = 3
        self.setMinimumSize(64*3, 64*3)

    def setPixmap(self, pixmap):
        self.portrait_pixmap = pixmap
        self.update()

    def setAnimData(self, eye_entries, mouth_entries):
        self.eye_entries = eye_entries
        self.mouth_entries = mouth_entries
        self.update()

    def setSelectedEye(self, idx):
        self.selected_eye_idx = idx
        self.selected_mouth_idx = -1
        self.update()

    def setSelectedMouth(self, idx):
        self.selected_mouth_idx = idx
        self.selected_eye_idx = -1
        self.update()

    def paintEvent(self, event):
        if not self.portrait_pixmap:
            return
        painter = QPainter(self)
        scaled_size = 64 * self.scale
        painter.drawPixmap(0, 0, scaled_size, scaled_size, self.portrait_pixmap)
        # сетка
        pen = QPen(QColor(128, 128, 128, 100))
        painter.setPen(pen)
        for i in range(1, 8):
            painter.drawLine(i * 8 * self.scale, 0, i * 8 * self.scale, scaled_size)
            painter.drawLine(0, i * 8 * self.scale, scaled_size, i * 8 * self.scale)
        # выделение глаз
        if self.selected_eye_idx >= 0 and self.selected_eye_idx < len(self.eye_entries):
            item = self.eye_entries[self.selected_eye_idx]
            self._drawTileRect(painter, item[0], item[1], QColor(255, 255, 0))
            self._drawTileRect(painter, item[2], item[3], QColor(255, 255, 0))
        # выделение рта
        if self.selected_mouth_idx >= 0 and self.selected_mouth_idx < len(self.mouth_entries):
            item = self.mouth_entries[self.selected_mouth_idx]
            self._drawTileRect(painter, item[0], item[1], QColor(255, 200, 0))
            self._drawTileRect(painter, item[2], item[3], QColor(255, 200, 0))
        painter.end()

    def _drawTileRect(self, painter, tx, ty, color):
        pen = QPen(color, 2)
        painter.setPen(pen)
        x = tx * self.tile_size * self.scale
        y = ty * self.tile_size * self.scale
        w = self.tile_size * self.scale - 1
        h = self.tile_size * self.scale - 1
        painter.drawRect(x, y, w, h)

    def mousePressEvent(self, event):
        if not self.portrait_pixmap:
            return
        scaled_size = 64 * self.scale
        pos = event.pos()
        if pos.x() < 0 or pos.x() >= scaled_size or pos.y() < 0 or pos.y() >= scaled_size:
            return
        tile_x = pos.x() // (self.tile_size * self.scale)
        tile_y = pos.y() // (self.tile_size * self.scale)
        self.tileClicked.emit(tile_x, tile_y)

# =============================================================================
# Основная панель PortraitPanel с редактором анимации
# =============================================================================
class PortraitPanel(rompanel.ROMPanel):
    frameTitle = "Portrait Editor"

    def init(self):
        if self.rom is None:
            return

        self.palette = self.rom.getDataByName("palettes", "Sprite & UI Palette")
        self.side = 0
        self.frame = 0
        self.mode = 0
        self.color_left = 0
        self.color_right = 0
        self.curFrameIdx = 0
        self.curPaletteIdx = 0

        # ---------- Выбор портрета ----------
        sbs1 = QGroupBox("1. Select a portrait.")
        sbs1_layout = QVBoxLayout(sbs1)
        self.portraitList = QComboBox()
        self.portraitList.addItems([bs.name for bs in self.rom.data["portraits"]])
        self.portraitList.setCurrentIndex(0)
        self.portraitList.currentIndexChanged.connect(self.OnSelectPortrait)
        sbs1_layout.addWidget(self.portraitList)

        # ---------- Редактор портрета и таблицы анимации ----------
        sbs_main = QGroupBox("Edit")
        sbs_main_layout = QHBoxLayout(sbs_main)

        # Левая колонка: цвета и импорт/экспорт
        left_layout = QVBoxLayout()
        text_colors = QLabel("Colors")
        left_layout.addWidget(text_colors, alignment=Qt.AlignCenter)
        self.colorPanels = []
        for p in range(16):
            cp = rompanel.ColorPanel2(self, None, "#000000", num=p)
            self.colorPanels.append(cp)
        color_grid = QGridLayout()
        for i, cp in enumerate(self.colorPanels):
            color_grid.addWidget(cp, i // 2, i % 2)
        left_layout.addLayout(color_grid)
        self.importButton = QPushButton("Import")
        self.exportButton = QPushButton("Export")
        left_layout.addWidget(self.importButton, alignment=Qt.AlignCenter)
        left_layout.addWidget(self.exportButton, alignment=Qt.AlignCenter)
        sbs_main_layout.addLayout(left_layout, 0)

        # Центральная часть: портрет и под ним чекбоксы
        center_layout = QVBoxLayout()
        text_portrait = QLabel("Portrait (click to set tile for selected eye/mouth entry)")
        center_layout.addWidget(text_portrait, alignment=Qt.AlignCenter)
        self.portraitTileWidget = PortraitTileWidget()
        self.portraitTileWidget.tileClicked.connect(self.onTileClicked)
        center_layout.addWidget(self.portraitTileWidget, alignment=Qt.AlignCenter)
        # Чекбоксы прямо под портретом
        anim_layout = QHBoxLayout()
        self.blinkCheck = QCheckBox("Blink frame")
        self.talkCheck = QCheckBox("Talk frame")
        self.blinkCheck.toggled.connect(self.updatePreview)
        self.talkCheck.toggled.connect(self.updatePreview)
        anim_layout.addStretch()
        anim_layout.addWidget(self.blinkCheck)
        anim_layout.addWidget(self.talkCheck)
        anim_layout.addStretch()
        center_layout.addLayout(anim_layout)
        sbs_main_layout.addLayout(center_layout, 1)

        # Правая часть: таблицы глаз и рта
        right_layout = QVBoxLayout()

        # Таблица глаз
        eyes_label = QLabel("Eyes")
        right_layout.addWidget(eyes_label, alignment=Qt.AlignCenter)
        self.eyeTable = QTableWidget(0, 4)
        self.eyeTable.setHorizontalHeaderLabels(["X", "Y", "X'", "Y'"])
        self.eyeTable.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.eyeTable.setSelectionMode(QAbstractItemView.SingleSelection)
        self.eyeTable.setMinimumWidth(200)
        self.eyeTable.itemSelectionChanged.connect(self.onEyeSelectionChanged)
        self.eyeTable.cellChanged.connect(self.onEyeCellChanged)
        eye_delegate = TileCoordDelegate(max_value=7)
        for col in range(4):
            self.eyeTable.setItemDelegateForColumn(col, eye_delegate)
            self.eyeTable.setColumnWidth(col, 40)
        self.eyeTable.verticalHeader().setDefaultSectionSize(25)
        right_layout.addWidget(self.eyeTable)

        # Кнопки добавления/удаления для глаз
        eye_btn_layout = QHBoxLayout()
        self.addEyeBtn = QPushButton("Add")
        self.removeEyeBtn = QPushButton("Remove")
        self.addEyeBtn.clicked.connect(self.addEyeRow)
        self.removeEyeBtn.clicked.connect(self.removeEyeRow)
        eye_btn_layout.addStretch()
        eye_btn_layout.addWidget(self.addEyeBtn)
        eye_btn_layout.addWidget(self.removeEyeBtn)
        right_layout.addLayout(eye_btn_layout)

        # Таблица рта
        mouth_label = QLabel("Mouth")
        right_layout.addWidget(mouth_label, alignment=Qt.AlignCenter)
        self.mouthTable = QTableWidget(0, 4)
        self.mouthTable.setHorizontalHeaderLabels(["X", "Y", "X'", "Y'"])
        self.mouthTable.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.mouthTable.setSelectionMode(QAbstractItemView.SingleSelection)
        self.mouthTable.setMinimumWidth(200)
        self.mouthTable.itemSelectionChanged.connect(self.onMouthSelectionChanged)
        self.mouthTable.cellChanged.connect(self.onMouthCellChanged)
        mouth_delegate = TileCoordDelegate(max_value=7)
        for col in range(4):
            self.mouthTable.setItemDelegateForColumn(col, mouth_delegate)
            self.mouthTable.setColumnWidth(col, 40)
        self.mouthTable.verticalHeader().setDefaultSectionSize(25)
        right_layout.addWidget(self.mouthTable)

        # Кнопки добавления/удаления для рта
        mouth_btn_layout = QHBoxLayout()
        self.addMouthBtn = QPushButton("Add")
        self.removeMouthBtn = QPushButton("Remove")
        self.addMouthBtn.clicked.connect(self.addMouthRow)
        self.removeMouthBtn.clicked.connect(self.removeMouthRow)
        mouth_btn_layout.addStretch()
        mouth_btn_layout.addWidget(self.addMouthBtn)
        mouth_btn_layout.addWidget(self.removeMouthBtn)
        right_layout.addLayout(mouth_btn_layout)

        sbs_main_layout.addLayout(right_layout, 0)

        # ---------- Главный лейаут ----------
        self.sizer.addWidget(sbs1, 0, 0, 1, 2)
        self.sizer.addWidget(sbs_main, 1, 0, 1, 2)

        # Загрузка первого портрета
        self.changePortrait(0)

        # Сигналы
        self.importButton.clicked.connect(self.OnImportImage)
        self.exportButton.clicked.connect(self.OnExportImage)

    # ====== Методы работы с таблицами ======
    def addEyeRow(self):
        self.eye_data.append([0, 0, 6, 0])  # x=0,y=0 src; x'=6,y'=0 dst
        self.refreshTables()
        self.applyChanges()
        self.portraitTileWidget.setAnimData(self.eye_data, self.mouth_data)
        self.updatePreview()
        # Выделяем последнюю строку
        self.eyeTable.selectRow(len(self.eye_data) - 1)

    def removeEyeRow(self):
        row = self.eyeTable.currentRow()
        if row >= 0 and row < len(self.eye_data):
            del self.eye_data[row]
            self.refreshTables()
            self.applyChanges()
            self.portraitTileWidget.setAnimData(self.eye_data, self.mouth_data)
            self.updatePreview()

    def addMouthRow(self):
        self.mouth_data.append([0, 0, 6, 0])
        self.refreshTables()
        self.applyChanges()
        self.portraitTileWidget.setAnimData(self.eye_data, self.mouth_data)
        self.updatePreview()
        self.mouthTable.selectRow(len(self.mouth_data) - 1)

    def removeMouthRow(self):
        row = self.mouthTable.currentRow()
        if row >= 0 and row < len(self.mouth_data):
            del self.mouth_data[row]
            self.refreshTables()
            self.applyChanges()
            self.portraitTileWidget.setAnimData(self.eye_data, self.mouth_data)
            self.updatePreview()

    # ====== Остальные методы без изменений (changePortrait, refreshPortraitImage, ...) ======
    def changePortrait(self, num=None):
        if num is not None:
            if not self.rom.data["portraits"][num].loaded:
                self.rom.getPortraits(num, num)
            self.portrait = self.rom.data["portraits"][num]
            self.eye_data = parse_anim_bytes(self.portrait.eyeBytes)
            self.mouth_data = parse_anim_bytes(self.portrait.mouthBytes)
        self.palette = self.portrait.palette
        self.changeColors()
        self.refreshPortraitImage()
        self.refreshTables()
        self.updateModifiedIndicator(self.portrait.modified)

    def refreshPortraitImage(self):
        tw = 8
        th = 8
        order = self.portrait.frame.getTileOrder(tw, th)
        tiles = [self.portrait.frame.tiles[t] for t in order]
        pixels = []
        for tRow in range(th):
            for pRow in range(8):
                row = "".join([tiles[tRow*tw+to].pixels[pRow] for to in range(tw)])
                pixels.append(row)
        img = QImage(64, 64, QImage.Format_ARGB32)
        for y in range(64):
            for x in range(64):
                idx = int(pixels[y][x], 16)
                color_str = self.palette.colors[idx]
                qc = QColor(color_str)
                img.setPixelColor(x, y, qc)
        pixmap = QPixmap.fromImage(img).scaled(64*3, 64*3)
        self.portraitTileWidget.setPixmap(pixmap)
        self.portraitTileWidget.setAnimData(self.eye_data, self.mouth_data)
        self.updatePreview()

    def updatePreview(self):
        if not hasattr(self, 'portrait'):
            return
        tw, th = 8, 8
        order = self.portrait.frame.getTileOrder(tw, th)
        tiles_all = self.portrait.frame.tiles
        tiles = [tiles_all[t] for t in order]
        tile_map = [[0]*8 for _ in range(8)]
        idx = 0
        for ty in range(8):
            for tx in range(8):
                tile_map[ty][tx] = idx
                idx += 1
        import copy
        tiles_mod = copy.deepcopy(tiles)
        if self.blinkCheck.isChecked():
            for entry in self.eye_data:
                src_x, src_y, dst_x, dst_y = entry
                if 0 <= src_x < 8 and 0 <= src_y < 8 and 0 <= dst_x < 8 and 0 <= dst_y < 8:
                    src_idx = tile_map[src_y][src_x]
                    dst_idx = tile_map[dst_y][dst_x]
                    tiles_mod[src_idx] = copy.deepcopy(tiles[dst_idx])
        if self.talkCheck.isChecked():
            for entry in self.mouth_data:
                src_x, src_y, dst_x, dst_y = entry
                if 0 <= src_x < 8 and 0 <= src_y < 8 and 0 <= dst_x < 8 and 0 <= dst_y < 8:
                    src_idx = tile_map[src_y][src_x]
                    dst_idx = tile_map[dst_y][dst_x]
                    tiles_mod[src_idx] = copy.deepcopy(tiles[dst_idx])
        pixels = []
        for tRow in range(th):
            for pRow in range(8):
                row = "".join([tiles_mod[tRow*tw+to].pixels[pRow] for to in range(tw)])
                pixels.append(row)
        img = QImage(64, 64, QImage.Format_ARGB32)
        for y in range(64):
            for x in range(64):
                idx = int(pixels[y][x], 16)
                color_str = self.palette.colors[idx]
                qc = QColor(color_str)
                img.setPixelColor(x, y, qc)
        pixmap = QPixmap.fromImage(img).scaled(64*3, 64*3)
        self.portraitTileWidget.setPixmap(pixmap)

    def refreshTables(self):
        self._fillTable(self.eyeTable, self.eye_data)
        self._fillTable(self.mouthTable, self.mouth_data)

    def _fillTable(self, table, data):
        table.blockSignals(True)
        table.clearContents()
        table.setRowCount(len(data))
        for row, entry in enumerate(data):
            for col, val in enumerate(entry):
                item = QTableWidgetItem()
                item.setData(Qt.EditRole, val)
                item.setData(Qt.DisplayRole, str(val))
                table.setItem(row, col, item)
        table.blockSignals(False)

    def onEyeSelectionChanged(self):
        row = self.eyeTable.currentRow()
        self.portraitTileWidget.setSelectedEye(row)
        self.mouthTable.clearSelection()

    def onMouthSelectionChanged(self):
        row = self.mouthTable.currentRow()
        self.portraitTileWidget.setSelectedMouth(row)
        self.eyeTable.clearSelection()

    def onEyeCellChanged(self, row, col):
        if row < len(self.eye_data):
            item = self.eyeTable.item(row, col)
            if item:
                val = item.data(Qt.EditRole)
                if val is None:
                    val = 0
                self.eye_data[row][col] = int(val)
            self.applyChanges()
            self.portraitTileWidget.setAnimData(self.eye_data, self.mouth_data)
            self.updatePreview()

    def onMouthCellChanged(self, row, col):
        if row < len(self.mouth_data):
            item = self.mouthTable.item(row, col)
            if item:
                val = item.data(Qt.EditRole)
                if val is None:
                    val = 0
                self.mouth_data[row][col] = int(val)
            self.applyChanges()
            self.portraitTileWidget.setAnimData(self.eye_data, self.mouth_data)
            self.updatePreview()

    def onTileClicked(self, tile_x, tile_y):
        eye_idx = self.portraitTileWidget.selected_eye_idx
        mouth_idx = self.portraitTileWidget.selected_mouth_idx
        if eye_idx >= 0 and eye_idx < len(self.eye_data):
            entry = self.eye_data[eye_idx]
            if tile_x < 6:
                entry[0], entry[1] = tile_x, tile_y
            else:
                entry[2], entry[3] = tile_x, tile_y
            self.applyChanges()
            self.refreshTables()
            self.portraitTileWidget.setAnimData(self.eye_data, self.mouth_data)
            self.updatePreview()
        elif mouth_idx >= 0 and mouth_idx < len(self.mouth_data):
            entry = self.mouth_data[mouth_idx]
            if tile_x < 6:
                entry[0], entry[1] = tile_x, tile_y
            else:
                entry[2], entry[3] = tile_x, tile_y
            self.applyChanges()
            self.refreshTables()
            self.portraitTileWidget.setAnimData(self.eye_data, self.mouth_data)
            self.updatePreview()

    def applyChanges(self):
        self.portrait.eyeBytes = pack_anim_bytes(self.eye_data)
        self.portrait.mouthBytes = pack_anim_bytes(self.mouth_data)
        self.portrait.modified = True
        self.updateModifiedIndicator(True)

    def changeColors(self):
        palette = self.palette
        for c in range(len(self.colorPanels)):
            if shiboken6.isValid(self.colorPanels[c]):
                self.colorPanels[c].setStyleSheet(
                    f"background-color: {palette.colors[c]}; border: 1px solid #555; border-radius: 3px;"
                )
                self.colorPanels[c].update()

    def OnImportImage(self):
        if not shiboken6.isValid(self.portraitTileWidget) or self.rom is None:
            return
        width, height = 64, 64
        dlg = QFileDialog(self, f"Import {width}x{height} PNG", "", "PNG files (*.png)")
        dlg.setFileMode(QFileDialog.ExistingFile)
        if dlg.exec() == QDialog.Accepted:
            fn = dlg.selectedFiles()[0]
            try:
                img = Image.open(fn)
                # Приводим к индексированному 16-цветному, если нужно
                if img.mode != 'P':
                    img = img.convert('P', palette=Image.ADAPTIVE, colors=16)
                if img.mode != 'P':
                    raise ValueError("Image is not indexed. Please save as 16-color PNG with palette.")
                if img.size != (width, height):
                    QMessageBox.warning(self, f"Image must be {width}x{height}.", self.parent.baseTitle + " -- Error")
                    return

                # Получаем палитру и преобразуем каждый цвет в CRAM (как в оригинале)
                raw_palette = img.getpalette()
                if raw_palette is None or len(raw_palette) < 48:
                    raw_palette = list(raw_palette or [])
                    raw_palette += [0] * (48 - len(raw_palette))

                cols = []
                for i in range(0, 48, 3):
                    r, g, b = raw_palette[i], raw_palette[i+1], raw_palette[i+2]
                    cr, cg, cb = conform_color_to_cram(r, g, b)
                    cols.append("#%02x%02x%02x" % (cr, cg, cb))

                pal = data.Palette()
                pal.init(cols)
                self.palette = pal
                self.portrait.palette = pal

                # Пиксели оставляем как есть (индекс 0 считается прозрачным)
                indexes = list(img.getdata())
                pixels_hex = "".join(["%x" % idx for idx in indexes])
                pixel_rows = [pixels_hex[i:i+width] for i in range(0, width*height, width)]

                # Обновляем тайлы кадра
                self.curFrame.convertFromPixelRows(pixel_rows)
                tw = width // 8
                th = height // 8
                newtiles = [None] * len(self.curFrame.tiles)
                order = self.curFrame.getTileOrder(tw, th)
                for i in range(len(newtiles)):
                    newtiles[order[i]] = self.curFrame.tiles[i]
                self.curFrame.tiles = newtiles

                self.changePortrait()
                self.changeColors()
                self.modify()
            except Exception as e:
                QMessageBox.critical(self, "Import Error", str(e))

    def OnExportImage(self):
        if not shiboken6.isValid(self.portraitTileWidget):
            return
        width, height = 64, 64
        dlg = QFileDialog(self, f"Export {width}x{height} PNG", "", "PNG files (*.png)")
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        if dlg.exec() == QDialog.Accepted:
            fn = dlg.selectedFiles()[0]
            try:
                # Собираем пиксели в экранном порядке (как при отображении)
                tw, th = 8, 8
                order = self.curFrame.getTileOrder(tw, th)
                tiles = [self.curFrame.tiles[t] for t in order]
                pixels_flat = []
                for tRow in range(th):
                    for pRow in range(8):
                        row = "".join([tiles[tRow*tw+to].pixels[pRow] for to in range(tw)])
                        pixels_flat.extend([int(c, 16) for c in row])

                img = Image.new("P", (width, height))
                img.putdata(pixels_flat)

                # Палитра из портрета (уже в CRAM)
                palette_bytes = []
                for i in range(16):
                    c = self.portrait.palette.colors[i]
                    palette_bytes.extend([int(c[1:3],16), int(c[3:5],16), int(c[5:7],16)])
                palette_bytes += [0] * (768 - len(palette_bytes))
                img.putpalette(palette_bytes)

                # Сохраняем с прозрачностью для индекса 0
                img.save(fn, "PNG", transparency=0)
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

    def OnSelectPortrait(self, idx):
        self.changePortrait(idx)

    def OnSwitchFrame(self):
        self.frame ^= 1
        self.changePortrait(self.portraitList.currentIndex())

    def OnShow(self, event=None):
        if self.rom is None:
            return
        self.changeColors()

    def refreshPixels(self):
        pass

    def getCurrentSpriteObject(self):
        return self.portrait

    def getCurrentData(self):
        return self.portrait

    changeSelection = changePortrait

    curFrame = property(lambda self: self.portrait.frame)
    curPalette = property(lambda self: self.portrait.palette)