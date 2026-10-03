# sf2edit/promotions.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QComboBox, QListWidget, QListWidgetItem,
    QSpinBox, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

import rompanel


# ---------- ROM-адреса ----------
PROMO_BASE        = 0x21046
TOTAL_PROMOTIONS  = 17


CLASS_NAMES = [
    "SDMN", "KNTE", "WARR", "MAGE", "PRST", "ARCH", "BDMN", "WFMN",
    "RNGR", "PHNK", "THIF", "TORT", "HERO", "PLDN", "PGNT", "GLDT",
    "BRN",  "WIZ",  "SORC", "VICR", "MMNK", "SNIP", "BRGN", "BDBT",
    "WRBR", "BWKT", "PHNX", "NINJ", "MNST", "RBT",  "GLM",  "RDBN",
]

ITEM_NAMES = [
    "Medical Herb", "Healing Seed", "Healing Drop", "Antidote",
    "Angel Wing", "Fairy Powder", "Healing Water", "Fairy Tear",
    "Healing Rain", "Power Water", "Protect Milk", "Quick Chicken",
    "Running Pimento", "Cheerful Bread", "Bright Honey", "Brave Apple",
    "Shining Ball", "Blizzard", "Holy Thunder", "Power Ring",
    "Protect Ring", "Quick Ring", "Running Ring", "White Ring",
    "Black Ring", "Evil Ring", "Leather Glove", "Power Glove",
    "Brass Knuckles", "Iron Knuckles", "Misty Knuckles", "Giant Knuckles",
    "Evil Knuckles", "Short Axe", "Hand Axe", "Middle Axe",
    "Power Axe", "Battle Axe", "Large Axe", "Great Axe",
    "Heat Axe", "Atlas Axe", "Ground Axe", "Rune Axe",
    "Evil Axe", "Wooden Arrow", "Iron Arrow", "Steel Arrow",
    "Robin Arrow", "Assault Shell", "Great Shot", "Nazca Cannon",
    "Buster Shot", "Hyper Cannon", "Grand Cannon", "Evil Shot",
    "Wooden Stick", "Short Sword", "Middle Sword", "Long Sword",
    "Steel Sword", "Achilles Sword", "Broad Sword", "Buster Sword",
    "Great Sword", "Critical Sword", "Battle Sword", "Force Sword",
    "Counter Sword", "Levanter", "Dark Sword", "Wooden Sword",
    "Short Spear", "Bronze Lance", "Spear", "Steel Lance",
    "Power Spear", "Heavy Lance", "Javelin", "Chrome Lance",
    "Valkyrie", "Holy Lance", "Mist Javelin", "Halberd",
    "Evil Lance", "Wooden Rod", "Short Rod", "Bronze Rod",
    "Iron Rod", "Power Stick", "Flail", "Guardian Staff",
    "Indra Staff", "Mage Staff", "Wish Staff", "Great Rod",
    "Supply Staff", "Holy Staff", "Freeze Staff", "Goddess Staff",
    "Mystery Staff", "Demon Rod", "Iron Ball", "Short Knife",
    "Dagger", "Knife", "Thieve's Dagger", "Katana",
    "Ninja Katana", "Gisarme", "Taros Sword", "Right of Hope",
    "Wooden Pannel", "Sky Orb", "Cannon", "Dry Stone",
    "Dynamite", "Arm of Golem", "Pegasus Wing", "Warrior's Pride",
    "Silver Tank", "Secret Book", "Vigor Ball", "Mithril",
    "Life Ring", "Cotton Balloon", "Chirrup Sandles", "Empty",
]


class PromotionsPanel(rompanel.ROMPanel):
    frameTitle = "Promotions"
    canMaximize = False

    # ---------- init ----------
    def init(self):
        if self.rom is None:
            return

        self.loading = True
        self.promos = []          # список dict'ов: from,to,is_special,from_addr,to_addr,item
        self.promo_items = []     # список индексов предметов
        self.basic_count = 0
        self.special_count = 0
        self.promo_item_addr = 0

        self._load_from_rom()

        # ---------- List ----------
        sbs_list = QGroupBox("Promotions")
        ll = QVBoxLayout(sbs_list)
        ll.setContentsMargins(8, 8, 8, 8)

        self.promoList = QListWidget()
        self.promoList.setMinimumHeight(260)
        self.promoList.setMinimumWidth(420)
        self.promoList.currentRowChanged.connect(self.OnSelectPromo)
        ll.addWidget(self.promoList)

        # ---------- Edit From / To ----------
        edit = QHBoxLayout()
        self.fromCombo = QComboBox()
        self.fromCombo.setMinimumWidth(180)
        self.fromCombo.addItems(CLASS_NAMES)
        self.fromCombo.currentIndexChanged.connect(self.OnFromChanged)

        self.toCombo = QComboBox()
        self.toCombo.setMinimumWidth(180)
        self.toCombo.addItems(CLASS_NAMES)
        self.toCombo.currentIndexChanged.connect(self.OnToChanged)

        edit.addWidget(self.fromCombo)
        lbl_to = QLabel("to")
        lbl_to.setAlignment(Qt.AlignCenter)
        lbl_to.setFixedWidth(30)
        edit.addWidget(lbl_to)
        edit.addWidget(self.toCombo)
        ll.addLayout(edit)

        # ---------- Special item + Reallocate ----------
        bot = QHBoxLayout()

        sbs_item = QGroupBox("Special Promotion Item")
        il = QVBoxLayout(sbs_item)
        il.setContentsMargins(8, 8, 8, 8)
        self.specialItemCombo = QComboBox()
        self.specialItemCombo.setMinimumWidth(200)
        self.specialItemCombo.addItems(ITEM_NAMES)
        self.specialItemCombo.currentIndexChanged.connect(self.OnSpecialItemChanged)
        il.addWidget(self.specialItemCombo)

        sbs_realloc = QGroupBox("Number of Basic Promotions")
        rl = QHBoxLayout(sbs_realloc)
        rl.setContentsMargins(8, 8, 8, 8)
        self.basicCountSpin = QSpinBox()
        self.basicCountSpin.setRange(1, 17)
        self.basicCountSpin.setFixedWidth(60)
        self.reallocButton = QPushButton("Reallocate")
        self.reallocButton.clicked.connect(self.OnReallocate)
        rl.addWidget(self.basicCountSpin)
        rl.addWidget(self.reallocButton)

        bot.addWidget(sbs_item)
        bot.addWidget(sbs_realloc)
        bot.addStretch()
        ll.addLayout(bot)

        self.sizer.addWidget(sbs_list, 0, 0)

        self.loading = False
        self._rebuild_list()
        if self.promoList.count() > 0:
            self.promoList.setCurrentRow(0)

    # ---------- helpers ----------
    def _labelFont(self):
        f = QFont("MS Sans Serif", 9)
        f.setBold(False)
        return f

    def _ensure_curFileStr(self):
        if not hasattr(self.rom, "curFileStr"):
            try:
                self.rom.startWriteProcess()
            except Exception:
                pass

    def _write_byte(self, addr, value):
        self._ensure_curFileStr()
        try:
            self.rom.writeBytes(addr, "%02x" % (value & 0xFF))
        except Exception:
            pass

    # ---------- read ----------
    def _load_from_rom(self):
        self.promos = []
        self.promo_items = []

        N = int(self.rom.getBytes(PROMO_BASE, 1), 16)
        M = TOTAL_PROMOTIONS - N
        self.basic_count = N
        self.special_count = M

        bfrom_addr = PROMO_BASE + 1
        bto_addr   = PROMO_BASE + N + 2

        for i in range(N):
            self.promos.append({
                "from": int(self.rom.getBytes(bfrom_addr + i, 1), 16),
                "to":   int(self.rom.getBytes(bto_addr + i, 1), 16),
                "is_special": False,
                "from_addr": bfrom_addr + i,
                "to_addr":   bto_addr + i,
                "item": None,
            })

        sfrom_addr = PROMO_BASE + 2 * N + 3
        sto_addr   = PROMO_BASE + 2 * N + 4 + M

        for i in range(M):
            self.promos.append({
                "from": int(self.rom.getBytes(sfrom_addr + i, 1), 16),
                "to":   int(self.rom.getBytes(sto_addr + i, 1), 16),
                "is_special": True,
                "from_addr": sfrom_addr + i,
                "to_addr":   sto_addr + i,
                "item": None,
            })

        # promo items
        item_count_addr = PROMO_BASE + 2 * N + 2 * M + 4
        item_count = int(self.rom.getBytes(item_count_addr, 1), 16)
        items_base = item_count_addr + 1
        self.promo_item_addr = items_base
        for i in range(item_count):
            self.promo_items.append(int(self.rom.getBytes(items_base + i, 1), 16))

        # Связываем items со special promos
        for i, it in enumerate(self.promo_items):
            if i < M:
                self.promos[N + i]["item"] = it

    # ---------- UI ----------
    def _rebuild_list(self):
        self.loading = True
        try:
            cur = self.promoList.currentRow()
            self.promoList.clear()
            for i, p in enumerate(self.promos):
                f = CLASS_NAMES[p["from"]] if 0 <= p["from"] < len(CLASS_NAMES) else "???"
                t = CLASS_NAMES[p["to"]]   if 0 <= p["to"]   < len(CLASS_NAMES) else "???"
                marker = "  *" if p["is_special"] else ""
                self.promoList.addItem(f"{f} to {t}{marker}")
            if 0 <= cur < self.promoList.count():
                self.promoList.setCurrentRow(cur)
        finally:
            self.loading = False

        self.basicCountSpin.setValue(self.basic_count)

    # ---------- signals ----------
    def OnSelectPromo(self, row):
        if self.loading or row < 0 or row >= len(self.promos):
            return
        p = self.promos[row]
        self.loading = True
        try:
            self.fromCombo.setCurrentIndex(p["from"] if 0 <= p["from"] < 32 else 0)
            self.toCombo.setCurrentIndex(p["to"]     if 0 <= p["to"]   < 32 else 0)
            if p["is_special"]:
                self.specialItemCombo.setEnabled(True)
                if p["item"] is not None and 0 <= p["item"] < len(ITEM_NAMES):
                    self.specialItemCombo.setCurrentIndex(p["item"])
            else:
                self.specialItemCombo.setEnabled(False)
        finally:
            self.loading = False

    def OnFromChanged(self, idx):
        if self.loading or idx < 0:
            return
        row = self.promoList.currentRow()
        if row < 0:
            return
        p = self.promos[row]
        p["from"] = idx
        self._write_byte(p["from_addr"], idx)
        # обновляем строку
        f = CLASS_NAMES[idx]
        t = CLASS_NAMES[p["to"]] if 0 <= p["to"] < len(CLASS_NAMES) else "???"
        marker = "  *" if p["is_special"] else ""
        item = self.promoList.item(row)
        if item:
            item.setText(f"{f} to {t}{marker}")
        self._mark_modified()

    def OnToChanged(self, idx):
        if self.loading or idx < 0:
            return
        row = self.promoList.currentRow()
        if row < 0:
            return
        p = self.promos[row]
        p["to"] = idx
        self._write_byte(p["to_addr"], idx)
        f = CLASS_NAMES[p["from"]] if 0 <= p["from"] < len(CLASS_NAMES) else "???"
        t = CLASS_NAMES[idx]
        marker = "  *" if p["is_special"] else ""
        item = self.promoList.item(row)
        if item:
            item.setText(f"{f} to {t}{marker}")
        self._mark_modified()

    def OnSpecialItemChanged(self, idx):
        if self.loading or idx < 0:
            return
        row = self.promoList.currentRow()
        if row < 0:
            return
        p = self.promos[row]
        if not p["is_special"] or p["item"] is None:
            return
        p["item"] = idx
        self._write_byte(self.promo_item_addr + (row - self.basic_count), idx)
        self._mark_modified()

    # ---------- reallocate ----------
    def OnReallocate(self):
        new_N = self.basicCountSpin.value()
        new_M = TOTAL_PROMOTIONS - new_N

        # сохраняем текущие пары в порядке [basic..., special...]
        pairs = [(p["from"], p["to"]) for p in self.promos]
        items = list(self.promo_items)

        if len(pairs) != TOTAL_PROMOTIONS:
            QMessageBox.warning(self, "Reallocate",
                                "Внутренняя ошибка: не 17 промоушенов.")
            return

        # новый layout
        self.basic_count = new_N
        self.special_count = new_M

        # пересобираем promos
        self.promos = []
        for i in range(TOTAL_PROMOTIONS):
            is_special = i >= new_N
            self.promos.append({
                "from": pairs[i][0],
                "to":   pairs[i][1],
                "is_special": is_special,
                "from_addr": 0,  # пересчитаем ниже
                "to_addr":   0,
                "item": None,
            })

        # пересчитываем адреса
        bfrom_addr = PROMO_BASE + 1
        bto_addr   = PROMO_BASE + new_N + 2
        sfrom_addr = PROMO_BASE + 2 * new_N + 3
        sto_addr   = PROMO_BASE + 2 * new_N + 4 + new_M

        for i in range(new_N):
            self.promos[i]["from_addr"] = bfrom_addr + i
            self.promos[i]["to_addr"]   = bto_addr + i
        for i in range(new_M):
            idx = new_N + i
            self.promos[idx]["from_addr"] = sfrom_addr + i
            self.promos[idx]["to_addr"]   = sto_addr + i

        # promo items — те же, но адрес тот же (PROMO_BASE + 2N + 2M + 4 = +38 всегда)
        item_count_addr = PROMO_BASE + 2 * new_N + 2 * new_M + 4
        items_base = item_count_addr + 1
        self.promo_item_addr = items_base
        self.promo_items = items

        # привязка items к special promos
        for i, it in enumerate(items):
            if i < new_M:
                self.promos[new_N + i]["item"] = it

        # пишем всё в ROM
        self._ensure_curFileStr()
        self._write_byte(PROMO_BASE, new_N)
        self._write_byte(PROMO_BASE + new_N + 1, new_N)

        for p in self.promos:
            self._write_byte(p["from_addr"], p["from"])
            self._write_byte(p["to_addr"],   p["to"])

        s_count_addr = PROMO_BASE + 2 * new_N + 2
        self._write_byte(s_count_addr, new_M)
        self._write_byte(s_count_addr + new_M + 1, new_M)

        self._write_byte(item_count_addr, len(items))
        for i, it in enumerate(items):
            self._write_byte(items_base + i, it)

        self._rebuild_list()
        self.promoList.setCurrentRow(0)
        self._mark_modified()
        QMessageBox.information(self, "Reallocate", "Reallocation successful.")

    # ---------- internal ----------
    def _mark_modified(self):
        self.updateModifiedIndicator(True)
        try:
            self.parent.modify()
        except Exception:
            pass

    # ---------- panel hooks ----------
    def OnShow(self, event=None):
        pass

    def getCurrentData(self):
        return None

    def getCurrentSpriteObject(self):
        return None