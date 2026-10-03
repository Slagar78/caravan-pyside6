# caravan-pyside6/data/characters.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QComboBox, QLineEdit, QListWidget,
    QCheckBox, QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

import rompanel


# ---------- ROM-адреса ----------
ADDR_PJOIN_PTR     = 0x1EE008      # pJoinData
ADDR_SPELLNAMES_PTR= 33476         # pSpellNames (LoadPointer(33476))
ADDR_ITEMNAMES_PTR = 65668         # pItemNames  (LoadPointer(65668))

NUM_CHARACTERS     = 30
PERSON_NAME_OFFSET = 44            # hero names start at index 44 in the spell-name bank


CHARACTER_NAMES = [
    "BOWIE", "SARAH", "CHESTER", "JAHA", "KAZIN", "SLADE",
    "KIWI", "PETER", "MAY", "GERHALT", "LUKE", "ROHDE",
    "RICK", "ELRIC", "ERIC", "KARNA", "RANDOLF", "TYRIN",
    "JANET", "HIGINS", "SKREECH", "TAYA", "FRAYJA", "JARO",
    "GYAN", "SHEELA", "ZYNK", "CHAZ", "LEMON", "CLAUDE",
]

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


# ---------- helpers ----------
def read_pointer(rom, ptr_addr):
    """SF2-style 3-byte BE pointer, stored at ptr_addr+1..ptr_addr+3."""
    return int(rom.getBytes(ptr_addr + 1, 3), 16)


class Character:
    __slots__ = ("addr", "class_idx", "level", "items", "modified")

    def __init__(self, addr=0, class_idx=0, level=1, items=None):
        self.addr = addr
        self.class_idx = class_idx
        self.level = level
        self.items = list(items) if items else [0, 0, 0, 0]
        self.modified = False

    @classmethod
    def from_rom(cls, rom, addr):
        raw = rom.getBytes(addr, 6)
        return cls(
            addr=addr,
            class_idx=int(raw[0:2], 16),
            level=int(raw[2:4], 16),
            items=[
                int(raw[4:6],   16),
                int(raw[6:8],   16),
                int(raw[8:10],  16),
                int(raw[10:12], 16),
            ],
        )

    def to_hex(self):
        b = "%02x%02x" % (self.class_idx & 0xFF, self.level & 0xFF)
        for it in self.items:
            b += "%02x" % (it & 0xFF)
        return b


# =========================================================
# Panel
# =========================================================
class CharacterPanel(rompanel.ROMPanel):
    frameTitle = "Character Start Data"
    canMaximize = False

    # ---------- init ----------
    def init(self):
        if self.rom is None:
            return

        self.loading = True
        self.character = None
        self.curCharacterIdx = 0
        self.curItemSlot = -1

        # кэш
        if "characters" not in self.rom.data or not self.rom.data["characters"]:
            self.rom.data["characters"] = self._load_all_characters()
        self.characters = self.rom.data["characters"]

        # ---------- Select ----------
        sbs_select = QGroupBox("Select")
        sel = QHBoxLayout(sbs_select)
        sel.setContentsMargins(8, 8, 8, 8)
        sel.setSpacing(8)

        self.characterList = QComboBox()
        self.characterList.setMinimumWidth(220)
        self.characterList.addItems(CHARACTER_NAMES)
        self.characterList.currentIndexChanged.connect(self.OnSelectCharacter)
        sel.addWidget(self.characterList)

        self.renameButton = QPushButton("Rename")
        self.renameButton.setFixedWidth(90)
        self.renameButton.clicked.connect(self.OnRename)
        sel.addWidget(self.renameButton)
        sel.addStretch()

        # ---------- Class / Level ----------
        sbs_class = QGroupBox()
        cl = QGridLayout(sbs_class)
        cl.setContentsMargins(14, 14, 14, 14)
        cl.setHorizontalSpacing(10)
        cl.setVerticalSpacing(12)

        lbl_class = QLabel("Class")
        lbl_class.setFont(self._labelFont())
        self.classCombo = QComboBox()
        self.classCombo.setMinimumWidth(180)
        self.classCombo.addItems(CLASS_NAMES)
        self.classCombo.currentIndexChanged.connect(self.OnClassChanged)

        lbl_level = QLabel("Level")
        lbl_level.setFont(self._labelFont())
        self.levelEdit = QLineEdit()
        self.levelEdit.setMaximumWidth(45)
        self.levelEdit.setMaxLength(3)
        self.levelEdit.setAlignment(Qt.AlignCenter)
        self.levelEdit.editingFinished.connect(self.OnLevelChanged)

        cl.addWidget(lbl_class, 0, 0)
        cl.addWidget(self.classCombo, 0, 1)
        cl.addWidget(lbl_level, 1, 0)
        cl.addWidget(self.levelEdit, 1, 1)
        cl.setColumnStretch(1, 1)

        # ---------- Inventory ----------
        sbs_inv = QGroupBox("Inventory")
        inv = QVBoxLayout(sbs_inv)
        inv.setContentsMargins(8, 8, 8, 8)
        inv.setSpacing(6)

        self.inventoryList = QListWidget()
        self.inventoryList.setMinimumWidth(280)
        # Высоту выставим динамически в changeCharacter, чтобы попасть в 4 строки.
        self.inventoryList.itemSelectionChanged.connect(self.OnItemSelected)
        inv.addWidget(self.inventoryList)

        self.itemCombo = QComboBox()
        self.itemCombo.setMinimumWidth(280)
        self.itemCombo.addItems(ITEM_NAMES)
        self.itemCombo.currentIndexChanged.connect(self.OnItemChanged)
        inv.addWidget(self.itemCombo)

        self.equippedCheck = QCheckBox("Equipped")
        self.equippedCheck.toggled.connect(self.OnEquippedToggled)
        inv.addWidget(self.equippedCheck)

        inv.addStretch()  # пустое место уезжает ВНИЗ под чекбокс

        # ---------- Layout ----------
        self.sizer.addWidget(sbs_select, 0, 0, 1, 2)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(sbs_class)
        ll.addStretch()

        self.sizer.addWidget(left, 1, 0)
        self.sizer.addWidget(sbs_inv, 1, 1)
        self.sizer.setColumnStretch(0, 2)
        self.sizer.setColumnStretch(1, 3)
        self.sizer.setRowStretch(1, 0)   # ← панель не растягивается на всю высоту

        self.loading = False
        self.changeCharacter(0)

    # ---------- helpers ----------
    def _load_all_characters(self):
        result = []
        try:
            pJoin = read_pointer(self.rom, ADDR_PJOIN_PTR)
            for i in range(NUM_CHARACTERS):
                result.append(Character.from_rom(self.rom, pJoin + i * 6))
        except Exception:
            for _ in range(NUM_CHARACTERS):
                result.append(Character(addr=0))
        return result

    def _labelFont(self):
        f = QFont("MS Sans Serif", 9)
        f.setBold(False)
        return f

    def _itemLabel(self, idx, equipped):
        name = ITEM_NAMES[idx] if 0 <= idx < len(ITEM_NAMES) else "Empty"
        return f"{name} (Equipped)" if equipped else name

    def _ensure_curFileStr(self):
        if not hasattr(self.rom, "curFileStr"):
            try:
                self.rom.startWriteProcess()
            except Exception:
                pass

    def _flushCharacter(self, ch):
        if not ch or not ch.addr:
            return
        try:
            self._ensure_curFileStr()
            self.rom.writeBytes(ch.addr, ch.to_hex())
        except Exception:
            pass

    # ---------- character name (ROM bank) ----------
    def _name_addr(self, name_idx):
        """Адрес name_idx-й записи (0-based) в bank'е pSpellNames."""
        addr = read_pointer(self.rom, ADDR_SPELLNAMES_PTR)
        for _ in range(name_idx):
            length = int(self.rom.getBytes(addr, 1), 16)
            addr += 1 + length
        return addr

    def _get_character_name(self, char_idx):
        addr = self._name_addr(PERSON_NAME_OFFSET + char_idx)
        length = int(self.rom.getBytes(addr, 1), 16)
        raw = self.rom.getBytes(addr + 1, length)
        return bytes.fromhex(raw).decode("ascii", errors="replace")

    def _set_character_name(self, char_idx, new_name):
        """Overwrite name in ROM — только та же длина, что и раньше."""
        addr = self._name_addr(PERSON_NAME_OFFSET + char_idx)
        old_len = int(self.rom.getBytes(addr, 1), 16)
        if len(new_name) != old_len:
            raise ValueError(
                f"Длина имени должна остаться {old_len}, получено {len(new_name)}"
            )
        self._ensure_curFileStr()
        self.rom.writeBytes(addr + 1, new_name.encode("ascii").hex())

    # ---------- character data ----------
    def changeCharacter(self, num=None):
        if num is not None:
            self.curCharacterIdx = num

        if not (0 <= self.curCharacterIdx < len(self.characters)):
            self.character = None
            return

        self.character = self.characters[self.curCharacterIdx]

        self.loading = True
        try:
            cls = self.character.class_idx
            self.classCombo.setCurrentIndex(cls if 0 <= cls < self.classCombo.count() else 0)
            self.levelEdit.setText(str(self.character.level))

            self.inventoryList.clear()
            for slot in range(4):
                v = self.character.items[slot] & 0xFF
                eq = v >= 0x80
                real = (v & 0x7F) if eq else v
                self.inventoryList.addItem(self._itemLabel(real, eq))

            # Подгоняем высоту ровно под 4 строки — без «воздуха» снизу
            row_h = self.inventoryList.sizeHintForRow(0)
            if row_h > 0:
                self.inventoryList.setFixedHeight(
                    row_h * 4 + 2 * self.inventoryList.frameWidth() + 4
                )

            self.curItemSlot = -1
            self.itemCombo.setCurrentIndex(-1)
            self.equippedCheck.setChecked(False)
        finally:
            self.loading = False

        self.updateModifiedIndicator(getattr(self.character, "modified", False))

    # ---------- signals ----------
    def OnSelectCharacter(self, idx):
        if self.loading:
            return
        self.changeCharacter(idx)

    def OnClassChanged(self, idx):
        if self.loading or self.character is None:
            return
        self.character.class_idx = idx
        self.character.modified = True
        self._flushCharacter(self.character)
        self._mark_modified()

    def OnLevelChanged(self):
        if self.loading or self.character is None:
            return
        txt = self.levelEdit.text().strip()
        if not txt.isdigit():
            self.levelEdit.setText(str(self.character.level))
            return
        self.character.level = int(txt) & 0xFF
        self.character.modified = True
        self._flushCharacter(self.character)
        self._mark_modified()

    def OnItemSelected(self):
        if self.loading or self.character is None:
            return
        row = self.inventoryList.currentRow()
        if row < 0:
            return
        self.curItemSlot = row

        v = self.character.items[row]
        eq = v >= 0x80
        real = (v & 0x7F) if eq else v

        self.loading = True
        if 0 <= real < self.itemCombo.count():
            self.itemCombo.setCurrentIndex(real)
        else:
            self.itemCombo.setCurrentIndex(-1)
        self.equippedCheck.setChecked(eq)
        self.loading = False

    def OnItemChanged(self, idx):
        if self.loading or self.character is None or self.curItemSlot < 0:
            return
        if idx < 0:
            return
        eq = self.equippedCheck.isChecked()
        value = (idx | 0x80) if eq else idx

        self.character.items[self.curItemSlot] = value
        self.character.modified = True

        item = self.inventoryList.item(self.curItemSlot)
        if item:
            item.setText(self._itemLabel(idx, eq))

        self._flushCharacter(self.character)
        self._mark_modified()

    def OnEquippedToggled(self, _checked):
        if self.loading or self.character is None or self.curItemSlot < 0:
            return
        self.OnItemChanged(self.itemCombo.currentIndex())

    # ---------- rename ----------
    def OnRename(self):
        if self.character is None:
            return
        idx = self.curCharacterIdx

        try:
            old_name = self._get_character_name(idx)
        except Exception as e:
            QMessageBox.critical(self, "Rename",
                                 f"Не удалось прочитать имя из ROM:\n{e}")
            return

        max_len = len(old_name)
        new_name, ok = QInputDialog.getText(
            self, "Rename",
            f"Новое имя для {CHARACTER_NAMES[idx]} (не длиннее {max_len} символов):",
            text=old_name,
        )
        if not ok:
            return

        new_name = new_name.strip().upper()
        if not new_name:
            return

        if len(new_name) > max_len:
            QMessageBox.warning(
                self, "Rename",
                f"Слишком длинное имя.\n"
                f"Максимум — {max_len} символов (как у исходного)."
            )
            return

        # Хвост добиваем пробелами, чтобы длина совпала с исходной.
        padded = new_name.ljust(max_len)

        try:
            self._set_character_name(idx, padded)
        except Exception as e:
            QMessageBox.critical(self, "Rename",
                                 f"Не удалось записать имя:\n{e}")
            return

        # Обновляем UI
        self.characterList.setItemText(idx, new_name)
        self.character.modified = True
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
        if self.character is not None:
            self.changeCharacter(self.curCharacterIdx)

    def getCurrentData(self):
        return getattr(self, "character", None)

    def getCurrentSpriteObject(self):
        return getattr(self, "character", None)

    changeSelection = changeCharacter