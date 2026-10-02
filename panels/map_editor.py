"""Редактор карт (ASM) — просмотр + split в ASM-файлы."""
import os
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLabel,
    QSplitter, QScrollArea, QComboBox, QMdiSubWindow,
    QPushButton, QProgressDialog, QMessageBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QTimer, QStandardPaths
from PySide6.QtGui import QPainter, QPixmap, QImage, QColor

import rompanel
import splitter
import parsers


def get_cache_dir(rom_path=None):
    """Папка кеша: %LOCALAPPDATA%/Caravan/maps/ (кроссплатформенно)."""
    base = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppLocalDataLocation
    )
    if not base:
        base = str(Path.home() / ".caravan")
    return Path(base) / "maps"


class SimpleMapView(QWidget):
    """Простой рендер карты из data.Map (Python-Caravan)."""

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


class AreasTable(QTableWidget):
    """Таблица Areas — порт MapAreaTableModel (read-only)."""

    COLUMNS = [
        "Index", "L1 X", "L1 Y", "L1 X'", "L1 Y'",
        "L2 FX", "L2 FY", "L2 BX", "L2 BY",
        "L1 PX", "L1 PY", "L2 PX", "L2 PY",
        "L1 SX", "L1 SY", "L2 SX", "L2 SY",
        "L1 Type", "Music"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels(self.COLUMNS)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

    def set_areas(self, areas: list):
        """Заполняет таблицу списком MapArea."""
        self.setRowCount(len(areas))
        for row, a in enumerate(areas):
            values = [
                row,
                a.layer1StartX, a.layer1StartY,
                a.layer1EndX, a.layer1EndY,
                a.foregroundLayer2StartX, a.foregroundLayer2StartY,
                a.backgroundLayer2StartX, a.backgroundLayer2StartY,
                a.layer1ParallaxX, a.layer1ParallaxY,
                a.layer2ParallaxX, a.layer2ParallaxY,
                a.layer1AutoscrollX, a.layer1AutoscrollY,
                a.layer2AutoscrollX, a.layer2AutoscrollY,
                a.layerType,
                a.defaultMusic,
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                if col != 18:  # все числовые, кроме Music
                    item.setTextAlignment(Qt.AlignCenter)
                self.setItem(row, col, item)


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
                return
            w = w.parentWidget()

    def init(self):
        # Список карт слева
        self.map_list = QListWidget()
        self.map_list.addItems(
            [f"Map {i:02d}" for i in range(len(self.rom.data["maps"]))]
        )
        self.map_list.currentRowChanged.connect(self._on_map_selected)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Maps:"))
        left_layout.addWidget(self.map_list)

        # Правая часть
        right = QWidget()
        right_layout = QVBoxLayout(right)

        # --- Верхняя панель ---
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

        right_layout.addLayout(top_bar)

        # --- Вертикальный сплиттер: карта сверху, вкладки снизу ---
        v_splitter = QSplitter(Qt.Vertical)

        # Верх — скролл с картой
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        v_splitter.addWidget(self.scroll_area)

        # Низ — вкладки
        self.tabs = QTabWidget()
        self.tabs.setMinimumHeight(180)

        # Вкладка Areas
        self.areas_table = AreasTable()
        self.tabs.addTab(self.areas_table, "Areas")

        # Заглушки для будущих вкладок
        for name in ["Flag Copies", "Step Copies", "Roof Copies", "Warps", "Items", "Animations"]:
            placeholder = QLabel(f"{name} — TODO")
            placeholder.setAlignment(Qt.AlignCenter)
            self.tabs.addTab(placeholder, name)

        v_splitter.addWidget(self.tabs)
        v_splitter.setSizes([600, 200])

        right_layout.addWidget(v_splitter)

        self.current_view = None

        # Главный сплиттер (карты слева | контент справа)
        splitter_widget = QSplitter(Qt.Horizontal)
        splitter_widget.addWidget(left)
        splitter_widget.addWidget(right)
        splitter_widget.setStretchFactor(0, 0)
        splitter_widget.setStretchFactor(1, 1)
        splitter_widget.setSizes([200, 800])

        self.sizer.addWidget(splitter_widget, 0, 0)

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
            QMessageBox.warning(self, "Split", "Не могу определить папку кеша.")
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
            progress.setLabelText(
                f"Splitting map {map_id:02d} ({current}/{total})..."
            )
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()

        try:
            splitter.split_all_maps(
                self.rom, self.cache_dir,
                progress_callback=callback
            )
            (self.cache_dir / ".split_done").write_text("ok")
            progress.setValue(len(self.rom.data["maps"]))

            if force:
                QMessageBox.information(
                    self, "Split to ASM",
                    f"Готово!\n\nФайлы в:\n{self.cache_dir}"
                )
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Split Error", str(e))
        finally:
            progress.close()

    def _on_open_folder(self):
        if self.cache_dir is None:
            return
        if not self.cache_dir.exists():
            QMessageBox.warning(self, "Open folder", "Папка ещё не создана.")
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
        if text == "1/4x": return 0.25
        if text == "1/2x": return 0.5
        if text == "1x":   return 1
        if text == "2x":   return 2
        if text == "4x":   return 4
        return 1

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
            f"Map {idx}  |  "
            f"palette: {py_map.paletteIdx}  |  "
            f"blocks: {len(py_map.blocks)}  |  "
            f"areas: {len(py_map.areas)}  |  "
            f"warps: {len(py_map.warps)}  |  "
            f"items: {len(py_map.items)}"
        )

        palette = self.rom.data["palettes"][py_map.paletteIdx]

        view = SimpleMapView(
            py_map, palette,
            scale=self._current_scale()
        )
        self.current_view = view
        self.scroll_area.setWidget(view)

        # --- Парсим ASM-файлы и заполняем таблицы ---
        self._refresh_tables(idx)

    def _refresh_tables(self, idx):
        """Читает ASM-файлы карты и заполняет таблицы."""
        if self.cache_dir is None:
            return
        map_dir = self.cache_dir / f"map{idx:02d}"
        if not map_dir.exists():
            print(f"[tables] Папка не найдена: {map_dir}")
            return

        # --- Areas ---
        try:
            areas_path = map_dir / "2-areas.asm"
            areas = parsers.parse_areas_asm(areas_path)
            self.areas_table.set_areas(areas)
            print(f"[tables] Map {idx}: распарсено {len(areas)} areas")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[tables] Ошибка парсинга areas: {e}")