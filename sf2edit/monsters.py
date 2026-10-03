# sf2edit/monsters.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QComboBox, QListWidget, QCheckBox,
    QSpinBox, QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

import rompanel

# Общие списки из items.py и classes.py, чтобы не дублировать
from sf2edit.items import ITEM_NAMES, SPELL_CODES
from sf2edit.classes import MOVE_TYPES


# ---------- ROM-адреса ----------
ADDR_PMONSTER_DATA   = 0x1B1A66
ADDR_BATTLE_SPRITES  = 0x1F806
ADDR_GOLD_BASE       = 48844           # 0xBECC
ADDR_SPELLNAMES_PTR  = 33476           # pSpellNames

NUM_MONSTERS         = 103
MONSTER_LEN          = 56
MONSTER_NAME_OFFSET  = 74              # monsters start after 44 spells + 30 heroes

BSPRITE_OFFSET       = 270             # pBattleSprites + 270 + idx*2


# ---------- Fallback имена (из MonsterCodes.txt) ----------
MONSTER_NAMES = [
    "Ooze", "Huge Rat", "Galam Soldier", "Galam Knight",
    "Goblin", "Green Ooze", "Dark Dwarf", "Hobgoblin",
    "Zombie", "Golem", "Kraken Leg", "Soulsower",
    "Orc", "Pawn", "Knight", "Rat",
    "Bubbling Ooze", "Skeleton", "Dark Soldier", "Lizardman",
    "Worm", "Dark Knight", "Orc Lord", "Devil Soldier",
    "Cerberus", "Mud Man", "Dragonnewt", "Purple Worm",
    "Executioner", "Hell Hound", "Minotaur", "Cyclops",
    "Burst Rock", "Hydra", "Chaos Warrior", "Reaper",
    "Evil Beast", "Pyrohydra", "Zeon Guard", "Gizmo",
    "Huge Bat", "Vampire Bat", "Evil Cloud", "Gargoyle",
    "Harpy", "Lesser Demon", "Wyvern", "Harpy Queen",
    "Pegasus Knight", "Griffin", "Mist Demon", "White Dragon",
    "Demon", "Chaos Dragon", "Devil Griffin", "Arch Demon",
    "Galam Archer", "Hunter Goblin", "Death Archer", "Kraken Arm",
    "Arrow Launcher", "Rook", "Dark Sniper", "Bow Master",
    "Bow Rider", "Dark Gunner", "Horseman",
    "Galam Mage", "Witch", "Master Mage", "Dark Madam",
    "Queen", "Wizard", "Necromancer", "Chaos Wizard",
    "Demon Master", "Dark Cleric", "Death Monk", "Black Monk",
    "High Priest", "Evil Bishop", "Dark Bishop", "Master Monk",
    "Shaman", "Evil Bishop", "Blue Shaman", "Dark Smoke",
    "Kraken Head", "Taros", "King", "Willard",
    "Zalbard", "Cameela", "Prism Flower", "Red Baron",
    "Geshp", "Odd Eye", "Galam", "Zeon",
    "Jar", "Master Mage", "Necromancer", "Blue Shaman",
]


# ---------- helpers ----------
def read_pointer(rom, ptr_addr):
    return int(rom.getBytes(ptr_addr + 1, 3), 16)


class Monster:
    """Одна запись монстра (56 байт)."""

    def __init__(self, addr=0, raw=None):
        self.addr = addr
        self.raw = bytearray(raw) if raw else bytearray(MONSTER_LEN)
        self.modified = False

    @classmethod
    def from_rom(cls, rom, addr):
        raw = bytes.fromhex(rom.getBytes(addr, MONSTER_LEN))
        return cls(addr=addr, raw=raw)

    def to_hex(self):
        return bytes(self.raw).hex()

    # --- byte properties ---
    def _get(self, i): return self.raw[i]
    def _set(self, i, v):
        self.raw[i] = v & 0xFF
        self.modified = True

    @property
    def spellpower(self): return self.raw[10]
    @spellpower.setter
    def spellpower(self, v): self._set(10, v)

    @property
    def level(self): return self.raw[11]
    @level.setter
    def level(self, v): self._set(11, v)

    @property
    def hp(self): return (self.raw[12] << 8) | self.raw[13]
    @hp.setter
    def hp(self, v):
        self.raw[12] = (v >> 8) & 0xFF
        self.raw[13] = v & 0xFF
        self.modified = True

    @property
    def mp(self): return self.raw[16]
    @mp.setter
    def mp(self, v): self._set(16, v)

    @property
    def atk(self): return self.raw[18]
    @atk.setter
    def atk(self, v): self._set(18, v)

    @property
    def dfn(self): return self.raw[20]
    @dfn.setter
    def dfn(self, v): self._set(20, v)

    @property
    def agi(self): return self.raw[22]
    @agi.setter
    def agi(self, v): self._set(22, v)

    @property
    def move(self): return self.raw[24]
    @move.setter
    def move(self, v): self._set(24, v)

    @property
    def other_res(self): return self.raw[26]
    @other_res.setter
    def other_res(self, v): self._set(26, v)

    @property
    def elem_res(self): return self.raw[27]
    @elem_res.setter
    def elem_res(self, v): self._set(27, v)

    @property
    def atk_chances(self): return self.raw[30]
    @atk_chances.setter
    def atk_chances(self, v): self._set(30, v)

    @property
    def move_type(self): return self.raw[49]
    @move_type.setter
    def move_type(self, v): self._set(49, v)

    # --- items (4 slots: +33, +35, +37, +39) ---
    def get_item(self, i):
        b = self.raw[33 + i * 2]
        eq = b >= 0x80
        idx = (b & 0x7F) if eq else b
        return idx, eq

    def set_item(self, i, idx, equipped):
        self.raw[33 + i * 2] = (idx | 0x80) if equipped else idx
        self.modified = True

    # --- spells (4 slots: +40..+43) ---
    def get_spell(self, i): return self.raw[40 + i]
    def set_spell(self, i, code):
        self.raw[40 + i] = code & 0xFF
        self.modified = True


# =========================================================
# Panel
# =========================================================
class MonsterPanel(rompanel.ROMPanel):
    frameTitle = "Monsters"
    canMaximize = True

    def init(self):
        if self.rom is None:
            return

        self.loading = True
        self.monster = None
        self.curIdx = 0

        if "monsters" not in self.rom.data or not self.rom.data["monsters"]:
            self.rom.data["monsters"] = self._load_all()
        self.monsters = self.rom.data["monsters"]

        # ---------- Select ----------
        sbs_select = QGroupBox("Select")
        sel = QHBoxLayout(sbs_select)
        sel.setContentsMargins(8, 8, 8, 8)
        sel.setSpacing(8)

        self.monList = QComboBox()
        self.monList.setMinimumWidth(200)
        self._populate_list()
        self.monList.currentIndexChanged.connect(self.OnSelectMonster)
        sel.addWidget(self.monList)

        self.renameButton = QPushButton("Rename")
        self.renameButton.setFixedWidth(90)
        self.renameButton.clicked.connect(self.OnRename)
        sel.addWidget(self.renameButton)
        sel.addStretch()

        # ============ Left: Stats ============
        sbs_stats = QGroupBox("Stats")
        st = QGridLayout(sbs_stats)
        st.setContentsMargins(12, 12, 12, 12)
        st.setHorizontalSpacing(8)
        st.setVerticalSpacing(6)

        def _make_spin(minv, maxv):
            s = QSpinBox()
            s.setRange(minv, maxv)
            s.setMaximumWidth(90)
            return s

        self.levelSpin  = _make_spin(0, 255);  self.levelSpin.valueChanged.connect(self.OnLevelChanged)
        self.hpSpin     = _make_spin(0, 65535);self.hpSpin.valueChanged.connect(self.OnHpChanged)
        self.mpSpin     = _make_spin(0, 255);  self.mpSpin.valueChanged.connect(self.OnMpChanged)
        self.atkSpin    = _make_spin(0, 255);  self.atkSpin.valueChanged.connect(self.OnAtkChanged)
        self.defSpin    = _make_spin(0, 255);  self.defSpin.valueChanged.connect(self.OnDefChanged)
        self.agiSpin    = _make_spin(0, 255);  self.agiSpin.valueChanged.connect(self.OnAgiChanged)
        self.goldSpin   = _make_spin(0, 65535);self.goldSpin.valueChanged.connect(self.OnGoldChanged)
        self.moveSpin   = _make_spin(0, 255);  self.moveSpin.valueChanged.connect(self.OnMoveChanged)

        self.moveTypeCombo = QComboBox()
        for code, name in MOVE_TYPES:
            self.moveTypeCombo.addItem(name, code)
        self.moveTypeCombo.currentIndexChanged.connect(self.OnMoveTypeChanged)

        rows = [
            ("Level", self.levelSpin),
            ("HP", self.hpSpin),
            ("MP", self.mpSpin),
            ("Attack", self.atkSpin),
            ("Defense", self.defSpin),
            ("Agility", self.agiSpin),
            ("Gold", self.goldSpin),
            ("Move", self.moveSpin),
        ]
        for i, (lbl, w) in enumerate(rows):
            l = QLabel(lbl); l.setFont(self._labelFont())
            st.addWidget(l, i, 0)
            st.addWidget(w, i, 1)

        l = QLabel("MV Type"); l.setFont(self._labelFont())
        st.addWidget(l, len(rows), 0)
        st.addWidget(self.moveTypeCombo, len(rows), 1)
        st.setColumnStretch(2, 1)

        # ============ Center: Inventory / Spells / Battle Sprite ============
        sbs_inv = QGroupBox("Inventory")
        inv = QVBoxLayout(sbs_inv)
        inv.setContentsMargins(8, 8, 8, 8)
        inv.setSpacing(4)
        self.invList = QListWidget()
        self.invList.setMinimumWidth(240)
        self.invList.itemSelectionChanged.connect(self.OnInvSelected)
        inv.addWidget(self.invList)
        self.invCombo = QComboBox()
        self.invCombo.addItems(ITEM_NAMES)
        self.invCombo.currentIndexChanged.connect(self.OnInvChanged)
        inv.addWidget(self.invCombo)
        self.invEquipCheck = QCheckBox("Equipped")
        self.invEquipCheck.toggled.connect(self.OnInvEquipToggled)
        inv.addWidget(self.invEquipCheck)

        sbs_spells = QGroupBox("Spells")
        spl = QVBoxLayout(sbs_spells)
        spl.setContentsMargins(8, 8, 8, 8)
        spl.setSpacing(4)
        self.spellList = QListWidget()
        self.spellList.setMinimumWidth(240)
        self.spellList.itemSelectionChanged.connect(self.OnSpellSelected)
        spl.addWidget(self.spellList)
        self.spellCombo = QComboBox()
        for code in sorted(SPELL_CODES.keys()):
            self.spellCombo.addItem(SPELL_CODES[code], code)
        self.spellCombo.currentIndexChanged.connect(self.OnSpellChanged)
        spl.addWidget(self.spellCombo)

        sbs_bsprite = QGroupBox("Battle Sprite")
        bs = QGridLayout(sbs_bsprite)
        bs.setContentsMargins(8, 8, 8, 8)
        lbl_model = QLabel("Model");   lbl_model.setFont(self._labelFont())
        lbl_pal   = QLabel("Palette"); lbl_pal.setFont(self._labelFont())
        self.modelSpin = QSpinBox(); self.modelSpin.setRange(0, 255); self.modelSpin.setMaximumWidth(70)
        self.modelSpin.valueChanged.connect(self.OnModelChanged)
        self.palSpin   = QSpinBox(); self.palSpin.setRange(0, 255);   self.palSpin.setMaximumWidth(70)
        self.palSpin.valueChanged.connect(self.OnPalChanged)
        bs.addWidget(lbl_model, 0, 0); bs.addWidget(self.modelSpin, 0, 1)
        bs.addWidget(lbl_pal,   1, 0); bs.addWidget(self.palSpin,   1, 1)
        bs.setColumnStretch(2, 1)

        # ============ Right: Resistances ============
        sbs_res = QGroupBox("Resistance - select both for weakness")
        res = QGridLayout(sbs_res)
        res.setContentsMargins(10, 10, 10, 10)
        res.setHorizontalSpacing(10)
        res.setVerticalSpacing(4)

        ELEM_CHECKS = [
            ("25% Wind",      0x01),
            ("50% Wind",      0x02),
            ("25% Lightning", 0x04),
            ("50% Lightning", 0x08),
            ("25% Ice",       0x10),
            ("50% Ice",       0x20),
            ("25% Fire",      0x40),
            ("50% Fire",      0x80),
        ]
        self.elemChecks = []
        for i, (lbl, bit) in enumerate(ELEM_CHECKS):
            cb = QCheckBox(lbl)
            cb.toggled.connect(self.OnElemResChanged)
            self.elemChecks.append((bit, cb))
            res.addWidget(cb, i // 2, i % 2)

        sbs_other = QGroupBox("Other Resist - select both for immunity")
        ot = QHBoxLayout(sbs_other)
        ot.setContentsMargins(8, 8, 8, 8)
        self.minorCheck = QCheckBox("Minor")
        self.majorCheck = QCheckBox("Major")
        self.minorCheck.toggled.connect(self.OnOtherResChanged)
        self.majorCheck.toggled.connect(self.OnOtherResChanged)
        ot.addWidget(self.minorCheck)
        ot.addWidget(self.majorCheck)
        ot.addStretch()

        sbs_pow = QGroupBox("Spell Power")
        pw = QHBoxLayout(sbs_pow)
        pw.setContentsMargins(8, 8, 8, 8)
        self.powSpin = QSpinBox(); self.powSpin.setRange(0, 255); self.powSpin.setMaximumWidth(80)
        self.powSpin.valueChanged.connect(self.OnSpellPowerChanged)
        pw.addWidget(self.powSpin)
        pw.addStretch()

        # ============ Bottom: Crit / Double / Counter ============
        sbs_chances = QGroupBox("Attack Chances")
        ch = QGridLayout(sbs_chances)
        ch.setContentsMargins(10, 10, 10, 10)
        ch.setHorizontalSpacing(10)
        ch.setVerticalSpacing(6)

        l1 = QLabel("Critical:");  l1.setFont(self._labelFont())
        l2 = QLabel("Double:");    l2.setFont(self._labelFont())
        l3 = QLabel("Counter:");   l3.setFont(self._labelFont())

        CRIT_OPTIONS = [
            "150% dmg, 1/32", "125% dmg, 1/32",
            "150% dmg, 1/16", "125% dmg, 1/16",
            "150% dmg, 1/8",  "125% dmg, 1/8",
            "150% dmg, 1/4",  "125% dmg, 1/4",
            "150% dmg, None", "150% dmg, Poison",
            "150% dmg, Sleep","150% dmg, Stun",
            "150% dmg, Muddle","150% dmg, Slow",
            "150% dmg, MP Drain","150% dmg, Silence",
        ]
        DOUBLE_OPTIONS  = [(0x00, "1/32"), (0x10, "1/16"), (0x20, "1/8"), (0x30, "1/4")]
        COUNTER_OPTIONS = [(0x00, "1/32"), (0x40, "1/16"), (0x80, "1/8"), (0xC0, "1/4")]

        self.critCombo = QComboBox(); self.critCombo.addItems(CRIT_OPTIONS)
        self.critCombo.currentIndexChanged.connect(self.OnChancesChanged)
        self.dblCombo = QComboBox()
        for code, name in DOUBLE_OPTIONS: self.dblCombo.addItem(name, code)
        self.dblCombo.currentIndexChanged.connect(self.OnChancesChanged)
        self.ctrCombo = QComboBox()
        for code, name in COUNTER_OPTIONS: self.ctrCombo.addItem(name, code)
        self.ctrCombo.currentIndexChanged.connect(self.OnChancesChanged)

        ch.addWidget(l1, 0, 0); ch.addWidget(self.critCombo, 0, 1)
        ch.addWidget(l2, 1, 0); ch.addWidget(self.dblCombo,  1, 1)
        ch.addWidget(l3, 2, 0); ch.addWidget(self.ctrCombo,  2, 1)
        ch.setColumnStretch(1, 1)

        # ============ Layout ============
        self.sizer.addWidget(sbs_select, 0, 0, 1, 3)
        self.sizer.addWidget(sbs_stats,  1, 0)
        self.sizer.addWidget(sbs_inv,    1, 1)
        self.sizer.addWidget(sbs_spells, 1, 1)
        self.sizer.addWidget(sbs_res,    1, 2)

        self.sizer.removeWidget(sbs_inv)
        self.sizer.removeWidget(sbs_spells)
        self.sizer.removeWidget(sbs_res)

        center = QWidget()
        cl = QVBoxLayout(center)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(6)
        cl.addWidget(sbs_inv)
        cl.addWidget(sbs_spells)
        cl.addWidget(sbs_bsprite)
        cl.addStretch()

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(6)
        rl.addWidget(sbs_res)
        rl.addWidget(sbs_other)
        rl.addWidget(sbs_pow)
        rl.addStretch()

        self.sizer.addWidget(center, 1, 1)
        self.sizer.addWidget(right,  1, 2)
        self.sizer.addWidget(sbs_chances, 2, 0, 1, 3)
        self.sizer.setColumnStretch(0, 0)
        self.sizer.setColumnStretch(1, 1)
        self.sizer.setColumnStretch(2, 0)

        self.loading = False
        self.changeMonster(0)

    # ---------- helpers ----------
    def _labelFont(self):
        f = QFont("MS Sans Serif", 9); f.setBold(False); return f

    def _load_all(self):
        result = []
        try:
            for i in range(NUM_MONSTERS):
                result.append(Monster.from_rom(self.rom, ADDR_PMONSTER_DATA + i * MONSTER_LEN))
        except Exception:
            for _ in range(NUM_MONSTERS):
                result.append(Monster())
        return result

    def _populate_list(self):
        for i in range(NUM_MONSTERS):
            name = MONSTER_NAMES[i] if i < len(MONSTER_NAMES) else f"Monster {i}"
            self.monList.addItem(f"{i}: {name}", i)

    def _ensure_curFileStr(self):
        if not hasattr(self.rom, "curFileStr"):
            try: self.rom.startWriteProcess()
            except Exception: pass

    def _flush(self, m):
        if not m or not m.addr: return
        try:
            self._ensure_curFileStr()
            self.rom.writeBytes(m.addr, m.to_hex())
        except Exception:
            pass

    # ---------- monster name (ROM bank) ----------
    def _name_addr(self, idx):
        addr = read_pointer(self.rom, ADDR_SPELLNAMES_PTR)
        for _ in range(MONSTER_NAME_OFFSET + idx):
            length = int(self.rom.getBytes(addr, 1), 16)
            addr += 1 + length
        return addr

    def _set_monster_name(self, idx, new_name):
        addr = self._name_addr(idx)
        old_len = int(self.rom.getBytes(addr, 1), 16)
        if len(new_name) != old_len:
            raise ValueError(f"Длина должна остаться {old_len}")
        self._ensure_curFileStr()
        self.rom.writeBytes(addr + 1, new_name.encode("ascii").hex())

    def _get_monster_name(self, idx):
        """Читает имя из ROM-банка. При ошибке — fallback на MONSTER_NAMES."""
        try:
            addr = self._name_addr(idx)
            length = int(self.rom.getBytes(addr, 1), 16)
            raw = self.rom.getBytes(addr + 1, length)
            name = bytes.fromhex(raw).decode("ascii", errors="replace")
            if name:
                return name
        except Exception:
            pass
        return MONSTER_NAMES[idx] if idx < len(MONSTER_NAMES) else f"Monster {idx}"

    # ---------- battle sprite / gold addresses ----------
    def _bsprite_addr(self, idx): return ADDR_BATTLE_SPRITES + BSPRITE_OFFSET + idx * 2
    def _gold_addr(self, idx):    return ADDR_GOLD_BASE + idx * 2

    # ---------- loading monster ----------
    def changeMonster(self, num=None):
        if num is not None:
            self.curIdx = num
        if not (0 <= self.curIdx < len(self.monsters)):
            self.monster = None
            return

        self.monster = self.monsters[self.curIdx]
        m = self.monster

        self.loading = True
        try:
            self.levelSpin.setValue(m.level)
            self.hpSpin.setValue(m.hp)
            self.mpSpin.setValue(m.mp)
            self.atkSpin.setValue(m.atk)
            self.defSpin.setValue(m.dfn)
            self.agiSpin.setValue(m.agi)
            self.moveSpin.setValue(m.move)
            self.powSpin.setValue(m.spellpower)

            for i in range(self.moveTypeCombo.count()):
                if self.moveTypeCombo.itemData(i) == m.move_type:
                    self.moveTypeCombo.setCurrentIndex(i); break

            addr = self._gold_addr(self.curIdx)
            gold = (int(self.rom.getBytes(addr, 1), 16) << 8) | int(self.rom.getBytes(addr+1, 1), 16)
            self.goldSpin.setValue(gold)

            baddr = self._bsprite_addr(self.curIdx)
            self.modelSpin.setValue(int(self.rom.getBytes(baddr, 1), 16))
            self.palSpin.setValue(int(self.rom.getBytes(baddr+1, 1), 16))

            # Inventory
            self.invList.clear()
            for i in range(4):
                idx, eq = m.get_item(i)
                name = ITEM_NAMES[idx] if 0 <= idx < len(ITEM_NAMES) else "Empty"
                label = f"{name} (Equipped)" if eq else name
                self.invList.addItem(label)
            self.invList.setFixedHeight(self.invList.sizeHintForRow(0) * 4
                                        + 2 * self.invList.frameWidth() + 4)

            # Spells
            self.spellList.clear()
            for i in range(4):
                code = m.get_spell(i)
                name = SPELL_CODES.get(code, "Nothing")
                self.spellList.addItem(name)
            self.spellList.setFixedHeight(self.spellList.sizeHintForRow(0) * 4
                                          + 2 * self.spellList.frameWidth() + 4)

            er = m.elem_res
            for bit, cb in self.elemChecks:
                cb.setChecked(bool(er & bit))

            self.minorCheck.setChecked(bool(m.other_res & 0x40))
            self.majorCheck.setChecked(bool(m.other_res & 0x80))

            ac = m.atk_chances
            crit_idx = ac & 0x0F
            if 0 <= crit_idx < self.critCombo.count():
                self.critCombo.setCurrentIndex(crit_idx)
            dbl = ac & 0x30
            for i in range(self.dblCombo.count()):
                if self.dblCombo.itemData(i) == dbl:
                    self.dblCombo.setCurrentIndex(i); break
            ctr = ac & 0xC0
            for i in range(self.ctrCombo.count()):
                if self.ctrCombo.itemData(i) == ctr:
                    self.ctrCombo.setCurrentIndex(i); break
        finally:
            self.loading = False

        self.updateModifiedIndicator(getattr(m, "modified", False))

    # ---------- signals ----------
    def OnSelectMonster(self, idx):
        if self.loading: return
        self.changeMonster(idx)

    def OnLevelChanged(self, v):
        if self.loading or self.monster is None: return
        self.monster.level = v; self._flush(self.monster); self._mark_modified()

    def OnHpChanged(self, v):
        if self.loading or self.monster is None: return
        self.monster.hp = v; self._flush(self.monster); self._mark_modified()

    def OnMpChanged(self, v):
        if self.loading or self.monster is None: return
        self.monster.mp = v; self._flush(self.monster); self._mark_modified()

    def OnAtkChanged(self, v):
        if self.loading or self.monster is None: return
        self.monster.atk = v; self._flush(self.monster); self._mark_modified()

    def OnDefChanged(self, v):
        if self.loading or self.monster is None: return
        self.monster.dfn = v; self._flush(self.monster); self._mark_modified()

    def OnAgiChanged(self, v):
        if self.loading or self.monster is None: return
        self.monster.agi = v; self._flush(self.monster); self._mark_modified()

    def OnMoveChanged(self, v):
        if self.loading or self.monster is None: return
        self.monster.move = v; self._flush(self.monster); self._mark_modified()

    def OnSpellPowerChanged(self, v):
        if self.loading or self.monster is None: return
        self.monster.spellpower = v; self._flush(self.monster); self._mark_modified()

    def OnMoveTypeChanged(self, idx):
        if self.loading or self.monster is None or idx < 0: return
        self.monster.move_type = self.moveTypeCombo.itemData(idx)
        self._flush(self.monster); self._mark_modified()

    def OnGoldChanged(self, v):
        if self.loading or self.monster is None: return
        addr = self._gold_addr(self.curIdx)
        self._ensure_curFileStr()
        try:
            self.rom.writeBytes(addr, "%04x" % (v & 0xFFFF))
        except Exception:
            pass
        self._mark_modified()

    def OnModelChanged(self, v):
        if self.loading or self.monster is None: return
        addr = self._bsprite_addr(self.curIdx)
        self._ensure_curFileStr()
        try: self.rom.writeBytes(addr, "%02x" % (v & 0xFF))
        except Exception: pass
        self._mark_modified()

    def OnPalChanged(self, v):
        if self.loading or self.monster is None: return
        addr = self._bsprite_addr(self.curIdx) + 1
        self._ensure_curFileStr()
        try: self.rom.writeBytes(addr, "%02x" % (v & 0xFF))
        except Exception: pass
        self._mark_modified()

    # --- inventory ---
    def OnInvSelected(self):
        if self.loading or self.monster is None: return
        row = self.invList.currentRow()
        if row < 0: return
        idx, eq = self.monster.get_item(row)
        self.loading = True
        if 0 <= idx < self.invCombo.count():
            self.invCombo.setCurrentIndex(idx)
        else:
            self.invCombo.setCurrentIndex(-1)
        self.invEquipCheck.setChecked(eq)
        self.loading = False

    def OnInvChanged(self, idx):
        if self.loading or self.monster is None: return
        row = self.invList.currentRow()
        if row < 0 or idx < 0: return
        eq = self.invEquipCheck.isChecked()
        self.monster.set_item(row, idx, eq)
        item = self.invList.item(row)
        if item:
            name = ITEM_NAMES[idx] if 0 <= idx < len(ITEM_NAMES) else "Empty"
            item.setText(f"{name} (Equipped)" if eq else name)
        self._flush(self.monster); self._mark_modified()

    def OnInvEquipToggled(self, _c):
        if self.loading or self.monster is None: return
        self.OnInvChanged(self.invCombo.currentIndex())

    # --- spells ---
    def OnSpellSelected(self):
        if self.loading or self.monster is None: return
        row = self.spellList.currentRow()
        if row < 0: return
        code = self.monster.get_spell(row)
        self.loading = True
        for i in range(self.spellCombo.count()):
            if self.spellCombo.itemData(i) == code:
                self.spellCombo.setCurrentIndex(i); break
        self.loading = False

    def OnSpellChanged(self, _idx):
        if self.loading or self.monster is None: return
        row = self.spellList.currentRow()
        if row < 0: return
        code = self.spellCombo.currentData()
        if code is None: return
        self.monster.set_spell(row, code)
        item = self.spellList.item(row)
        if item:
            item.setText(SPELL_CODES.get(code, "Nothing"))
        self._flush(self.monster); self._mark_modified()

    # --- resistances ---
    def OnElemResChanged(self, _c):
        if self.loading or self.monster is None: return
        val = 0
        for bit, cb in self.elemChecks:
            if cb.isChecked(): val |= bit
        self.monster.elem_res = val
        self._flush(self.monster); self._mark_modified()

    def OnOtherResChanged(self, _c):
        if self.loading or self.monster is None: return
        val = 0
        if self.minorCheck.isChecked(): val |= 0x40
        if self.majorCheck.isChecked(): val |= 0x80
        self.monster.other_res = val
        self._flush(self.monster); self._mark_modified()

    # --- chances ---
    def OnChancesChanged(self, _idx):
        if self.loading or self.monster is None: return
        val = self.critCombo.currentIndex() & 0x0F
        dbl = self.dblCombo.currentData()
        ctr = self.ctrCombo.currentData()
        if dbl is not None: val |= (dbl & 0x30)
        if ctr is not None: val |= (ctr & 0xC0)
        self.monster.atk_chances = val
        self._flush(self.monster); self._mark_modified()

    # ---------- rename ----------
    def OnRename(self):
        if self.monster is None:
            return
        idx = self.curIdx
        old_name = self._get_monster_name(idx)
        max_len = len(old_name)

        new_name, ok = QInputDialog.getText(
            self, "Rename",
            f"Новое имя для монстра '{old_name}' (не длиннее {max_len}):",
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
        try:
            self._set_monster_name(idx, new_name.ljust(max_len))
        except Exception as e:
            QMessageBox.critical(self, "Rename", f"Не удалось записать:\n{e}")
            return

        # обновляем RAM и UI
        while len(MONSTER_NAMES) <= idx:
            MONSTER_NAMES.append(f"Monster {len(MONSTER_NAMES)}")
        MONSTER_NAMES[idx] = new_name

        self.monList.setItemText(idx, f"{idx}: {new_name}")
        self.monster.modified = True
        self._mark_modified()

    # ---------- internal ----------
    def _mark_modified(self):
        self.updateModifiedIndicator(True)
        try: self.parent.modify()
        except Exception: pass

    # ---------- panel hooks ----------
    def OnShow(self, event=None):
        if self.monster is not None:
            self.changeMonster(self.curIdx)

    def getCurrentData(self): return getattr(self, "monster", None)
    def getCurrentSpriteObject(self): return getattr(self, "monster", None)
    changeSelection = changeMonster