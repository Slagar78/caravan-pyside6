"""Редактор карт (ASM) — просмотр + split + таблицы (read-only)."""
import os
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLabel,
    QSplitter, QScrollArea, QComboBox, QMdiSubWindow,
    QPushButton, QProgressDialog, QMessageBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QCheckBox, QSizePolicy,
    QGridLayout, QSpinBox
)
from PySide6.QtCore import Qt, QTimer, QStandardPaths
from PySide6.QtGui import QPainter, QPixmap, QImage, QColor

import rompanel
import splitter
import parsers


def get_cache_dir(rom_path=None):
    base = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppLocalDataLocation
    )
    if not base:
        base = str(Path.home() / ".caravan")
    return Path(base) / "maps"


# ============================================================
#  Рендер карты
# ============================================================

class SimpleMapView(QWidget):
    BASE_BLOCK_SIZE = 24

    def __init__(self, py_map, palette, scale=1, parent=None):
        super().__init__(parent)
        self.py_map = py_map
        self.palette = palette
        self.scale = scale
        self.block_bmps = []
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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(32, 32, 32))
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

def build_view_panel() -> QWidget:
    w = QWidget()
    w.setMaximumWidth(220)
    layout = QVBoxLayout(w)
    layout.setContentsMargins(4, 4, 4, 4)

    # --- Основные ---
    g1 = QGroupBox("View")
    l1 = QVBoxLayout(g1)
    l1.setSpacing(2)
    l1.addWidget(QCheckBox("Show grid"))
    l1.addWidget(QCheckBox("Show priority"))
    l1.addWidget(QCheckBox("Exploration flags"))
    ind1 = QCheckBox("   Areas")
    ind2 = QCheckBox("   Warps")
    ind3 = QCheckBox("   Triggers")
    ind4 = QCheckBox("   Items")
    ind5 = QCheckBox("   Vehicles")
    for cb in (ind1, ind2, ind3, ind4, ind5):
        l1.addWidget(cb)
    l1.addWidget(QCheckBox("Flag Copies"))
    l1.addWidget(QCheckBox("Step Copies"))
    l1.addWidget(QCheckBox("Roof Copies"))
    l1.addWidget(QCheckBox("Preview anim"))
    layout.addWidget(g1)

    # --- Areas display ---
    g2 = QGroupBox("Areas display")
    l2 = QVBoxLayout(g2)
    l2.setSpacing(2)
    l2.addWidget(QCheckBox("Upper layer overlay"))
    l2.addWidget(QCheckBox("BG underlay"))
    l2.addWidget(QCheckBox("Simulate parallax\nand autoscroll"))
    layout.addWidget(g2)

    layout.addStretch()

    # Все чекбоксы выключены (заглушки)
    for cb in w.findChildren(QCheckBox):
        cb.setEnabled(False)

    return w


# ============================================================
#  Панель Blockset (слева от карты)
# ============================================================

class BlocksetPanel(QWidget):
    """Показывает все блоки карты в виде сетки (read-only).

    Порт Java-панели MapBlocksetLayoutPanel.
    Пока без выбора блока — только отображение.
    """

    BLOCK_SIZE = 24      # размер блока в пикселях (1x)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.blocks = []
        self.block_bmps = []
        self.tiles_per_row = 10

        # Заголовок
        header = QLabel("Blockset")
        header.setStyleSheet("font-weight: bold; padding: 4px;")

        # Скролл с сеткой блоков
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.inner = QWidget()
        self.inner.setStyleSheet("background: #2a2a2a;")
        self.grid = QGridLayout(self.inner)
        self.grid.setSpacing(0)
        self.grid.setContentsMargins(4, 4, 4, 4)
        self.scroll.setWidget(self.inner)

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
        layout.addLayout(btn_row)
        layout.addWidget(opts)

    def set_map(self, py_map, palette):
        """Загружает блоки карты и строит сетку миниатюр."""
        self.blocks = list(getattr(py_map, "blocks", []) or [])
        self.block_bmps = []

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
                self.block_bmps.append(QPixmap.fromImage(img))
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

            # Миниатюра блока
            cell = QLabel()
            cell.setPixmap(bmp)
            cell.setFixedSize(self.BLOCK_SIZE, self.BLOCK_SIZE)
            cell.setStyleSheet(CELL_STYLE)
            cell.setToolTip(f"Block {i}")
            self.grid.addWidget(cell, row, col + 1)

        # Растяжка по правому краю
        self.grid.setColumnStretch(cols + 1, 1)

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
        # Найти главный сплиттер и задать размеры
        if hasattr(self, "_main_splitter"):
            self._main_splitter.setSizes([150, 300, 900, 200])

    def init(self):
        # ============ Слева — список карт ============
        self.map_list = QListWidget()
        self.map_list.addItems(
            [f"Map {i:02d}" for i in range(len(self.rom.data["maps"]))]
        )
        self.map_list.currentRowChanged.connect(self._on_map_selected)

        left = QWidget()
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
        self.scale_combo.setCurrentIndex(2)
        self.scale_combo.currentIndexChanged.connect(self._on_scale_changed)
        top_bar.addWidget(self.scale_combo)

        top_bar.addSpacing(20)
        self.split_btn = QPushButton("Split to ASM")
        self.split_btn.clicked.connect(self._on_split_clicked)
        top_bar.addWidget(self.split_btn)

        self.open_folder_btn = QPushButton("Open ASM folder")
        self.open_folder_btn.clicked.connect(self._on_open_folder)
        top_bar.addWidget(self.open_folder_btn)

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
        self.blockset_panel.setMinimumWidth(300)
        self.blockset_panel.setMaximumWidth(340)

        # ============ Справа — View panel ============
        right_panel = build_view_panel()

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
        main_splitter.setSizes([150, 300, 900, 200])

        # ЗАПРЕЩАЕМ сжимать Blockset в 0 — сплиттер уже существует
        main_splitter.setCollapsible(1, False)

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

    def _current_scale(self):
        text = self.scale_combo.currentText()
        return {"1/4x": 0.25, "1/2x": 0.5, "1x": 1, "2x": 2, "4x": 4}.get(text, 1)

    def _on_scale_changed(self, _):
        if self.current_view:
            self.current_view.set_scale(self._current_scale())

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
        view = SimpleMapView(py_map, palette, scale=self._current_scale())
        self.current_view = view
        self.scroll_area.setWidget(view)

        # Загружаем блоки в панель Blockset
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