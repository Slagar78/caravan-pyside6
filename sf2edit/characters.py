# sf2edit/characters.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QComboBox, QLineEdit, QListWidget,
    QCheckBox, QSpinBox, QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

import rompanel
from sf2edit.spells import SPELL_CODES


# ---------- ROM-адреса ----------
ADDR_PJOIN_PTR     = 0x1EE008      # Start Data
ADDR_PSTATS_PTR    = 0x1EE270      # ← ИСПРАВЛЕНО (было 0x1EE2F0)
ADDR_BSPRITE_BASE  = 0x1F806
ADDR_SPELLNAMES_PTR= 33476

NUM_CHARACTERS     = 30
PERSON_NAME_OFFSET = 44
MAX_STAT_BLOCKS    = 200


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

STAT_GROWTH_OPTIONS = [
    (0, "None"), (1, "Linear"), (2, "Late"),
    (3, "Early"), (4, "Middle"), (5, "Early+Late"),
]


# ---------- helpers ----------
def read_pointer(rom, ptr_addr):
    return int(rom.getBytes(ptr_addr + 1, 3), 16)


class Character:
    """Start Data — 6 байт."""
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
            items=[int(raw[4:6], 16), int(raw[6:8], 16),
                   int(raw[8:10], 16), int(raw[10:12], 16)],
        )

    def to_hex(self):
        b = "%02x%02x" % (self.class_idx & 0xFF, self.level & 0xFF)
        for it in self.items:
            b += "%02x" % (it & 0xFF)
        return b


class StatBlock:
    """Один блок статов (для одного класса)."""
    __slots__ = (
        "addr", "char_idx", "idx_in_group",
        "class_idx",
        "hp_growth", "hp_base", "hp_proj",
        "mp_growth", "mp_base", "mp_proj",
        "atk_growth", "atk_base", "atk_proj",
        "def_growth", "def_base", "def_proj",
        "agi_growth", "agi_base", "agi_proj",
        "spells", "use_base_class",
        "modified",
    )

    def __init__(self, addr=0, char_idx=0):
        self.addr = addr
        self.char_idx = char_idx
        self.idx_in_group = 1
        self.class_idx = 0
        self.hp_growth  = 0; self.hp_base  = 0; self.hp_proj  = 0
        self.mp_growth  = 0; self.mp_base  = 0; self.mp_proj  = 0
        self.atk_growth = 0; self.atk_base = 0; self.atk_proj = 0
        self.def_growth = 0; self.def_base = 0; self.def_proj = 0
        self.agi_growth = 0; self.agi_base = 0; self.agi_proj = 0
        self.spells = []
        self.use_base_class = False
        self.modified = False

    @classmethod
    def from_rom(cls, rom, addr, char_idx=0):
        s = cls(addr=addr, char_idx=char_idx)
        raw = rom.getBytes(addr, 16)
        s.class_idx  = int(raw[0:2],   16)
        s.hp_growth  = int(raw[2:4],   16)
        s.hp_base    = int(raw[4:6],   16)
        s.hp_proj    = int(raw[6:8],   16)
        s.mp_growth  = int(raw[8:10],  16)
        s.mp_base    = int(raw[10:12], 16)
        s.mp_proj    = int(raw[12:14], 16)
        s.atk_growth = int(raw[14:16], 16)
        s.atk_base   = int(raw[16:18], 16)
        s.atk_proj   = int(raw[18:20], 16)
        s.def_growth = int(raw[20:22], 16)
        s.def_base   = int(raw[22:24], 16)
        s.def_proj   = int(raw[24:26], 16)
        s.agi_growth = int(raw[26:28], 16)
        s.agi_base   = int(raw[28:30], 16)
        s.agi_proj   = int(raw[30:32], 16)

        idx = addr + 16
        for _ in range(32):
            b = int(rom.getBytes(idx, 1), 16)
            if b == 0xFF or b == 0xFE:
                s.use_base_class = (b == 0xFE)
                break
            code = int(rom.getBytes(idx + 1, 1), 16)
            s.spells.append((b, code))
            idx += 2
        return s

    def end_addr(self):
        """Адрес сразу за байтом FF/FE."""
        return self.addr + 16 + len(self.spells) * 2 + 1

    def to_hex(self):
        b  = "%02x%02x" % (self.class_idx & 0xFF, self.hp_growth & 0xFF)
        b += "%02x%02x" % (self.hp_base & 0xFF,   self.hp_proj & 0xFF)
        b += "%02x%02x" % (self.mp_growth & 0xFF, self.mp_base & 0xFF)
        b += "%02x%02x" % (self.mp_proj & 0xFF,   self.atk_growth & 0xFF)
        b += "%02x%02x" % (self.atk_base & 0xFF,  self.atk_proj & 0xFF)
        b += "%02x%02x" % (self.def_growth & 0xFF,self.def_base & 0xFF)
        b += "%02x%02x" % (self.def_proj & 0xFF,  self.agi_growth & 0xFF)
        b += "%02x%02x" % (self.agi_base & 0xFF,  self.agi_proj & 0xFF)
        for lvl, code in self.spells:
            b += "%02x%02x" % (lvl & 0xFF, code & 0xFF)
        b += "fe" if self.use_base_class else "ff"
        return b


# =========================================================
# Panel
# =========================================================
class CharacterPanel(rompanel.ROMPanel):
    frameTitle = "Characters"
    canMaximize = True

    def init(self):
        if self.rom is None:
            return

        self.loading = True
        self.character = None
        self.stats_block = None
        self.curBlockIdx = 0
        self.curItemSlot = -1
        self.curSpellSlot = -1

        # Start Data
        if "characters" not in self.rom.data or not self.rom.data["characters"]:
            self.rom.data["characters"] = self._load_all_characters()
        self.characters = self.rom.data["characters"]

        # Stat Blocks (все, сгруппированные по персонажам)
        if "stat_blocks" not in self.rom.data or not self.rom.data["stat_blocks"]:
            self.rom.data["stat_blocks"] = self._load_all_blocks()
        self.stat_blocks = self.rom.data["stat_blocks"]

        # ---------- Select ----------
        sbs_select = QGroupBox("Select")
        sel = QHBoxLayout(sbs_select)
        sel.setContentsMargins(6, 6, 6, 6)
        sel.setSpacing(6)

        self.blockList = QComboBox()
        self.blockList.setMinimumWidth(180)
        self._populate_blocks()
        self.blockList.currentIndexChanged.connect(self.OnSelectBlock)
        sel.addWidget(self.blockList)

        self.renameButton = QPushButton("Rename")
        self.renameButton.setFixedWidth(80)
        self.renameButton.clicked.connect(self.OnRename)
        sel.addWidget(self.renameButton)
        sel.addStretch()

        # ---------- Class / Level ----------
        sbs_class = QGroupBox()
        cl = QGridLayout(sbs_class)
        cl.setContentsMargins(8, 8, 8, 8)
        cl.setHorizontalSpacing(8)
        cl.setVerticalSpacing(6)

        lbl_class = QLabel("Class"); lbl_class.setFont(self._labelFont())
        self.classCombo = QComboBox()
        self.classCombo.setMinimumWidth(110)
        self.classCombo.addItems(CLASS_NAMES)
        self.classCombo.currentIndexChanged.connect(self.OnClassChanged)

        lbl_level = QLabel("Level"); lbl_level.setFont(self._labelFont())
        self.levelEdit = QLineEdit()
        self.levelEdit.setMaximumWidth(45)
        self.levelEdit.setMaxLength(3)
        self.levelEdit.setAlignment(Qt.AlignCenter)
        self.levelEdit.editingFinished.connect(self.OnLevelChanged)

        cl.addWidget(lbl_class, 0, 0); cl.addWidget(self.classCombo, 0, 1)
        cl.addWidget(lbl_level, 1, 0); cl.addWidget(self.levelEdit, 1, 1)
        cl.setColumnStretch(1, 1)

        # ---------- Inventory ----------
        sbs_inv = QGroupBox("Inventory")
        inv = QVBoxLayout(sbs_inv)
        inv.setContentsMargins(6, 6, 6, 6)
        inv.setSpacing(4)

        self.inventoryList = QListWidget()
        self.inventoryList.setMinimumWidth(150)
        self.inventoryList.itemSelectionChanged.connect(self.OnItemSelected)
        inv.addWidget(self.inventoryList)

        self.itemCombo = QComboBox()
        self.itemCombo.setMinimumWidth(150)
        self.itemCombo.addItems(ITEM_NAMES)
        self.itemCombo.currentIndexChanged.connect(self.OnItemChanged)
        inv.addWidget(self.itemCombo)

        self.equippedCheck = QCheckBox("Equipped")
        self.equippedCheck.toggled.connect(self.OnEquippedToggled)
        inv.addWidget(self.equippedCheck)

        # ---------- Battle Sprite ----------
        sbs_bs = QGroupBox("Battle Sprite")
        bs = QGridLayout(sbs_bs)
        bs.setContentsMargins(6, 6, 6, 6)
        bs.setHorizontalSpacing(6); bs.setVerticalSpacing(4)

        lbl_m = QLabel("Model"); lbl_m.setFont(self._labelFont())
        self.modelSpin = QSpinBox(); self.modelSpin.setRange(0, 255)
        self.modelSpin.setMaximumWidth(60)
        self.modelSpin.valueChanged.connect(self.OnModelChanged)

        lbl_p = QLabel("Palette"); lbl_p.setFont(self._labelFont())
        self.palSpin = QSpinBox(); self.palSpin.setRange(0, 255)
        self.palSpin.setMaximumWidth(60)
        self.palSpin.valueChanged.connect(self.OnPalChanged)

        bs.addWidget(lbl_m, 0, 0); bs.addWidget(self.modelSpin, 0, 1)
        bs.addWidget(lbl_p, 1, 0); bs.addWidget(self.palSpin,   1, 1)
        bs.setColumnStretch(2, 1)

        # ---------- Stats ----------
        sbs_stats = QGroupBox("Stats")
        st = QGridLayout(sbs_stats)
        st.setContentsMargins(8, 8, 8, 8)
        st.setHorizontalSpacing(6)
        st.setVerticalSpacing(4)

        hdr_b = QLabel("Base");   hdr_b.setFont(self._labelFont())
        hdr_p = QLabel("Lv.30");  hdr_p.setFont(self._labelFont())
        hdr_g = QLabel("Growth"); hdr_g.setFont(self._labelFont())
        st.addWidget(hdr_b, 0, 1); st.addWidget(hdr_p, 0, 2); st.addWidget(hdr_g, 0, 3)

        def make_row(row_idx, label):
            l = QLabel(label); l.setFont(self._labelFont())
            b = QSpinBox(); b.setRange(0, 255); b.setMaximumWidth(60)
            p = QSpinBox(); p.setRange(0, 255); p.setMaximumWidth(60)
            g = QComboBox()
            for code, name in STAT_GROWTH_OPTIONS:
                g.addItem(name, code)
            g.setMinimumWidth(100)
            st.addWidget(l, row_idx, 0)
            st.addWidget(b, row_idx, 1)
            st.addWidget(p, row_idx, 2)
            st.addWidget(g, row_idx, 3)
            return b, p, g

        self.hpBase,  self.hpProj,  self.hpGrowth  = make_row(1, "HP")
        self.mpBase,  self.mpProj,  self.mpGrowth  = make_row(2, "MP")
        self.atkBase, self.atkProj, self.atkGrowth = make_row(3, "ATK")
        self.defBase, self.defProj, self.defGrowth = make_row(4, "DEF")
        self.agiBase, self.agiProj, self.agiGrowth = make_row(5, "AGI")

        self.hpBase.valueChanged.connect(self.OnHpBaseChanged)
        self.hpProj.valueChanged.connect(self.OnHpProjChanged)
        self.hpGrowth.currentIndexChanged.connect(self.OnHpGrowthChanged)
        self.mpBase.valueChanged.connect(self.OnMpBaseChanged)
        self.mpProj.valueChanged.connect(self.OnMpProjChanged)
        self.mpGrowth.currentIndexChanged.connect(self.OnMpGrowthChanged)
        self.atkBase.valueChanged.connect(self.OnAtkBaseChanged)
        self.atkProj.valueChanged.connect(self.OnAtkProjChanged)
        self.atkGrowth.currentIndexChanged.connect(self.OnAtkGrowthChanged)
        self.defBase.valueChanged.connect(self.OnDefBaseChanged)
        self.defProj.valueChanged.connect(self.OnDefProjChanged)
        self.defGrowth.currentIndexChanged.connect(self.OnDefGrowthChanged)
        self.agiBase.valueChanged.connect(self.OnAgiBaseChanged)
        self.agiProj.valueChanged.connect(self.OnAgiProjChanged)
        self.agiGrowth.currentIndexChanged.connect(self.OnAgiGrowthChanged)

        self.useBaseClassCheck = QCheckBox("Use Base Class List")
        self.useBaseClassCheck.toggled.connect(self.OnUseBaseClassToggled)
        st.addWidget(self.useBaseClassCheck, 6, 0, 1, 4)
        st.setColumnStretch(4, 1)

        # ---------- Spells ----------
        sbs_sp = QGroupBox("Spells")
        sp = QVBoxLayout(sbs_sp)
        sp.setContentsMargins(6, 6, 6, 6)
        sp.setSpacing(4)

        self.spellList = QListWidget()
        self.spellList.setMinimumWidth(150)
        self.spellList.setMinimumHeight(140)
        self.spellList.itemSelectionChanged.connect(self.OnSpellSelected)
        sp.addWidget(self.spellList)

        self.spellCombo = QComboBox()
        self.spellCombo.setMinimumWidth(150)
        for code in sorted(SPELL_CODES.keys()):
            self.spellCombo.addItem(SPELL_CODES[code], code)
        self.spellCombo.currentIndexChanged.connect(self.OnSpellChanged)
        sp.addWidget(self.spellCombo)

        level_row = QHBoxLayout()
        lbl_at = QLabel("@ Level"); lbl_at.setFont(self._labelFont())
        self.spellLevelSpin = QSpinBox()
        self.spellLevelSpin.setRange(0, 255)
        self.spellLevelSpin.setMaximumWidth(60)
        self.spellLevelSpin.valueChanged.connect(self.OnSpellLevelChanged)
        level_row.addWidget(lbl_at); level_row.addWidget(self.spellLevelSpin)
        level_row.addStretch()
        sp.addLayout(level_row)

        # ---------- Layout ----------
        self.sizer.addWidget(sbs_select, 0, 0, 1, 3)

        left = QWidget(); ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0); ll.setSpacing(4)
        ll.addWidget(sbs_class); ll.addWidget(sbs_bs); ll.addWidget(sbs_stats); ll.addStretch()

        mid = QWidget(); ml = QVBoxLayout(mid)
        ml.setContentsMargins(0, 0, 0, 0); ml.setSpacing(4)
        ml.addWidget(sbs_inv); ml.addStretch()

        right = QWidget(); rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0); rl.setSpacing(4)
        rl.addWidget(sbs_sp); rl.addStretch()

        self.sizer.addWidget(left,  1, 0)
        self.sizer.addWidget(mid,   1, 1)
        self.sizer.addWidget(right, 1, 2)
        self.sizer.setColumnStretch(0, 0)   # ← было 2
        self.sizer.setColumnStretch(1, 0)   # ← было 2
        self.sizer.setColumnStretch(2, 1)   # ← оставил 1
        self.sizer.setRowStretch(2, 1)

        self.loading = False
        self.changeBlock(0)

    # ---------- helpers ----------
    def _labelFont(self):
        f = QFont("MS Sans Serif", 9); f.setBold(False); return f

    def _load_all_characters(self):
        result = []
        try:
            pJoin = read_pointer(self.rom, ADDR_PJOIN_PTR)
            for i in range(NUM_CHARACTERS):
                result.append(Character.from_rom(self.rom, pJoin + i * 6))
        except Exception:
            for _ in range(NUM_CHARACTERS):
                result.append(Character())
        return result

    def _load_all_blocks(self):
        """Читаем ВСЕ стат-блоки от pStats[0] до конца."""
        blocks = []
        try:
            # указатели начала групп
            ptrs = []
            for i in range(NUM_CHARACTERS):
                p = read_pointer(self.rom, ADDR_PSTATS_PTR + i * 4)
                if not p:
                    break
                ptrs.append(p)
            while len(ptrs) < NUM_CHARACTERS:
                ptrs.append(0)
            if not ptrs or not ptrs[0]:
                return blocks

            addr = ptrs[0]
            for _ in range(MAX_STAT_BLOCKS):
                # char_idx = к какой группе относится
                char_idx = 0
                for i in range(NUM_CHARACTERS - 1, -1, -1):
                    if ptrs[i] and ptrs[i] <= addr:
                        char_idx = i
                        break

                blk = StatBlock.from_rom(self.rom, addr, char_idx)
                blocks.append(blk)

                addr = blk.end_addr()
                # защита
                if addr > 0x1FFFFF: break
                if len(blocks) > 5 and addr > blocks[0].addr + 20000: break

            # idx_in_group
            per_char = {}
            for b in blocks:
                per_char.setdefault(b.char_idx, []).append(b)
            for c, lst in per_char.items():
                for i, b in enumerate(lst):
                    b.idx_in_group = i + 1
        except Exception:
            pass
        return blocks

    def _populate_blocks(self):
        """Combo: BOWIE 1, BOWIE 2, SARAH 1, ..."""
        self.blockList.clear()
        for i, b in enumerate(self.stat_blocks):
            name = CHARACTER_NAMES[b.char_idx] if 0 <= b.char_idx < len(CHARACTER_NAMES) else f"C{b.char_idx}"
            self.blockList.addItem(f"{name} {b.idx_in_group}", i)

    def _itemLabel(self, idx, equipped):
        name = ITEM_NAMES[idx] if 0 <= idx < len(ITEM_NAMES) else "Empty"
        return f"{name} (Equipped)" if equipped else name

    def _spellName(self, code):
        return SPELL_CODES.get(code) or f"[0x{code:02X}]"

    def _ensure_curFileStr(self):
        if not hasattr(self.rom, "curFileStr"):
            try: self.rom.startWriteProcess()
            except Exception: pass

    def _flush_character(self, ch):
        if not ch or not ch.addr: return
        try:
            self._ensure_curFileStr()
            self.rom.writeBytes(ch.addr, ch.to_hex())
        except Exception: pass

    def _flush_block(self, b):
        if not b or not b.addr: return
        try:
            self._ensure_curFileStr()
            self.rom.writeBytes(b.addr, b.to_hex())
        except Exception: pass

    def _bsprite_addr(self, block_idx):
        """Порт VB6 SpriteUpdate(): шагает по 3 байта, пропуская записи где byte+3 == 255."""
        addr = ADDR_BSPRITE_BASE
        idx = 0
        guard = 0
        while idx < block_idx and guard < 500:
            if int(self.rom.getBytes(addr + 3, 1), 16) < 255:
                idx += 1
            addr += 3
            guard += 1
        return addr

    # ---------- name ----------
    def _name_addr(self, name_idx):
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
        addr = self._name_addr(PERSON_NAME_OFFSET + char_idx)
        old_len = int(self.rom.getBytes(addr, 1), 16)
        if len(new_name) != old_len:
            raise ValueError(f"Длина должна остаться {old_len}")
        self._ensure_curFileStr()
        self.rom.writeBytes(addr + 1, new_name.encode("ascii").hex())

    # ---------- change ----------
    def changeBlock(self, idx=None):
        if idx is not None:
            self.curBlockIdx = idx
        if not (0 <= self.curBlockIdx < len(self.stat_blocks)):
            self.character = None
            self.stats_block = None
            return

        self.stats_block = self.stat_blocks[self.curBlockIdx]
        char_idx = self.stats_block.char_idx
        self.character = self.characters[char_idx] if 0 <= char_idx < len(self.characters) else None

        self.loading = True
        try:
            # Class / Level (Start Data)
            if self.character:
                cls = self.character.class_idx
                self.classCombo.setCurrentIndex(cls if 0 <= cls < self.classCombo.count() else 0)
                self.levelEdit.setText(str(self.character.level))

            # Inventory
            self.inventoryList.clear()
            if self.character:
                for slot in range(4):
                    v = self.character.items[slot] & 0xFF
                    eq = v >= 0x80
                    real = (v & 0x7F) if eq else v
                    self.inventoryList.addItem(self._itemLabel(real, eq))
            row_h = self.inventoryList.sizeHintForRow(0)
            if row_h > 0:
                self.inventoryList.setFixedHeight(
                    row_h * 4 + 2 * self.inventoryList.frameWidth() + 4
                )
            self.curItemSlot = -1
            self.itemCombo.setCurrentIndex(-1)
            self.equippedCheck.setChecked(False)

            # Stats block
            s = self.stats_block
            self.hpBase.setValue(s.hp_base);   self.hpProj.setValue(s.hp_proj)
            self.mpBase.setValue(s.mp_base);   self.mpProj.setValue(s.mp_proj)
            self.atkBase.setValue(s.atk_base); self.atkProj.setValue(s.atk_proj)
            self.defBase.setValue(s.def_base); self.defProj.setValue(s.def_proj)
            self.agiBase.setValue(s.agi_base); self.agiProj.setValue(s.agi_proj)

            for combo, val in ((self.hpGrowth, s.hp_growth), (self.mpGrowth, s.mp_growth),
                               (self.atkGrowth, s.atk_growth), (self.defGrowth, s.def_growth),
                               (self.agiGrowth, s.agi_growth)):
                for i in range(combo.count()):
                    if combo.itemData(i) == val:
                        combo.setCurrentIndex(i); break

            self.useBaseClassCheck.setChecked(s.use_base_class)

            # Battle sprite
            baddr = self._bsprite_addr(self.curBlockIdx)
            model = int(self.rom.getBytes(baddr + 1, 1), 16)
            pal   = int(self.rom.getBytes(baddr + 2, 1), 16)
            self.modelSpin.setValue(model)
            self.palSpin.setValue(pal)

            # Spells
            self.spellList.clear()
            for lvl, code in s.spells:
                self.spellList.addItem(f"{self._spellName(code)} @ {lvl}")
            self.curSpellSlot = -1
            self.spellLevelSpin.setValue(0)
        finally:
            self.loading = False

        self.updateModifiedIndicator(getattr(self.stats_block, "modified", False))

    # ---------- signals ----------
    def OnSelectBlock(self, _i):
        if self.loading: return
        idx = self.blockList.currentData()
        if idx is None: return
        self.changeBlock(idx)

    def OnClassChanged(self, idx):
        if self.loading or self.character is None: return
        self.character.class_idx = idx
        self.character.modified = True
        self._ensure_curFileStr()
        try:
            self.rom.writeBytes(self._bsprite_addr(self.curBlockIdx), "%02x" % (idx & 0xFF))
        except Exception: pass
        self._flush_character(self.character)
        self._mark_modified()

    def OnLevelChanged(self):
        if self.loading or self.character is None: return
        txt = self.levelEdit.text().strip()
        if not txt.isdigit():
            self.levelEdit.setText(str(self.character.level)); return
        self.character.level = int(txt) & 0xFF
        self.character.modified = True
        self._flush_character(self.character)
        self._mark_modified()

    # --- inventory ---
    def OnItemSelected(self):
        if self.loading or self.character is None: return
        row = self.inventoryList.currentRow()
        if row < 0: return
        self.curItemSlot = row
        v = self.character.items[row]
        eq = v >= 0x80
        real = (v & 0x7F) if eq else v
        self.loading = True
        self.itemCombo.setCurrentIndex(real if 0 <= real < self.itemCombo.count() else -1)
        self.equippedCheck.setChecked(eq)
        self.loading = False

    def OnItemChanged(self, idx):
        if self.loading or self.character is None or self.curItemSlot < 0: return
        if idx < 0: return
        eq = self.equippedCheck.isChecked()
        value = (idx | 0x80) if eq else idx
        self.character.items[self.curItemSlot] = value
        self.character.modified = True
        item = self.inventoryList.item(self.curItemSlot)
        if item: item.setText(self._itemLabel(idx, eq))
        self._flush_character(self.character)
        self._mark_modified()

    def OnEquippedToggled(self, _c):
        if self.loading or self.character is None or self.curItemSlot < 0: return
        self.OnItemChanged(self.itemCombo.currentIndex())

    # --- stats ---
    def _upd_stat(self, attr, value):
        if self.loading or self.stats_block is None: return
        setattr(self.stats_block, attr, value & 0xFF)
        self.stats_block.modified = True
        self._flush_block(self.stats_block)
        self._mark_modified()

    def OnHpBaseChanged(self, v):   self._upd_stat("hp_base", v)
    def OnHpProjChanged(self, v):   self._upd_stat("hp_proj", v)
    def OnMpBaseChanged(self, v):   self._upd_stat("mp_base", v)
    def OnMpProjChanged(self, v):   self._upd_stat("mp_proj", v)
    def OnAtkBaseChanged(self, v):  self._upd_stat("atk_base", v)
    def OnAtkProjChanged(self, v):  self._upd_stat("atk_proj", v)
    def OnDefBaseChanged(self, v):  self._upd_stat("def_base", v)
    def OnDefProjChanged(self, v):  self._upd_stat("def_proj", v)
    def OnAgiBaseChanged(self, v):  self._upd_stat("agi_base", v)
    def OnAgiProjChanged(self, v):  self._upd_stat("agi_proj", v)

    def _upd_growth(self, attr, combo):
        if self.loading or self.stats_block is None: return
        data = combo.currentData()
        if data is None: return
        setattr(self.stats_block, attr, data)
        self.stats_block.modified = True
        self._flush_block(self.stats_block)
        self._mark_modified()

    def OnHpGrowthChanged(self, _i):  self._upd_growth("hp_growth",  self.hpGrowth)
    def OnMpGrowthChanged(self, _i):  self._upd_growth("mp_growth",  self.mpGrowth)
    def OnAtkGrowthChanged(self, _i): self._upd_growth("atk_growth", self.atkGrowth)
    def OnDefGrowthChanged(self, _i): self._upd_growth("def_growth", self.defGrowth)
    def OnAgiGrowthChanged(self, _i): self._upd_growth("agi_growth", self.agiGrowth)

    def OnUseBaseClassToggled(self, checked):
        if self.loading or self.stats_block is None: return
        self.stats_block.use_base_class = bool(checked)
        self.stats_block.modified = True
        self._flush_block(self.stats_block)
        self._mark_modified()

    # --- battle sprite ---
    def OnModelChanged(self, v):
        if self.loading or self.stats_block is None: return
        self._ensure_curFileStr()
        try:
            self.rom.writeBytes(self._bsprite_addr(self.curBlockIdx) + 1, "%02x" % (v & 0xFF))
        except Exception: pass
        self._mark_modified()

    def OnPalChanged(self, v):
        if self.loading or self.stats_block is None: return
        self._ensure_curFileStr()
        try:
            self.rom.writeBytes(self._bsprite_addr(self.curBlockIdx) + 2, "%02x" % (v & 0xFF))
        except Exception: pass
        self._mark_modified()

    # --- spells ---
    def OnSpellSelected(self):
        if self.loading or self.stats_block is None: return
        row = self.spellList.currentRow()
        if row < 0: return
        self.curSpellSlot = row
        level, code = self.stats_block.spells[row]
        self.loading = True
        for i in range(self.spellCombo.count()):
            if self.spellCombo.itemData(i) == code:
                self.spellCombo.setCurrentIndex(i); break
        self.spellLevelSpin.setValue(level)
        self.loading = False

    def OnSpellChanged(self, _i):
        if self.loading or self.stats_block is None or self.curSpellSlot < 0: return
        code = self.spellCombo.currentData()
        if code is None: return
        level, _ = self.stats_block.spells[self.curSpellSlot]
        self.stats_block.spells[self.curSpellSlot] = (level, code)
        self.stats_block.modified = True
        item = self.spellList.item(self.curSpellSlot)
        if item: item.setText(f"{self._spellName(code)} @ {level}")
        self._flush_block(self.stats_block)
        self._mark_modified()

    def OnSpellLevelChanged(self, v):
        if self.loading or self.stats_block is None or self.curSpellSlot < 0: return
        _, code = self.stats_block.spells[self.curSpellSlot]
        self.stats_block.spells[self.curSpellSlot] = (v & 0xFF, code)
        self.stats_block.modified = True
        item = self.spellList.item(self.curSpellSlot)
        if item: item.setText(f"{self._spellName(code)} @ {v}")
        self._flush_block(self.stats_block)
        self._mark_modified()

    # ---------- rename ----------
    def OnRename(self):
        if self.character is None: return
        char_idx = self.stats_block.char_idx
        try:
            old_name = self._get_character_name(char_idx)
        except Exception as e:
            QMessageBox.critical(self, "Rename", f"Не удалось прочитать:\n{e}"); return
        max_len = len(old_name)
        new_name, ok = QInputDialog.getText(
            self, "Rename",
            f"Новое имя для {CHARACTER_NAMES[char_idx]} (не длиннее {max_len}):",
            text=old_name,
        )
        if not ok: return
        new_name = new_name.strip().upper()
        if not new_name: return
        if len(new_name) > max_len:
            QMessageBox.warning(self, "Rename", f"Максимум — {max_len} символов."); return
        try:
            self._set_character_name(char_idx, new_name.ljust(max_len))
        except Exception as e:
            QMessageBox.critical(self, "Rename", f"Не удалось записать:\n{e}"); return

        # обновить текст во всех блоках этого персонажа
        for i, b in enumerate(self.stat_blocks):
            if b.char_idx == char_idx:
                self.blockList.setItemText(i, f"{new_name} {b.idx_in_group}")

        self.character.modified = True
        self._mark_modified()

    # ---------- internal ----------
    def _mark_modified(self):
        self.updateModifiedIndicator(True)
        try: self.parent.modify()
        except Exception: pass

    # ---------- panel hooks ----------
    def OnShow(self, event=None):
        if self.stats_block is not None:
            self.changeBlock(self.curBlockIdx)

    def getCurrentData(self): return getattr(self, "stats_block", None)
    def getCurrentSpriteObject(self): return getattr(self, "stats_block", None)
    changeSelection = changeBlock