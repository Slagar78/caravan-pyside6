# sf2edit/shops.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QComboBox, QListWidget, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

import rompanel
from sf2edit.items import ITEM_NAMES


# ---------- ROM-адреса ----------
STORE_START = 0x20878
STORE_END   = 0x20A01
STORE_SIZE  = STORE_END - STORE_START     # 393 байта

NUM_SHOPS   = 31
BONUS_IDX   = 30                          # индекс Bonus Shop


SHOP_NAMES = [
    "Weapon Merchant 1",  "Weapon Merchant 2",  "Weapon Merchant 3",
    "Weapon Merchant 4",  "Weapon Merchant 5",  "Weapon Merchant 6",
    "Weapon Merchant 7",  "Weapon Merchant 8",  "Weapon Merchant 9",
    "Weapon Merchant 10", "Weapon Merchant 11", "Weapon Merchant 12",
    "Weapon Merchant 13", "Weapon Merchant 14", "Weapon Merchant 15",
    "Item Merchant 1",  "Item Merchant 2",  "Item Merchant 3",
    "Item Merchant 4",  "Item Merchant 5",  "Item Merchant 6",
    "Item Merchant 7",  "Item Merchant 8",  "Item Merchant 9",
    "Item Merchant 10", "Item Merchant 11", "Item Merchant 12",
    "Item Merchant 13", "Item Merchant 14", "Item Merchant 15",
    "Bonus Shop",
]


# =========================================================
# Panel
# =========================================================
class ShopPanel(rompanel.ROMPanel):
    frameTitle = "Shops"
    canMaximize = False

    # ---------- init ----------
    def init(self):
        if self.rom is None:
            return

        self.loading = True
        self.curShop = 0

        if "shops" not in self.rom.data or not self.rom.data["shops"]:
            self.rom.data["shops"] = self._load_all()
        self.shops = self.rom.data["shops"]

        # ---------- Select ----------
        sbs_select = QGroupBox("Select")
        sel = QHBoxLayout(sbs_select)
        sel.setContentsMargins(8, 8, 8, 8)
        sel.setSpacing(8)

        self.shopList = QComboBox()
        self.shopList.setMinimumWidth(220)
        self.shopList.addItems(SHOP_NAMES)
        self.shopList.currentIndexChanged.connect(self.OnSelectShop)
        sel.addWidget(self.shopList)

        self.addSlotBtn = QPushButton("Add Slot")
        self.addSlotBtn.setFixedWidth(110)
        self.addSlotBtn.clicked.connect(self.OnAddSlot)
        sel.addWidget(self.addSlotBtn)

        self.removeSlotBtn = QPushButton("Remove Slot")
        self.removeSlotBtn.setFixedWidth(110)
        self.removeSlotBtn.clicked.connect(self.OnRemoveSlot)
        sel.addWidget(self.removeSlotBtn)
        sel.addStretch()

        # ---------- Inventory ----------
        sbs_inv = QGroupBox("Inventory")
        inv = QHBoxLayout(sbs_inv)
        inv.setContentsMargins(8, 8, 8, 8)
        inv.setSpacing(10)

        # Левая колонка: все предметы
        left = QVBoxLayout()
        lbl_all = QLabel("All Items"); lbl_all.setFont(self._labelFont())
        left.addWidget(lbl_all)
        self.allItems = QListWidget()
        self.allItems.setMinimumWidth(240)
        self.allItems.setMinimumHeight(320)
        for i, name in enumerate(ITEM_NAMES):
            self.allItems.addItem(f"{i}: {name}")
        left.addWidget(self.allItems)
        inv.addLayout(left, 1)

        # Средняя колонка: Add >>
        mid = QVBoxLayout()
        mid.addStretch()
        self.addBtn = QPushButton("Add >>")
        self.addBtn.setFixedWidth(90)
        self.addBtn.clicked.connect(self.OnAddItem)
        mid.addWidget(self.addBtn)
        mid.addStretch()
        inv.addLayout(mid, 0)

        # Правая колонка: содержимое магазина
        right = QVBoxLayout()
        lbl_shop = QLabel("Shop Stock"); lbl_shop.setFont(self._labelFont())
        right.addWidget(lbl_shop)
        self.shopInventory = QListWidget()
        self.shopInventory.setMinimumWidth(240)
        self.shopInventory.setMinimumHeight(320)
        right.addWidget(self.shopInventory)
        inv.addLayout(right, 1)

        # ---------- Layout ----------
        self.sizer.addWidget(sbs_select, 0, 0)
        self.sizer.addWidget(sbs_inv, 1, 0)
        self.sizer.setRowStretch(2, 1)

        self.loading = False
        self.changeShop(0)

    # ---------- helpers ----------
    def _labelFont(self):
        f = QFont("MS Sans Serif", 9); f.setBold(False); return f

    def _load_all(self):
        """Читает 31 магазин последовательно начиная с STORE_START."""
        result = []
        try:
            addr = STORE_START
            for _ in range(NUM_SHOPS):
                length = int(self.rom.getBytes(addr, 1), 16)
                items = []
                for j in range(length):
                    items.append(int(self.rom.getBytes(addr + 1 + j, 1), 16))
                result.append(items)
                addr += 1 + length
        except Exception:
            result = [[] for _ in range(NUM_SHOPS)]
        return result

    def _ensure_curFileStr(self):
        if not hasattr(self.rom, "curFileStr"):
            try: self.rom.startWriteProcess()
            except Exception: pass

    def _emit(self):
        """Пересобирает весь регион магазинов и пишет обратно в ROM."""
        self._ensure_curFileStr()
        buf = bytearray()
        for shop in self.shops:
            buf.append(len(shop) & 0xFF)
            for item in shop:
                buf.append(item & 0xFF)
        if len(buf) > STORE_SIZE:
            buf = buf[:STORE_SIZE]
        elif len(buf) < STORE_SIZE:
            buf.extend([0] * (STORE_SIZE - len(buf)))
        try:
            self.rom.writeBytes(STORE_START, bytes(buf).hex())
        except Exception:
            pass

    def _itemName(self, idx):
        return ITEM_NAMES[idx] if 0 <= idx < len(ITEM_NAMES) else f"Item {idx}"

    def _refresh(self):
        self.loading = True
        try:
            self.shopInventory.clear()
            for item in self.shops[self.curShop]:
                self.shopInventory.addItem(f"{item}: {self._itemName(item)}")
        finally:
            self.loading = False

        is_bonus = (self.curShop == BONUS_IDX)
        self.addSlotBtn.setEnabled(not is_bonus)
        self.removeSlotBtn.setEnabled(not is_bonus)

    # ---------- change ----------
    def changeShop(self, num=None):
        if num is not None:
            self.curShop = num
        if not (0 <= self.curShop < len(self.shops)):
            return
        self._refresh()
        self.updateModifiedIndicator(True)

    # ---------- signals ----------
    def OnSelectShop(self, idx):
        if self.loading: return
        self.changeShop(idx)

    def OnAddItem(self):
        row = self.allItems.currentRow()
        if row < 0:
            return
        target_row = self.shopInventory.currentRow()

        if target_row < 0:
            self.shops[self.curShop].append(row)
        else:
            self.shops[self.curShop][target_row] = row

        self._emit()
        self._refresh()
        if target_row < 0:
            self.shopInventory.setCurrentRow(len(self.shops[self.curShop]) - 1)
        else:
            self.shopInventory.setCurrentRow(target_row)
        self._mark_modified()

    def OnAddSlot(self):
        if self.curShop == BONUS_IDX:
            return
        if len(self.shops[BONUS_IDX]) <= 0:
            QMessageBox.warning(self, "Add Slot",
                                "No spare room in Bonus Shop to expand into.")
            return

        pos = self.shopInventory.currentRow()
        if pos < 0:
            pos = len(self.shops[self.curShop])

        self.shops[self.curShop].insert(pos, 0)      # добавляем пустой слот
        self.shops[BONUS_IDX].pop()                  # отнимаем 1 байт у Bonus Shop

        self._emit()
        self._refresh()
        self.shopInventory.setCurrentRow(pos)
        self._mark_modified()

    def OnRemoveSlot(self):
        if self.curShop == BONUS_IDX:
            return
        if len(self.shops[self.curShop]) <= 1:
            QMessageBox.warning(self, "Remove Slot",
                                "Cannot remove — shop must keep at least one item.")
            return

        pos = self.shopInventory.currentRow()
        if pos < 0:
            pos = len(self.shops[self.curShop]) - 1

        self.shops[self.curShop].pop(pos)            # удаляем выбранный слот
        self.shops[BONUS_IDX].append(0)              # возвращаем 1 байт Bonus Shop

        self._emit()
        self._refresh()
        if self.shops[self.curShop]:
            self.shopInventory.setCurrentRow(min(pos, len(self.shops[self.curShop]) - 1))
        self._mark_modified()

    # ---------- internal ----------
    def _mark_modified(self):
        self.updateModifiedIndicator(True)
        try: self.parent.modify()
        except Exception: pass

    # ---------- panel hooks ----------
    def OnShow(self, event=None):
        self._refresh()

    def getCurrentData(self): return None
    def getCurrentSpriteObject(self): return None