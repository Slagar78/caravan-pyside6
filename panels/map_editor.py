"""Минимальный редактор карт (ASM) — только отображение."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLabel,
    QSplitter, QScrollArea, QComboBox, QMdiSubWindow
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QPixmap, QImage, QColor

import rompanel


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
        """Обновляет размер виджета под текущий масштаб."""
        size = int(64 * self.BASE_BLOCK_SIZE * self.scale)
        self.setFixedSize(size, size)

    def set_scale(self, scale):
        self.scale = scale
        self._update_size()
        self.update()

    def _rebuild(self):
        """Создаёт QPixmap для каждого блока (в 1x)."""
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


class MapEditorPanel(rompanel.ROMPanel):

    frameTitle = "Map Editor (ASM)"
    canMaximize = True

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(100, self._maximize_once)

    def _maximize_once(self):
        """Разворачивает MDI-подокно один раз при открытии."""
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

        # --- Верхняя панель с масштабом ---
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Scale:"))

        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["1/4x", "1/2x", "1x", "2x", "4x"])
        self.scale_combo.setCurrentIndex(2)  # 1x по умолчанию
        self.scale_combo.currentIndexChanged.connect(self._on_scale_changed)
        top_bar.addWidget(self.scale_combo)

        top_bar.addStretch()

        self.info_label = QLabel("Select a map...")
        top_bar.addWidget(self.info_label)

        right_layout.addLayout(top_bar)

        # --- Скролл с картой ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        right_layout.addWidget(self.scroll_area)

        self.current_view = None

        # Сплиттер
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([200, 800])

        self.sizer.addWidget(splitter, 0, 0)

        QTimer.singleShot(100, lambda: self.map_list.setCurrentRow(0))

    def _current_scale(self):
        """Преобразует текст комбобокса в числовой множитель."""
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