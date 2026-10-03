# sf2edit/items.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QComboBox, QLineEdit, QCheckBox,
    QSpinBox, QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

import rompanel


# ---------- ROM-адреса ----------
ADDR_PITEM_PTR     = 65676         # pItemData  = LoadPointer(65676)
ADDR_ITEMNAMES_PTR = 65668         # pItemNames = LoadPointer(65668)

NUM_ITEMS          = 128
ITEM_NAME_OFFSET   = 0             # items первыми в банке имён


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

CLASS_NAMES = [
    "SDMN", "KNTE", "WARR", "MAGE", "PRST", "ARCH", "BDMN", "WFMN",
    "RNGR", "PHNK", "THIF", "TORT", "HERO", "PLDN", "PGNT", "GLDT",
    "BRN",  "WIZ",  "SORC", "VICR", "MMNK", "SNIP", "BRGN", "BDBT",
    "WRBR", "BWKT", "PHNX", "NINJ", "MNST", "RBT",  "GLM",  "RDBN",
]

ITEM_TYPES = {
    0x00: "Empty",
    0x02: "Normal Weapon",
    0x08: "Special Item",
    0x0A: "Special Weapon",
    0x0C: "Normal Ring",
    0x18: "Story Item",
    0x1A: "Force Sword",
    0x20: "Normal Item",
    0x28: "Battle Item",
    0x4A: "Cursed - Glove Axe Shot Lance",
    0x82: "Indra Staff?",
    0x8A: "Magic Weapon",
    0x8C: "Magic Ring",
    0xCA: "Cursed - Sword Rod",
    0xCC: "Cursed Ring",
}

ATTRIBUTE_CODES = {
    0:  "Nothing",
    1:  "Evade Up?",
    2:  "Critical Up",
    3:  "Double Attack Up?",
    4:  "Counter Up",
    5:  "???",
    6:  "Attack Up",
    7:  "Defense Up",
    8:  "Agility Up",
    9:  "Move Up",
    10: "Attack Down",
    11: "Defense Down",
    12: "Agility Down",
    13: "Move Down",
    14: "Instant Kill?",
}

# Из SpellCodes.txt — code → имя
SPELL_CODES = {
    0x00: "Heal 1",     0x01: "Aura 1",      0x02: "Detox 1",
    0x03: "Boost 1",    0x04: "Slow 1",      0x05: "Attack 1",
    0x06: "Dispel 1",   0x07: "Muddle 1",    0x08: "Desoul 1",
    0x09: "Sleep 1",    0x0A: "Egress 1",    0x0B: "Blaze 1",
    0x0C: "Freeze 1",   0x0D: "Bolt 1",      0x0E: "Blast 1",
    0x0F: "Magic Drain",0x10: "Medical Herb",0x11: "Flame Breath",
    0x12: "Snow Breath",0x13: "Demon Breath",0x14: "Power Water",
    0x15: "Protect Milk",0x16: "Quick Chicken",0x17: "Running Pimento",
    0x18: "Cheerful Bread",0x19: "Burst Rock",0x1A: "Laser",
    0x1B: "Katon 1",    0x1C: "Raijin 1",    0x1D: "Dao 1",
    0x1E: "Apollo 1",   0x1F: "Neptune 1",   0x20: "Atlas 1",
    0x21: "Fairy Powder",0x22: "Restore MP?",0x23: "Bright Honey",
    0x24: "Brave Apple",0x25: "Shining Ball",0x26: "Blizzard",
    0x27: "Holy Thunder",0x28: "Kraken Bubble Breath",
    0x29: "Kiwi Flame Breath",0x2A: "Right of Hope",
    0x2B: "Odd Eye Laser",0x37: "Freeze Game",0x3F: "Nothing",

    0x40: "Heal 2",     0x41: "Aura 2",      0x42: "Detox 2",
    0x43: "Boost 2",    0x44: "Slow 2",      0x45: "Attack Boost",
    0x47: "Muddle 2",   0x48: "Desoul 2",    0x49: "Ally Sleep",
    0x4A: "Fairy of Nothing (Egress 2?)",   0x4B: "Blaze 2",
    0x4C: "Freeze 2",   0x4D: "Bolt 2",      0x4E: "Blast 2",
    0x4F: "MP Ally Absorb",0x50: "Healing Seed",
    0x51: "Flame Breath 2",0x52: "Snow Breath 2",
    0x53: "Demon Breath 2",0x54: "Attack Increase",
    0x55: "Defense Increase",0x56: "Agility Increase",
    0x57: "Move Increase",0x58: "Max HP Increase",
    0x5B: "Katon 2",    0x5C: "Raijin 2",    0x5D: "Dao 2",
    0x5E: "Apollo 2",   0x5F: "Neptune 2",   0x60: "Atlas 2",
    0x62: "Fairy Tear", 0x63: "Max MP Increase",0x64: "Level Up",
    0x66: "Damage Fairy",0x68: "Bubble Breath",
    0x69: "Kiwi Flame Breath 2",0x6A: "MP Recover",

    0x80: "Heal 3",     0x81: "Aura 3",      0x82: "Detox 3",
    0x83: "Boost Item", 0x84: "Unboost Item",0x85: "Attack Item",
    0x86: "Silence Fairy",0x87: "Muddle Fairy",0x88: "Desoul Fairy",
    0x89: "Sleep Fairy",0x8B: "Blaze 3",     0x8C: "Freeze 3",
    0x8D: "Bolt 3",     0x8E: "Blast 3",     0x8F: "MP Absorb Fairy",
    0x90: "Healing Drop",0x91: "Flame Breath 3",
    0x92: "Snow Breath 3",0x94: "Attack Increase",
    0x95: "Defense Increase",0x96: "Agility Increase",
    0x97: "Move Increase",0x98: "Max HP Increase",
    0x9B: "Katon 3",    0x9C: "Raijin 3",    0xA2: "MP Restore",
    0xA3: "Max MP Increase",0xA4: "Level Up",
    0xA9: "Kiwi Flame Breath 3",

    0xC0: "Heal 4",     0xC1: "Aura 4",      0xC2: "Detox 4",
    0xC3: "Adjacent Boost",0xC4: "Adjacent Unboost",0xCB: "Blaze 4",
    0xCC: "Freeze 4",   0xCD: "Bolt 4",      0xCE: "Blast 4",
    0xCF: "MP Absorb Fairy",0xE9: "Kiwi Flame Breath 4",
}


# ---------- helpers ----------
def read_pointer(rom, ptr_addr):
    """SF2-style 3-byte BE pointer, stored at ptr_addr+1..ptr_addr+3."""
    return int(rom.getBytes(ptr_addr + 1, 3), 16)


class Item:
    __slots__ = ("addr", "equip", "min_range", "max_range", "value",
                 "type", "spell", "attr1_code", "attr1_val",
                 "attr2_code", "attr2_val", "modified")

    def __init__(self, addr=0):
        self.addr = addr
        self.equip = [0, 0, 0, 0]
        self.min_range = 0
        self.max_range = 0
        self.value = 0
        self.type = 0
        self.spell = 0
        self.attr1_code = 0
        self.attr1_val = 0
        self.attr2_code = 0
        self.attr2_val = 0
        self.modified = False

    @classmethod
    def from_rom(cls, rom, addr):
        raw = rom.getBytes(addr, 16)
        it = cls(addr=addr)
        it.equip = [int(raw[0:2], 16), int(raw[2:4], 16),
                    int(raw[4:6], 16), int(raw[6:8], 16)]
        it.max_range   = int(raw[8:10], 16)
        it.min_range   = int(raw[10:12], 16)
        it.value       = (int(raw[12:14], 16) << 8) | int(raw[14:16], 16)
        it.type        = int(raw[16:18], 16)
        it.spell       = int(raw[18:20], 16)
        it.attr1_code  = int(raw[20:22], 16)
        it.attr1_val   = int(raw[22:24], 16)
        it.attr2_code  = int(raw[24:26], 16)
        it.attr2_val   = int(raw[26:28], 16)
        return it

    def to_hex(self):
        b  = "%02x%02x%02x%02x" % tuple(self.equip)
        b += "%02x" % (self.max_range & 0xFF)
        b += "%02x" % (self.min_range & 0xFF)
        b += "%04x" % (self.value & 0xFFFF)
        b += "%02x" % (self.type & 0xFF)
        b += "%02x" % (self.spell & 0xFF)
        b += "%02x%02x" % (self.attr1_code & 0xFF, self.attr1_val & 0xFF)
        b += "%02x%02x" % (self.attr2_code & 0xFF, self.attr2_val & 0xFF)
        b += "0000"
        return b


# =========================================================
# Panel
# =========================================================
class ItemPanel(rompanel.ROMPanel):
    frameTitle = "Items"
    canMaximize = False

    def init(self):
        if self.rom is None:
            return

        self.loading = True
        self.item = None
        self.curItemIdx = 0
        self.sort_by_name = False

        if "items_full" not in self.rom.data or not self.rom.data["items_full"]:
            self.rom.data["items_full"] = self._load_all_items()
        self.items = self.rom.data["items_full"]

        # ---------- Select ----------
        sbs_select = QGroupBox("Select")
        sel = QHBoxLayout(sbs_select)
        sel.setContentsMargins(8, 8, 8, 8)
        sel.setSpacing(8)

        self.itemList = QComboBox()
        self.itemList.setMinimumWidth(220)
        self._populate_list()
        self.itemList.currentIndexChanged.connect(self.OnSelectItem)
        sel.addWidget(self.itemList)

        self.renameButton = QPushButton("Rename")
        self.renameButton.setFixedWidth(90)
        self.renameButton.clicked.connect(self.OnRename)
        sel.addWidget(self.renameButton)

        self.sortNameButton = QPushButton("Sort by Name")
        self.sortNameButton.setFixedWidth(120)
        self.sortNameButton.clicked.connect(self.OnSortByName)
        sel.addWidget(self.sortNameButton)

        self.sortIndexButton = QPushButton("Sort by Index")
        self.sortIndexButton.setFixedWidth(120)
        self.sortIndexButton.clicked.connect(self.OnSortByIndex)
        sel.addWidget(self.sortIndexButton)
        sel.addStretch()

        # ---------- Info ----------
        sbs_info = QGroupBox()
        info = QGridLayout(sbs_info)
        info.setContentsMargins(14, 14, 14, 14)
        info.setHorizontalSpacing(10)
        info.setVerticalSpacing(8)

        lbl_a1 = QLabel("Attribute 1")
        lbl_a1.setFont(self._labelFont())
        self.attr1Combo = QComboBox()
        for code in sorted(ATTRIBUTE_CODES.keys()):
            self.attr1Combo.addItem(ATTRIBUTE_CODES[code], code)
        self.attr1Combo.currentIndexChanged.connect(self.OnAttr1CodeChanged)
        self.attr1Spin = QSpinBox()
        self.attr1Spin.setRange(0, 255)
        self.attr1Spin.setMaximumWidth(70)
        self.attr1Spin.valueChanged.connect(self.OnAttr1ValChanged)

        lbl_a2 = QLabel("Attribute 2")
        lbl_a2.setFont(self._labelFont())
        self.attr2Combo = QComboBox()
        for code in sorted(ATTRIBUTE_CODES.keys()):
            self.attr2Combo.addItem(ATTRIBUTE_CODES[code], code)
        self.attr2Combo.currentIndexChanged.connect(self.OnAttr2CodeChanged)
        self.attr2Spin = QSpinBox()
        self.attr2Spin.setRange(0, 255)
        self.attr2Spin.setMaximumWidth(70)
        self.attr2Spin.valueChanged.connect(self.OnAttr2ValChanged)

        lbl_min = QLabel("Min Range")
        lbl_min.setFont(self._labelFont())
        self.minSpin = QSpinBox()
        self.minSpin.setRange(0, 255)
        self.minSpin.setMaximumWidth(70)
        self.minSpin.valueChanged.connect(self.OnMinChanged)

        lbl_max = QLabel("Max Range")
        lbl_max.setFont(self._labelFont())
        self.maxSpin = QSpinBox()
        self.maxSpin.setRange(0, 255)
        self.maxSpin.setMaximumWidth(70)
        self.maxSpin.valueChanged.connect(self.OnMaxChanged)

        lbl_type = QLabel("Type")
        lbl_type.setFont(self._labelFont())
        self.typeCombo = QComboBox()
        for code in sorted(ITEM_TYPES.keys()):
            self.typeCombo.addItem(ITEM_TYPES[code], code)
        self.typeCombo.currentIndexChanged.connect(self.OnTypeChanged)

        lbl_spell = QLabel("Spell")
        lbl_spell.setFont(self._labelFont())
        self.spellCombo = QComboBox()
        for code in sorted(SPELL_CODES.keys()):
            self.spellCombo.addItem(SPELL_CODES[code], code)
        self.spellCombo.currentIndexChanged.connect(self.OnSpellChanged)

        lbl_val = QLabel("Value (GP)")
        lbl_val.setFont(self._labelFont())
        self.valueSpin = QSpinBox()
        self.valueSpin.setRange(0, 65535)
        self.valueSpin.setMaximumWidth(100)
        self.valueSpin.valueChanged.connect(self.OnValueChanged)

        info.addWidget(lbl_a1, 0, 0);   info.addWidget(self.attr1Combo, 0, 1)
        info.addWidget(self.attr1Spin, 0, 2)
        info.addWidget(lbl_a2, 1, 0);   info.addWidget(self.attr2Combo, 1, 1)
        info.addWidget(self.attr2Spin, 1, 2)
        info.addWidget(lbl_min, 2, 0);  info.addWidget(self.minSpin, 2, 1)
        info.addWidget(lbl_max, 3, 0);  info.addWidget(self.maxSpin, 3, 1)
        info.addWidget(lbl_val, 4, 0);  info.addWidget(self.valueSpin, 4, 1)
        info.addWidget(lbl_type, 0, 3); info.addWidget(self.typeCombo, 0, 4, 1, 2)
        info.addWidget(lbl_spell, 1, 3);info.addWidget(self.spellCombo, 1, 4, 1, 2)
        info.setColumnStretch(1, 1)
        info.setColumnStretch(4, 1)

        # ---------- Equipable ----------
        sbs_equip = QGroupBox("Equipable Class")
        eq = QGridLayout(sbs_equip)
        eq.setContentsMargins(14, 14, 14, 14)
        eq.setHorizontalSpacing(20)
        eq.setVerticalSpacing(4)

        self.equipChecks = []
        for i, name in enumerate(CLASS_NAMES):
            cb = QCheckBox(name)
            cb.toggled.connect(self.OnEquipChanged)
            self.equipChecks.append(cb)
            eq.addWidget(cb, i % 8, i // 8)

        # ---------- Layout ----------
        self.sizer.addWidget(sbs_select, 0, 0)
        self.sizer.addWidget(sbs_info, 1, 0)
        self.sizer.addWidget(sbs_equip, 2, 0)
        self.sizer.setRowStretch(3, 1)

        self.loading = False
        self.changeItem(0)

    # ---------- helpers ----------
    def _labelFont(self):
        f = QFont("MS Sans Serif", 9)
        f.setBold(False)
        return f

    def _load_all_items(self):
        result = []
        try:
            pIt = read_pointer(self.rom, ADDR_PITEM_PTR)
            for i in range(NUM_ITEMS):
                result.append(Item.from_rom(self.rom, pIt + i * 16))
        except Exception:
            for _ in range(NUM_ITEMS):
                result.append(Item(addr=0))
        return result

    def _ensure_curFileStr(self):
        if not hasattr(self.rom, "curFileStr"):
            try:
                self.rom.startWriteProcess()
            except Exception:
                pass

    def _flushItem(self, it):
        if not it or not it.addr:
            return
        try:
            self._ensure_curFileStr()
            self.rom.writeBytes(it.addr, it.to_hex())
        except Exception:
            pass

    def _populate_list(self):
        self.loading = True
        try:
            self.itemList.clear()
            if self.sort_by_name:
                entries = sorted(range(NUM_ITEMS), key=lambda i: ITEM_NAMES[i].lower())
            else:
                entries = list(range(NUM_ITEMS))
            for i in entries:
                self.itemList.addItem(f"{i}: {ITEM_NAMES[i]}", i)
        finally:
            self.loading = False

    # ---------- item name (ROM bank, pItemNames @ 0) ----------
    def _name_addr(self, item_idx):
        addr = read_pointer(self.rom, ADDR_ITEMNAMES_PTR)
        for i in range(item_idx):
            length = int(self.rom.getBytes(addr, 1), 16)
            addr += 1 + length
            if i == 127:
                addr += 1
        return addr

    def _set_item_name(self, item_idx, new_name):
        addr = self._name_addr(item_idx)
        old_len = int(self.rom.getBytes(addr, 1), 16)
        if len(new_name) != old_len:
            raise ValueError(f"Длина должна остаться {old_len}")
        self._ensure_curFileStr()
        self.rom.writeBytes(addr + 1, new_name.encode("ascii").hex())

    # ---------- item data ----------
    def changeItem(self, num=None):
        if num is not None:
            self.curItemIdx = num

        if not (0 <= self.curItemIdx < len(self.items)):
            self.item = None
            return

        self.item = self.items[self.curItemIdx]
        it = self.item

        self.loading = True
        try:
            self._set_combo_by_code(self.attr1Combo, it.attr1_code)
            self.attr1Spin.setValue(it.attr1_val)

            self._set_combo_by_code(self.attr2Combo, it.attr2_code)
            self.attr2Spin.setValue(it.attr2_val)

            self.minSpin.setValue(it.min_range)
            self.maxSpin.setValue(it.max_range)
            self.valueSpin.setValue(it.value)

            self._set_combo_by_code(self.typeCombo, it.type)
            self._set_combo_by_code(self.spellCombo, it.spell)

            # Equip checks
            for i, cb in enumerate(self.equipChecks):
                byte_idx = 3 - (i // 8)
                bit = 1 << (i % 8)
                cb.setChecked(bool(it.equip[byte_idx] & bit))
        finally:
            self.loading = False

        self.updateModifiedIndicator(getattr(it, "modified", False))

    def _set_combo_by_code(self, combo, code):
        for i in range(combo.count()):
            if combo.itemData(i) == code:
                combo.setCurrentIndex(i)
                return
        combo.setCurrentIndex(-1)

    # ---------- signals ----------
    def OnSelectItem(self, _idx):
        if self.loading:
            return
        data = self.itemList.currentData()
        if data is None:
            return
        self.changeItem(data)

    def OnSortByName(self):
        self.sort_by_name = True
        self._populate_list()
        # восстановить текущий выбор
        for i in range(self.itemList.count()):
            if self.itemList.itemData(i) == self.curItemIdx:
                self.itemList.setCurrentIndex(i)
                break

    def OnSortByIndex(self):
        self.sort_by_name = False
        self._populate_list()
        self.itemList.setCurrentIndex(self.curItemIdx)

    def OnAttr1CodeChanged(self, _idx):
        if self.loading or self.item is None:
            return
        code = self.attr1Combo.currentData()
        if code is None:
            return
        self.item.attr1_code = code
        self.item.modified = True
        self._flushItem(self.item)
        self._mark_modified()

    def OnAttr1ValChanged(self, v):
        if self.loading or self.item is None:
            return
        self.item.attr1_val = v
        self.item.modified = True
        self._flushItem(self.item)
        self._mark_modified()

    def OnAttr2CodeChanged(self, _idx):
        if self.loading or self.item is None:
            return
        code = self.attr2Combo.currentData()
        if code is None:
            return
        self.item.attr2_code = code
        self.item.modified = True
        self._flushItem(self.item)
        self._mark_modified()

    def OnAttr2ValChanged(self, v):
        if self.loading or self.item is None:
            return
        self.item.attr2_val = v
        self.item.modified = True
        self._flushItem(self.item)
        self._mark_modified()

    def OnMinChanged(self, v):
        if self.loading or self.item is None:
            return
        self.item.min_range = v
        self.item.modified = True
        self._flushItem(self.item)
        self._mark_modified()

    def OnMaxChanged(self, v):
        if self.loading or self.item is None:
            return
        self.item.max_range = v
        self.item.modified = True
        self._flushItem(self.item)
        self._mark_modified()

    def OnValueChanged(self, v):
        if self.loading or self.item is None:
            return
        self.item.value = v
        self.item.modified = True
        self._flushItem(self.item)
        self._mark_modified()

    def OnTypeChanged(self, _idx):
        if self.loading or self.item is None:
            return
        code = self.typeCombo.currentData()
        if code is None:
            return
        self.item.type = code
        self.item.modified = True
        self._flushItem(self.item)
        self._mark_modified()

    def OnSpellChanged(self, _idx):
        if self.loading or self.item is None:
            return
        code = self.spellCombo.currentData()
        if code is None:
            return
        self.item.spell = code
        self.item.modified = True
        self._flushItem(self.item)
        self._mark_modified()

    def OnEquipChanged(self, _checked):
        if self.loading or self.item is None:
            return
        eq = [0, 0, 0, 0]
        for i, cb in enumerate(self.equipChecks):
            if cb.isChecked():
                byte_idx = 3 - (i // 8)
                bit = 1 << (i % 8)
                eq[byte_idx] |= bit
        self.item.equip = eq
        self.item.modified = True
        self._flushItem(self.item)
        self._mark_modified()

    # ---------- rename ----------
    def OnRename(self):
        if self.item is None:
            return
        idx = self.curItemIdx
        old_name = ITEM_NAMES[idx]
        max_len = len(old_name)

        new_name, ok = QInputDialog.getText(
            self, "Rename",
            f"Новое имя для предмета '{old_name}' (не длиннее {max_len}):",
            text=old_name,
        )
        if not ok:
            return
        new_name = new_name.strip()
        if not new_name:
            return

        if len(new_name) > max_len:
            QMessageBox.warning(
                self, "Rename",
                f"Слишком длинное имя.\nМаксимум — {max_len} символов."
            )
            return

        padded = new_name.ljust(max_len)
        try:
            self._set_item_name(idx, padded)
        except Exception as e:
            QMessageBox.critical(self, "Rename", f"Не удалось записать:\n{e}")
            return

        ITEM_NAMES[idx] = new_name
        # обновляем строку в combo
        for i in range(self.itemList.count()):
            if self.itemList.itemData(i) == idx:
                self.itemList.setItemText(i, f"{idx}: {new_name}")
                break
        self.item.modified = True
        self._mark_modified()

    # ---------- internal ----------
    def _mark_modified(self):
        self.updateModifiedIndicator(True)
        try:
            self.parent.modify()
        except Exception:
            pass

    # ---------- panel hooks ----------
    def OnShow(self, event=None):
        if self.item is not None:
            self.changeItem(self.curItemIdx)

    def getCurrentData(self):
        return getattr(self, "item", None)

    def getCurrentSpriteObject(self):
        return getattr(self, "item", None)

    changeSelection = changeItem