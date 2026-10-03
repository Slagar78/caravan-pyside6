"""Редактор карт (ASM) — просмотр + split + таблицы (read-only)."""
import os
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLabel,
    QSplitter, QScrollArea, QComboBox, QMdiSubWindow,
    QPushButton, QProgressDialog, QMessageBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QCheckBox, QSizePolicy,
    QGridLayout, QSpinBox,
    QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, QTimer, QStandardPaths, Signal
from PySide6.QtGui import QPainter, QPixmap, QImage, QColor, QPen, QGuiApplication
import rompanel
import splitter
import parsers

# ============================================================
#  Шахматка (alpha.png)
# ============================================================

_ALPHA_BG = None

def get_alpha_bg():
    """Возвращает QPixmap alpha.png (загружается один раз)."""
    global _ALPHA_BG
    if _ALPHA_BG is None:
        _ALPHA_BG = QPixmap("alpha.png")
    return _ALPHA_BG


def make_alpha_block(bmp: QPixmap, size: int) -> QPixmap:
    """Накладывает блок поверх шахматки alpha.png."""
    bg = get_alpha_bg().scaled(size, size)
    p = QPainter(bg)
    p.drawPixmap(0, 0, bmp)
    p.end()
    return bg


def get_cache_dir(rom_path=None):
    base = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppLocalDataLocation
    )
    if not base:
        base = str(Path.home() / ".caravan")
    return Path(base) / "maps"

# ============================================================
#  Авто-определение раскладки под экран
# ============================================================

# (min_width, sizes,                          map_scale)
SCREEN_PRESETS = [
    (2500, (180, 340, 1200, 240), 2.0 ),  # QHD+
    (1900, (150, 300,  900, 200), 1.0 ),  # Full HD / WUXGA
    (1580, (130, 270,  800, 170), 1.0 ),  # 1600x900
    (1420, (110, 240,  700, 150), 0.5 ),  # 1440x900
    (1340, (100, 200,  600, 140), 0.5 ),  # 1366x768
    (0,    ( 90, 170,  500, 130), 0.5 ),  # 1280 и меньше — карта 1/2x, скролл всё равно есть
]


def detect_screen_preset():
    """Возвращает (sizes, map_scale)."""
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return SCREEN_PRESETS[1][1], SCREEN_PRESETS[1][2]
    w = screen.availableGeometry().width()
    for min_w, sizes, scale in SCREEN_PRESETS:
        if w >= min_w:
            return sizes, scale
    return SCREEN_PRESETS[-1][1], SCREEN_PRESETS[-1][2]

# ============================================================
#  Рендер карты
# ============================================================

class SimpleMapView(QWidget):
    BASE_BLOCK_SIZE = 24

    # Сигнал: изменилась ячейка карты. (idx, old_value, new_value)
    blockPainted = Signal(int, int, int)

    def __init__(self, py_map, palette, scale=1, parent=None,
                 get_paint_block=None, editable=False):
        super().__init__(parent)
        self.py_map = py_map
        self.palette = palette
        self.scale = scale
        self.show_grid = False
        self.block_bmps = []

        # === Режим редактирования ===
        self.editable = editable
        self.get_paint_block = get_paint_block   # callable(button) → block_idx
        self._painting = False
        self._last_painted_idx = -1

        if self.editable:
            self.setCursor(Qt.ArrowCursor)   # по умолчанию — стрелка

        self._rebuild()
        self._update_size()

    def _update_size(self):
        size = int(64 * self.BASE_BLOCK_SIZE * self.scale)
        self.setFixedSize(size, size)

    def set_scale(self, scale):
        self.scale = scale
        self._update_size()
        self.update()

    def _rebuild(self):
        self.block_bmps = []
        if not hasattr(self.py_map, "blocks") or not self.py_map.blocks:
            return
        try:
            rt = self.palette.rgbaTuples()
        except Exception as e:
            print(f"Ошибка палитры: {e}")
            return
        for blk in self.py_map.blocks:
            try:
                buf = b""
                for row in blk.pixels:
                    for p in row:
                        color_idx = int(p, 16)
                        for t in rt[color_idx]:
                            buf += bytes([t])
                image = QImage(buf, 24, 24, QImage.Format_RGBA8888)
                self.block_bmps.append(QPixmap.fromImage(image))
            except Exception as e:
                print(f"Ошибка блока: {e}")
                self.block_bmps.append(QPixmap(24, 24))

    def _pos_to_idx(self, pos):
        """Переводит координаты мыши в индекс ячейки карты (0..4095) или -1."""
        s = self.BASE_BLOCK_SIZE * self.scale
        x = int(pos.x() // s)
        y = int(pos.y() // s)
        if 0 <= x < 64 and 0 <= y < 64:
            return y * 64 + x
        return -1

    def _paint_at(self, pos, button):
        """Рисует один блок в позиции pos. Сохраняет верхние 6 бит (флаги)."""
        if not self.editable or self.get_paint_block is None:
            return
        idx = self._pos_to_idx(pos)
        if idx < 0 or idx == self._last_painted_idx:
            return

        block_idx = self.get_paint_block(button)
        if block_idx is None or block_idx < 0:
            return

        old = self.py_map.layoutData[idx]
        new = (old & 0xFC00) | (block_idx & 0x3FF)

        self._last_painted_idx = idx
        if new == old:
            return

        self.py_map.layoutData[idx] = new
        self.py_map.modified = True
        self.update()
        self.blockPainted.emit(idx, old, new)

    def mousePressEvent(self, event):
        if not self.editable:
            return
        if event.button() in (Qt.LeftButton, Qt.RightButton):
            self._painting = True
            self._last_painted_idx = -1
            self._paint_at(event.pos(), event.button())

    def mouseMoveEvent(self, event):
        if not self._painting or not self.editable:
            return
        if event.buttons() & Qt.LeftButton:
            self._paint_at(event.pos(), Qt.LeftButton)
        elif event.buttons() & Qt.RightButton:
            self._paint_at(event.pos(), Qt.RightButton)

    def mouseReleaseEvent(self, event):
        self._painting = False
        self._last_painted_idx = -1

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawTiledPixmap(self.rect(), get_alpha_bg())
        if not self.block_bmps:
            painter.end()
            return
        s = self.BASE_BLOCK_SIZE * self.scale
        layout = self.py_map.layoutData
        for y in range(64):
            for x in range(64):
                idx = y * 64 + x
                if idx >= len(layout):
                    continue
                block_idx = layout[idx] & 0x3FF
                if block_idx < len(self.block_bmps):
                    bmp = self.block_bmps[block_idx]
                    if self.scale != 1:
                        bmp = bmp.scaled(
                            int(s), int(s),
                            Qt.KeepAspectRatio, Qt.FastTransformation
                        )
                    painter.drawPixmap(int(x * s), int(y * s), bmp)

        # ===== Сетка =====
        if self.show_grid:
            pen = QPen(QColor(255, 255, 255, 80))
            pen.setWidth(1)
            painter.setPen(pen)
            step = int(self.BASE_BLOCK_SIZE * self.scale)
            total = step * 64
            for i in range(65):
                pos = i * step
                painter.drawLine(pos, 0, pos, total)
                painter.drawLine(0, pos, total, pos)

        painter.end()


# ============================================================
#  Универсальная таблица
# ============================================================

def make_table(columns: list[str]) -> QTableWidget:
    table = QTableWidget()
    table.setColumnCount(len(columns))
    table.setHorizontalHeaderLabels(columns)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectRows)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    return table


def fill_table(table: QTableWidget, rows: list[list]):
    table.setRowCount(len(rows))
    for r, values in enumerate(rows):
        for c, val in enumerate(values):
            item = QTableWidgetItem(str(val))
            if not isinstance(val, str):
                item.setTextAlignment(Qt.AlignCenter)
            table.setItem(r, c, item)


# ============================================================
#  Правая панель View (чекбоксы — заглушки)
# ============================================================

def build_view_panel():
    """Возвращает (widget, cbs) — словарь с чекбоксами."""
    w = QWidget()
    w.setMinimumWidth(120)
    w.setMaximumWidth(220)
    layout = QVBoxLayout(w)
    layout.setContentsMargins(4, 4, 4, 4)

    # Скруглённые чекбоксы
    w.setStyleSheet("""
        QCheckBox {
            spacing: 6px;
            padding: 2px 4px;
        }
        QCheckBox::indicator {
            width: 14px;
            height: 14px;
            border: 1px solid #888;
            border-radius: 4px;
            background: #f5f5f5;
        }
        QCheckBox::indicator:hover {
            border: 1px solid #3b82f6;
            border-radius: 4px;
        }
        QCheckBox::indicator:checked {
            background: #3b82f6;
            border: 1px solid #2563eb;
            border-radius: 4px;
        }
        QCheckBox::indicator:disabled {
            border: 1px solid #ccc;
            border-radius: 4px;
            background: #e8e8e8;
        }
        QCheckBox::indicator:checked:disabled {
            background: #c7d9f0;
            border: 1px solid #b0c4de;
            border-radius: 4px;
        }
    """)

    cbs = {}

    # --- Основные ---
    g1 = QGroupBox("View")
    l1 = QVBoxLayout(g1)
    l1.setSpacing(2)

    cb = QCheckBox("Show grid");     cbs["grid"] = cb;     l1.addWidget(cb)
    cb = QCheckBox("Show priority"); cbs["priority"] = cb; l1.addWidget(cb)
    cb = QCheckBox("Exploration flags"); cbs["exploration"] = cb; l1.addWidget(cb)

    for key, text in [("areas", "   Areas"), ("warps", "   Warps"),
                      ("triggers", "   Triggers"), ("items", "   Items"),
                      ("vehicles", "   Vehicles")]:
        cb = QCheckBox(text); cbs[key] = cb; l1.addWidget(cb)

    for key, text in [("flag_copies", "Flag Copies"),
                      ("step_copies", "Step Copies"),
                      ("roof_copies", "Roof Copies"),
                      ("preview_anim", "Preview anim")]:
        cb = QCheckBox(text); cbs[key] = cb; l1.addWidget(cb)

    layout.addWidget(g1)

    # --- Areas display ---
    g2 = QGroupBox("Areas display")
    l2 = QVBoxLayout(g2)
    l2.setSpacing(2)

    for key, text in [("upper_overlay", "Upper layer overlay"),
                      ("bg_underlay", "BG underlay"),
                      ("parallax", "Simulate parallax\nand autoscroll")]:
        cb = QCheckBox(text); cbs[key] = cb; l2.addWidget(cb)

    layout.addWidget(g2)
    layout.addStretch()

    return w, cbs

# ============================================================
#  Панель Blockset (слева от карты)
# ============================================================

class ClickLabel(QLabel):
    """QLabel с сигналами ЛКМ и ПКМ."""
    clicked = Signal(int)
    right_clicked = Signal(int)

    def __init__(self, index: int, parent=None):
        super().__init__(parent)
        self.index = index
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.index)
        elif event.button() == Qt.RightButton:
            self.right_clicked.emit(self.index)
        super().mousePressEvent(event)


class BlocksetPanel(QWidget):
    """Показывает все блоки карты в виде сетки (read-only).

    Порт Java-панели MapBlocksetLayoutPanel.
    """

    # Сигнал: кликнули на блок. Передаём (left_idx, right_idx), 
    # -1 если не выбран.
    blockSelected = Signal(int, int)

    # Сигнал: сменился режим. 0 = Paint Blocks, иначе — маска флага.
    paintModeChanged = Signal(int)

    BLOCK_SIZE = 24      # размер блока в пикселях (1x)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.blocks = []
        self.block_bmps = []
        self.tiles_per_row = 10
        self.cell_labels = {}          # index → ClickLabel
        self.left_selected_index = -1   # текущий выбранный ЛКМ
        self.right_selected_index = -1  # текущий выбранный ПКМ

        # Заголовок
        header = QLabel("Blockset")
        header.setStyleSheet("font-weight: bold; padding: 4px;")

        # Скролл с сеткой блоков
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMaximumHeight(420)
        self.inner = QWidget()
        self.inner.setStyleSheet("background: #2a2a2a;")
        self.grid = QGridLayout(self.inner)
        self.grid.setSpacing(0)
        self.grid.setContentsMargins(4, 4, 4, 4)
        self.scroll.setWidget(self.inner)

        # ===== Вкладки: Selected Blocks / Exploration Flags =====
        self.mode_tabs = QTabWidget()
        self.mode_tabs.setStyleSheet("""
            QTabBar::tab {
                padding: 6px 10px;
                font-size: 9pt;
            }
            QTabBar::tab:selected {
                background: #3b82f6;
                color: white;
            }
        """)

        # --- Вкладка 1: Selected Blocks ---
        tab_preview = QWidget()
        preview_layout = QHBoxLayout(tab_preview)
        preview_layout.setContentsMargins(4, 4, 4, 4)
        preview_layout.setSpacing(12)

        # Left click
        left_col = QVBoxLayout()
        left_col.setSpacing(2)
        left_lbl = QLabel("Left click")
        left_lbl.setAlignment(Qt.AlignCenter)
        left_lbl.setStyleSheet("color: #ccc; font-size: 9pt;")
        left_col.addWidget(left_lbl)

        self.left_preview = QLabel("—")
        self.left_preview.setFixedSize(64, 64)
        self.left_preview.setAlignment(Qt.AlignCenter)
        self.left_preview.setStyleSheet("""
            QLabel {
                border: 2px solid #ffd700;
                border-radius: 6px;
                background: #1e1e1e;
                color: #888;
            }
        """)
        left_col.addWidget(self.left_preview, 0, Qt.AlignCenter)

        self.left_index_label = QLabel("")
        self.left_index_label.setAlignment(Qt.AlignCenter)
        self.left_index_label.setStyleSheet("color: #888; font-size: 8pt;")
        left_col.addWidget(self.left_index_label)

        # Right click
        right_col = QVBoxLayout()
        right_col.setSpacing(2)
        right_lbl = QLabel("Right click")
        right_lbl.setAlignment(Qt.AlignCenter)
        right_lbl.setStyleSheet("color: #ccc; font-size: 9pt;")
        right_col.addWidget(right_lbl)

        self.right_preview = QLabel("—")
        self.right_preview.setFixedSize(64, 64)
        self.right_preview.setAlignment(Qt.AlignCenter)
        self.right_preview.setStyleSheet("""
            QLabel {
                border: 2px solid #ff00ff;
                border-radius: 6px;
                background: #1e1e1e;
                color: #888;
            }
        """)
        right_col.addWidget(self.right_preview, 0, Qt.AlignCenter)

        self.right_index_label = QLabel("")
        self.right_index_label.setAlignment(Qt.AlignCenter)
        self.right_index_label.setStyleSheet("color: #888; font-size: 8pt;")
        right_col.addWidget(self.right_index_label)

        preview_layout.addStretch(1)     # слева — воздух
        preview_layout.addLayout(left_col)
        preview_layout.addLayout(right_col)
        preview_layout.addStretch(1)     # справа — воздух

        self.mode_tabs.addTab(tab_preview, "Selected Blocks")

        # --- Вкладка 2: Exploration Flags ---
        tab_flags = QWidget()
        flags_layout = QVBoxLayout(tab_flags)
        flags_layout.setContentsMargins(4, 4, 4, 4)
        flags_layout.setSpacing(2)

        self.radio_obstructed = QRadioButton("Obstructed")
        self.radio_stairs = QRadioButton("Stairs")
        self.radio_obstructed.setChecked(True)

        self._flag_group = QButtonGroup(self)
        self._flag_group.addButton(self.radio_obstructed, 1)   # mask 0xC000
        self._flag_group.addButton(self.radio_stairs, 2)       # mask 0x4000
        self._flag_group.buttonClicked.connect(self._on_flag_changed)

        flags_layout.addWidget(self.radio_obstructed)
        flags_layout.addWidget(self.radio_stairs)
        flags_layout.addStretch()

        self.mode_tabs.addTab(tab_flags, "Exploration Flags")

        # Переключение вкладок — эмитим режим
        self.mode_tabs.currentChanged.connect(self._on_tab_changed)

        # Кнопки (пока заглушки)
        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.clone_btn = QPushButton("Clone")
        self.remove_btn = QPushButton("Remove")
        for b in (self.add_btn, self.clone_btn, self.remove_btn):
            b.setEnabled(False)
            b.setMaximumWidth(80)
            btn_row.addWidget(b)

        # Опции (пока заглушки)
        opts = QGroupBox("Blockset View")
        opts_layout = QVBoxLayout(opts)
        opts_layout.setSpacing(2)

        self.cb_priority = QCheckBox("Show Priority")
        self.cb_priority.setEnabled(False)
        self.cb_grid = QCheckBox("Grid")
        self.cb_grid.setEnabled(False)
        opts_layout.addWidget(self.cb_priority)
        opts_layout.addWidget(self.cb_grid)

        tiles_row = QHBoxLayout()
        tiles_row.addWidget(QLabel("Tiles per row:"))
        self.spin_tiles = QSpinBox()
        self.spin_tiles.setRange(1, 32)
        self.spin_tiles.setValue(10)
        self.spin_tiles.setEnabled(False)
        tiles_row.addWidget(self.spin_tiles)
        opts_layout.addLayout(tiles_row)

        scale_row = QHBoxLayout()
        scale_row.addWidget(QLabel("Scale:"))
        self.combo_scale = QComboBox()
        self.combo_scale.addItems(["1x", "2x", "3x"])
        self.combo_scale.setEnabled(False)
        scale_row.addWidget(self.combo_scale)
        opts_layout.addLayout(scale_row)

        # Собираем
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)
        layout.addWidget(header)
        layout.addWidget(self.scroll, 1)
        layout.addWidget(self.mode_tabs)
        layout.addLayout(btn_row)
        layout.addWidget(opts)

    def set_map(self, py_map, palette):
        """Загружает блоки карты и строит сетку миниатюр."""
        self.blocks = list(getattr(py_map, "blocks", []) or [])
        self.block_bmps = []

        # === Полный сброс выбора ===
        self.left_selected_index = -1
        self.right_selected_index = -1

        # Сбрасываем оба превью
        self.left_preview.setPixmap(QPixmap())
        self.left_preview.setText("—")
        self.left_index_label.setText("")
        self.right_preview.setPixmap(QPixmap())
        self.right_preview.setText("—")
        self.right_index_label.setText("")

        # Сообщаем наружу, что выбор потерян
        self.blockSelected.emit(-1, -1)

        if not self.blocks:
            self._rebuild_grid()
            return

        try:
            rt = palette.rgbaTuples()
        except Exception as e:
            print(f"[blockset] Ошибка палитры: {e}")
            self._rebuild_grid()
            return

        for blk in self.blocks:
            try:
                buf = b""
                for row in blk.pixels:
                    for p in row:
                        idx = int(p, 16)
                        for t in rt[idx]:
                            buf += bytes([t])
                img = QImage(buf, 24, 24, QImage.Format_RGBA8888)
                self.block_bmps.append(QPixmap.fromImage(img))   # ← без alpha
            except Exception as e:
                print(f"[blockset] Ошибка блока: {e}")
                self.block_bmps.append(QPixmap(24, 24))

        self._rebuild_grid()

    def _rebuild_grid(self):
        """Перерисовывает сетку блоков."""
        # Очищаем
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cols = self.tiles_per_row
        self.cell_labels = {}    # сбрасываем
        CELL_STYLE = "border: 1px solid #555;"
        LABEL_STYLE = "color: #ccc; font-size: 8pt; " + CELL_STYLE

        # ===== Угловая пустая ячейка (0, 0) =====
        corner = QLabel("")
        corner.setStyleSheet(LABEL_STYLE)
        corner.setFixedSize(28, 18)
        corner.setAlignment(Qt.AlignCenter)
        self.grid.addWidget(corner, 0, 0)

        # ===== Верхняя строка — номера столбцов (0..9) =====
        for c in range(cols):
            lbl_col = QLabel(str(c))
            lbl_col.setStyleSheet(LABEL_STYLE)
            lbl_col.setFixedSize(self.BLOCK_SIZE, 18)
            lbl_col.setAlignment(Qt.AlignCenter)
            self.grid.addWidget(lbl_col, 0, c + 1)

        # ===== Строки блоков =====
        for i, bmp in enumerate(self.block_bmps):
            row = i // cols + 1
            col = i % cols

            # Левая метка (0, 10, 20, ...)
            if i % cols == 0:
                lbl = QLabel(str(i))
                lbl.setStyleSheet(LABEL_STYLE)
                lbl.setFixedSize(28, self.BLOCK_SIZE)
                lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.grid.addWidget(lbl, row, 0)

            # Миниатюра блока (alpha под низом — при показе)
            cell = ClickLabel(i)
            cell.setPixmap(make_alpha_block(bmp, self.BLOCK_SIZE))
            cell.setFixedSize(self.BLOCK_SIZE, self.BLOCK_SIZE)
            cell.setToolTip(f"Block {i}")
            cell.clicked.connect(self._on_block_clicked)
            cell.right_clicked.connect(self._on_block_right_clicked)
            self.cell_labels[i] = cell
            self.grid.addWidget(cell, row, col + 1)

        # Растяжка по правому краю
        self.grid.setColumnStretch(cols + 1, 1)
        # Восстанавливаем подсветку выбранных
        self._refresh_cell_highlight()

    def _on_block_clicked(self, index: int):
        """ЛКМ → левый квадрат + жёлтая рамка в сетке."""
        if not (0 <= index < len(self.block_bmps)):
            return
        self.left_selected_index = index

        big = self.block_bmps[index].scaled(
            56, 56, Qt.KeepAspectRatio, Qt.FastTransformation
        )
        self.left_preview.setPixmap(make_alpha_block(big, 56))
        self.left_index_label.setText(f"Block {index}")

        self._refresh_cell_highlight()
        self.blockSelected.emit(self.left_selected_index,
                                self.right_selected_index)

    def _on_block_right_clicked(self, index: int):
        """ПКМ → правый квадрат + розовая рамка в сетке."""
        if not (0 <= index < len(self.block_bmps)):
            return
        self.right_selected_index = index

        big = self.block_bmps[index].scaled(
            56, 56, Qt.KeepAspectRatio, Qt.FastTransformation
        )
        self.right_preview.setPixmap(make_alpha_block(big, 56))
        self.right_index_label.setText(f"Block {index}")

        self._refresh_cell_highlight()
        self.blockSelected.emit(self.left_selected_index,
                                self.right_selected_index)

    def _on_tab_changed(self, idx: int):
        """Сменилась вкладка. Вкладка 0 — Paint Blocks, вкладка 1 — флаги."""
        if idx == 0:
            self.paintModeChanged.emit(0)
        else:
            self._emit_current_flag()

    def _on_flag_changed(self, btn):
        """Переключили радио внутри Exploration Flags."""
        if self.mode_tabs.currentIndex() == 1:
            self._emit_current_flag()

    def _emit_current_flag(self):
        """Эмитит маску текущего выбранного флага."""
        mode_id = self._flag_group.checkedId()
        if mode_id == 1:
            mask = 0xC000   # Obstructed
        elif mode_id == 2:
            mask = 0x4000   # Stairs
        else:
            mask = 0
        self.paintModeChanged.emit(mask)

    def _refresh_cell_highlight(self):
        """Обновляет рамки у выбранных блоков в сетке.

        ЛКМ → жёлтая рамка
        ПКМ → розовая рамка
        Если индекс один и тот же — рисуем обе (фиолетовая)
        """
        for idx, cell in self.cell_labels.items():
            is_left = (idx == self.left_selected_index)
            is_right = (idx == self.right_selected_index)

            if is_left and is_right:
                # Оба выбраны — толстая фиолетовая
                cell.setStyleSheet(
                    "border: 2px solid #c060ff;"
                    "background: #3a2a4a;"
                )
            elif is_left:
                # Только ЛКМ — жёлтая
                cell.setStyleSheet(
                    "border: 2px solid #ffd700;"
                    "background: #3a3a10;"
                )
            elif is_right:
                # Только ПКМ — розовая
                cell.setStyleSheet(
                    "border: 2px solid #ff00ff;"
                    "background: #3a103a;"
                )
            else:
                # Обычная
                cell.setStyleSheet("border: 1px solid #555;")

# ============================================================
#  Главная панель
# ============================================================

class MapEditorPanel(rompanel.ROMPanel):

    frameTitle = "Map Editor (ASM)"
    canMaximize = True

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(100, self._maximize_once)
        QTimer.singleShot(200, self._maybe_split)

    def _maximize_once(self):
        if getattr(self, "_maximized_done", False):
            return
        self._maximized_done = True
        w = self
        while w is not None:
            if isinstance(w, QMdiSubWindow):
                w.showMaximized()
                # После разворота — применить размеры панелей
                QTimer.singleShot(50, self._apply_splitter_sizes)
                return
            w = w.parentWidget()

    def _apply_splitter_sizes(self):
        """Применяет размеры панелей после разворота окна."""
        if hasattr(self, "_main_splitter") and hasattr(self, "_auto_sizes"):
            self._main_splitter.setSizes(list(self._auto_sizes))
       
    def init(self):
        # === Авто-детект экрана — один раз при старте ===
        self._auto_sizes, self._auto_map_scale = detect_screen_preset()
        print(f"[screen] sizes={self._auto_sizes} scale={self._auto_map_scale}")

        # === Состояние редактора карты ===
        self.paint_left = -1       # индекс блока для ЛКМ (-1 = не выбран)
        self.paint_right = -1      # индекс блока для ПКМ (-1 = не выбран)
        self.paint_mode = 0        # 0 = Paint Blocks, иначе — маска флага
        self.undo_stack = []       # [(idx, old_val, new_val), ...]
        self.redo_stack = []
        self.current_view = None        

        # ============ Слева — список карт ============
        self.map_list = QListWidget()
        self.map_list.addItems(
            [f"Map {i:02d}" for i in range(len(self.rom.data["maps"]))]
        )
        self.map_list.currentRowChanged.connect(self._on_map_selected)

        left = QWidget()
        left.setMinimumWidth(80)
        left.setMaximumWidth(200)
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Maps:"))
        left_layout.addWidget(self.map_list)

        # ============ Центр — верхняя панель + карта + вкладки ============
        center = QWidget()
        center_layout = QVBoxLayout(center)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Scale:"))
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["1/4x", "1/2x", "1x", "2x", "4x"])
        _scale_to_index = {0.25: 0, 0.5: 1, 1.0: 2, 2.0: 3, 4.0: 4}
        self.scale_combo.setCurrentIndex(
            _scale_to_index.get(self._auto_map_scale, 2)
        )
        self.scale_combo.currentIndexChanged.connect(self._on_scale_changed)
        top_bar.addWidget(self.scale_combo)

        top_bar.addSpacing(20)
        self.split_btn = QPushButton("Split to ASM")
        self.split_btn.clicked.connect(self._on_split_clicked)
        top_bar.addWidget(self.split_btn)

        self.open_folder_btn = QPushButton("Open ASM folder")
        self.open_folder_btn.clicked.connect(self._on_open_folder)
        top_bar.addWidget(self.open_folder_btn)

        top_bar.addSpacing(20)
        self.undo_btn = QPushButton("↶ Undo")
        self.undo_btn.clicked.connect(self._undo)
        self.undo_btn.setEnabled(False)
        top_bar.addWidget(self.undo_btn)

        self.redo_btn = QPushButton("↷ Redo")
        self.redo_btn.clicked.connect(self._redo)
        self.redo_btn.setEnabled(False)
        top_bar.addWidget(self.redo_btn)

        top_bar.addStretch()
        self.info_label = QLabel("Select a map...")
        top_bar.addWidget(self.info_label)

        center_layout.addLayout(top_bar)

        # Вертикальный сплиттер: карта сверху, вкладки снизу
        v_splitter = QSplitter(Qt.Vertical)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        v_splitter.addWidget(self.scroll_area)

        # ============ Вкладки ============
        self.tabs = QTabWidget()
        self.tabs.setMinimumHeight(200)

        # Areas
        self.areas_table = make_table([
            "Index", "L1 X", "L1 Y", "L1 X'", "L1 Y'",
            "L2 FX", "L2 FY", "L2 BX", "L2 BY",
            "L1 PX", "L1 PY", "L2 PX", "L2 PY",
            "L1 SX", "L1 SY", "L2 SX", "L2 SY",
            "L1 Type", "Music"
        ])
        self.tabs.addTab(self.areas_table, "Areas")

        # Flag Copies
        self.flag_table = make_table([
            "Index", "Flag", "Flag Info",
            "Source X", "Source Y", "Source X'", "Source Y'",
            "Dest X", "Dest Y", "Comment"
        ])
        self.tabs.addTab(self.flag_table, "Flag Copies")

        # Step Copies
        self.step_table = make_table([
            "Index", "Trigger X", "Trigger Y",
            "Source X", "Source Y", "Source X'", "Source Y'",
            "Dest X", "Dest Y", "Comment"
        ])
        self.tabs.addTab(self.step_table, "Step Copies")

        # Roof Copies
        self.roof_table = make_table([
            "Index", "Trigger X", "Trigger Y",
            "Source X", "Source Y", "Source X'", "Source Y'",
            "Dest X", "Dest Y", "Comment"
        ])
        self.tabs.addTab(self.roof_table, "Roof Copies")

        # Warps
        self.warps_table = make_table([
            "Index", "Trigger X", "Trigger Y", "Scroll Dir.",
            "Dest Map", "Dest X", "Dest Y", "Facing", "Comment"
        ])
        self.tabs.addTab(self.warps_table, "Warps")

        # Items (с подвкладками Chest/Other)
        self.items_subtabs = QTabWidget()
        self.chest_table = make_table([
            "Index", "X", "Y", "Flag", "Flag Info", "Item", "Comment"
        ])
        self.other_table = make_table([
            "Index", "X", "Y", "Flag", "Flag Info", "Item", "Comment"
        ])
        self.items_subtabs.addTab(self.chest_table, "Chest Items")
        self.items_subtabs.addTab(self.other_table, "Other Items")
        self.tabs.addTab(self.items_subtabs, "Items")

        # Animations
        self.anim_table = make_table([
            "Index", "Start", "End", "Dest", "Delay"
        ])
        self.tabs.addTab(self.anim_table, "Animations")

        v_splitter.addWidget(self.tabs)
        v_splitter.setSizes([500, 250])

        center_layout.addWidget(v_splitter)

        # ============ Панель Blockset (между списком карт и картой) ============
        self.blockset_panel = BlocksetPanel()
        self.blockset_panel.setMinimumWidth(150)
        self.blockset_panel.setMaximumWidth(340)
        self.blockset_panel.blockSelected.connect(self._on_block_selected)
        self.blockset_panel.paintModeChanged.connect(self._on_paint_mode_changed)

        # ============ Справа — View panel ============
        right_panel, self.view_cbs = build_view_panel()

        # Все выключены по умолчанию
        for cb in self.view_cbs.values():
            cb.setEnabled(False)

        # Активируем grid
        self.view_cbs["grid"].setEnabled(True)
        self.view_cbs["grid"].toggled.connect(self._on_grid_toggled)

        # ============ Главный сплиттер ============
        self._main_splitter = QSplitter(Qt.Horizontal)
        main_splitter = self._main_splitter
        main_splitter.addWidget(left)                # 0 — список карт
        main_splitter.addWidget(self.blockset_panel) # 1 — Blockset
        main_splitter.addWidget(center)              # 2 — карта + вкладки
        main_splitter.addWidget(right_panel)         # 3 — View
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 0)
        main_splitter.setStretchFactor(2, 1)
        main_splitter.setStretchFactor(3, 0)

        # === Раскладка под экран (авто-детект из начала init) ===
        main_splitter.setSizes(list(self._auto_sizes))

        # Ничего не прячем — разрешаем сжиматься
        main_splitter.setCollapsible(1, True)
        main_splitter.setCollapsible(3, True)

        self.sizer.addWidget(main_splitter, 0, 0)

        # Кеш-директория
        self.cache_dir = None
        try:
            self.cache_dir = get_cache_dir(self.rom.file.name)
            print(f"[cache] Путь кеша: {self.cache_dir}")
        except Exception as e:
            print(f"[cache] Не могу получить путь кеша: {e}")

        QTimer.singleShot(100, lambda: self.map_list.setCurrentRow(0))

    # ============================================================
    #  Split
    # ============================================================

    def _maybe_split(self):
        if self.cache_dir is None:
            return
        marker = self.cache_dir / ".split_done"
        if marker.exists():
            print(f"[split] Кеш уже есть: {self.cache_dir}")
            return
        print(f"[split] Запускаю split в {self.cache_dir}")
        self._do_split()

    def _on_split_clicked(self):
        if self.cache_dir is None:
            return
        self._do_split(force=True)

    def _do_split(self, force=False):
        if self.cache_dir is None:
            return

        if force and self.cache_dir.exists():
            import shutil
            shutil.rmtree(self.cache_dir, ignore_errors=True)

        self.cache_dir.mkdir(parents=True, exist_ok=True)

        progress = QProgressDialog(
            "Splitting maps to ASM...", "Cancel", 0,
            len(self.rom.data["maps"]), self
        )
        progress.setWindowTitle("Split to ASM")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        def callback(current, total, map_id):
            progress.setValue(current)
            progress.setLabelText(f"Splitting map {map_id:02d} ({current}/{total})...")
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()

        try:
            splitter.split_all_maps(self.rom, self.cache_dir, progress_callback=callback)
            (self.cache_dir / ".split_done").write_text("ok")
            progress.setValue(len(self.rom.data["maps"]))
            if force:
                QMessageBox.information(self, "Split to ASM",
                                        f"Готово!\n\nФайлы в:\n{self.cache_dir}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Split Error", str(e))
        finally:
            progress.close()

    def _on_open_folder(self):
        if self.cache_dir is None or not self.cache_dir.exists():
            return
        import subprocess
        import sys
        path = str(self.cache_dir)
        if sys.platform.startswith("win"):
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    # ============================================================
    #  Просмотр
    # ============================================================

    def _on_grid_toggled(self, checked: bool):
        """Включить/выключить сетку на карте."""
        if self.current_view:
            self.current_view.show_grid = checked
            self.current_view.update()

    def _current_scale(self):
        text = self.scale_combo.currentText()
        return {"1/4x": 0.25, "1/2x": 0.5, "1x": 1, "2x": 2, "4x": 4}.get(text, 1)

    def _on_scale_changed(self, _):
        if self.current_view:
            self.current_view.set_scale(self._current_scale())

    # ============================================================
    #  Редактирование карты
    # ============================================================

    def _on_block_selected(self, left_idx: int, right_idx: int):
        """Пользователь выбрал блок в BlocksetPanel.
        
        -1 в BlocksetPanel означает «не выбран» — сохраняем как есть.
        """
        self.paint_left = left_idx
        self.paint_right = right_idx

        # Курсор: крестик, если есть хоть один выбранный блок
        if self.current_view and self.current_view.editable:
            if left_idx >= 0 or right_idx >= 0:
                self.current_view.setCursor(Qt.CrossCursor)
            else:
                self.current_view.setCursor(Qt.ArrowCursor)

    def _on_paint_mode_changed(self, mask: int):
        """Сменился режим. Пока только запоминаем — само редактирование флагов позже."""
        self.paint_mode = mask
        print(f"[paint_mode] mask = 0x{mask:04X}")
        # Курсор: крестик, если есть хоть один активный режим
        if self.current_view and self.current_view.editable:
            if mask != 0 or self.paint_left >= 0 or self.paint_right >= 0:
                self.current_view.setCursor(Qt.CrossCursor)
            else:
                self.current_view.setCursor(Qt.ArrowCursor)

    def _get_paint_block(self, button):
        """Возвращает индекс блока для данной кнопки мыши.
        
        Возвращает -1, если:
          - блок для этой кнопки не выбран;
          - мы в режиме флагов (paint_mode != 0) — блоки не рисуем.
        """
        # Режим флагов — блоки запрещены
        if self.paint_mode != 0:
            return -1

        if button == Qt.LeftButton:
            return self.paint_left
        elif button == Qt.RightButton:
            return self.paint_right
        return -1

    def _on_block_painted(self, idx: int, old_val: int, new_val: int):
        """Пользователь нарисовал блок — пушим в undo."""
        self.undo_stack.append((idx, old_val, new_val))
        self.redo_stack.clear()
        self._update_undo_buttons()
        if hasattr(self, "parent") and hasattr(self.parent, "modify"):
            self.parent.modify()

    def _undo(self):
        if not self.undo_stack:
            return
        idx, old_val, new_val = self.undo_stack.pop()
        self.current_view.py_map.layoutData[idx] = old_val
        self.current_view.update()
        self.redo_stack.append((idx, old_val, new_val))
        self._update_undo_buttons()

    def _redo(self):
        if not self.redo_stack:
            return
        idx, old_val, new_val = self.redo_stack.pop()
        self.current_view.py_map.layoutData[idx] = new_val
        self.current_view.update()
        self.undo_stack.append((idx, old_val, new_val))
        self._update_undo_buttons()

    def _update_undo_buttons(self):
        self.undo_btn.setEnabled(bool(self.undo_stack))
        self.redo_btn.setEnabled(bool(self.redo_stack))


    def _on_map_selected(self, idx):
        if idx < 0:
            return

        py_map = self.rom.data["maps"][idx]
        if not getattr(py_map, "loaded", False):
            self.rom.getMaps(idx, idx)
            py_map = self.rom.data["maps"][idx]

        self.info_label.setText(
            f"Map {idx}  |  palette: {py_map.paletteIdx}  |  "
            f"blocks: {len(py_map.blocks)}  |  areas: {len(py_map.areas)}  |  "
            f"warps: {len(py_map.warps)}  |  items: {len(py_map.items)}"
        )

        palette = self.rom.data["palettes"][py_map.paletteIdx]
        view = SimpleMapView(
            py_map, palette,
            scale=self._current_scale(),
            editable=True,
            get_paint_block=self._get_paint_block,
        )
        view.show_grid = self.view_cbs["grid"].isChecked()
        view.blockPainted.connect(self._on_block_painted)
        self.current_view = view
        self.scroll_area.setWidget(view)

        # При смене карты undo/redo сбрасываем
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._update_undo_buttons()

        # Сбрасываем выбор блока (paint_left/right) перед загрузкой
        self.paint_left = -1
        self.paint_right = -1

        # Загружаем блоки в панель Blockset (внутри тоже эмитится blockSelected(-1,-1))
        self.blockset_panel.set_map(py_map, palette)

        self._refresh_all_tables(idx)

    def _refresh_all_tables(self, idx):
        if self.cache_dir is None:
            return
        map_dir = self.cache_dir / f"map{idx:02d}"
        if not map_dir.exists():
            return

        try:
            # Areas
            areas = parsers.parse_areas_asm(map_dir / "2-areas.asm")
            rows = []
            for i, a in enumerate(areas):
                rows.append([
                    i, a.layer1StartX, a.layer1StartY, a.layer1EndX, a.layer1EndY,
                    a.foregroundLayer2StartX, a.foregroundLayer2StartY,
                    a.backgroundLayer2StartX, a.backgroundLayer2StartY,
                    a.layer1ParallaxX, a.layer1ParallaxY,
                    a.layer2ParallaxX, a.layer2ParallaxY,
                    a.layer1AutoscrollX, a.layer1AutoscrollY,
                    a.layer2AutoscrollX, a.layer2AutoscrollY,
                    a.layerType, a.defaultMusic
                ])
            fill_table(self.areas_table, rows)
            print(f"[tables] Map {idx}: {len(areas)} areas")

            # Flag Copies
            flags = parsers.parse_flag_events_asm(map_dir / "3-flag-events.asm")
            rows = []
            for i, e in enumerate(flags):
                rows.append([
                    i, e.triggerX, parsers.get_flag_info(e.triggerX),
                    e.sourceStartX, e.sourceStartY, e.sourceEndX, e.sourceEndY,
                    e.destStartX, e.destStartY, e.comment or ""
                ])
            fill_table(self.flag_table, rows)
            print(f"[tables] Map {idx}: {len(flags)} flag copies")

            # Step Copies
            steps = parsers.parse_step_events_asm(map_dir / "4-step-events.asm")
            rows = []
            for i, e in enumerate(steps):
                rows.append([
                    i, e.triggerX, e.triggerY,
                    e.sourceStartX, e.sourceStartY, e.sourceEndX, e.sourceEndY,
                    e.destStartX, e.destStartY, e.comment or ""
                ])
            fill_table(self.step_table, rows)
            print(f"[tables] Map {idx}: {len(steps)} step copies")

            # Roof Copies
            roofs = parsers.parse_roof_events_asm(map_dir / "5-roof-events.asm")
            rows = []
            for i, e in enumerate(roofs):
                rows.append([
                    i, e.triggerX, e.triggerY,
                    e.sourceStartX, e.sourceStartY, e.sourceEndX, e.sourceEndY,
                    e.destStartX, e.destStartY, e.comment or ""
                ])
            fill_table(self.roof_table, rows)
            print(f"[tables] Map {idx}: {len(roofs)} roof copies")

            # Warps
            warps = parsers.parse_warps_asm(map_dir / "6-warp-events.asm")
            rows = []
            for i, w in enumerate(warps):
                rows.append([
                    i, w.triggerX, w.triggerY,
                    w.scrollDirection, w.destMap,
                    w.destX, w.destY, w.facing, w.comment or ""
                ])
            fill_table(self.warps_table, rows)
            print(f"[tables] Map {idx}: {len(warps)} warps")

            # Chest Items
            chests = parsers.parse_items_asm(map_dir / "7-chest-items.asm")
            rows = []
            for i, it in enumerate(chests):
                rows.append([
                    i, it.x, it.y, it.flag, parsers.get_flag_info(it.flag),
                    it.item, it.comment or ""
                ])
            fill_table(self.chest_table, rows)
            print(f"[tables] Map {idx}: {len(chests)} chest items")

            # Other Items
            others = parsers.parse_items_asm(map_dir / "8-other-items.asm")
            rows = []
            for i, it in enumerate(others):
                rows.append([
                    i, it.x, it.y, it.flag, parsers.get_flag_info(it.flag),
                    it.item, it.comment or ""
                ])
            fill_table(self.other_table, rows)
            print(f"[tables] Map {idx}: {len(others)} other items")

            # Animations
            anim_set = parsers.parse_animations_asm(map_dir / "9-animations.asm")
            rows = []
            for i, a in enumerate(anim_set.anims):
                rows.append([i, a.start, a.end, a.dest, a.delay])
            fill_table(self.anim_table, rows)
            print(f"[tables] Map {idx}: {len(anim_set.anims)} animations, "
                  f"tileset={anim_set.tilesetIdx}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[tables] Ошибка: {e}")