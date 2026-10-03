# sf2edit/spells.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QComboBox, QSpinBox,
    QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

import rompanel


# ---------- ROM-адреса ----------
ADDR_PSPELLS_PTR     = 65680       # pSpells = LoadPointer(65680)
ADDR_SPELLNAMES_PTR  = 33476       # pSpellNames

NUM_SPELLS    = 88
SPELL_LEN     = 8
SPELLNAMES_SPELLS_COUNT = 44       # 0..43 — имена заклинаний в банке


SPELL_CODES = {
    0x3F: "Nothing",
    0x00: "Heal 1",   0x40: "Heal 2",   0x80: "Heal 3",   0xC0: "Heal 4",
    0x01: "Aura 1",   0x41: "Aura 2",   0x81: "Aura 3",   0xC1: "Aura 4",
    0x0B: "Blaze 1",  0x4B: "Blaze 2",  0x8B: "Blaze 3",  0xCB: "Blaze 4",
    0x0C: "Freeze 1", 0x4C: "Freeze 2", 0x8C: "Freeze 3", 0xCC: "Freeze 4",
    0x0D: "Bolt 1",   0x4D: "Bolt 2",   0x8D: "Bolt 3",   0xCD: "Bolt 4",
    0x0E: "Blast 1",  0x4E: "Blast 2",  0x8E: "Blast 3",  0xCE: "Blast 4",
    0x03: "Boost 1",  0x43: "Boost 2",
    0x04: "Slow 1",   0x44: "Slow 2",
    0x05: "Attack 1", 0x45: "Attack Boost",
    0x06: "Dispel 1",
    0x07: "Muddle 1", 0x47: "Muddle 2",
    0x08: "Desoul 1", 0x48: "Desoul 2",
    0x09: "Sleep 1",
    0x0A: "Egress 1",
    0x02: "Detox 1",  0x42: "Detox 2",  0x82: "Detox 3",  0xC2: "Detox 4",
    0x1B: "Katon 1",  0x5B: "Katon 2",  0x9B: "Katon 3",
    0x1C: "Raijin 1", 0x5C: "Raijin 2", 0x9C: "Raijin 3",
    0x1D: "Dao 1",    0x5D: "Dao 2",
    0x1E: "Apollo 1", 0x5E: "Apollo 2",
    0x1F: "Neptune 1",0x5F: "Neptune 2",
    0x20: "Atlas 1",  0x60: "Atlas 2",
    0x11: "Flame Breath", 0x51: "Flame Breath 2", 0x91: "Flame Breath 3",
    0x12: "Snow Breath",  0x52: "Snow Breath 2",  0x92: "Snow Breath 3",
    0x13: "Demon Breath", 0x53: "Demon Breath 2",
    0x29: "Kiwi Flame Breath", 0x69: "Kiwi Flame Breath 2",
    0xA9: "Kiwi Flame Breath 3", 0xE9: "Kiwi Flame Breath 4",
    0x28: "Kraken Bubble Breath",
    0x2B: "Odd Eye Laser",
    0x0F: "Magic Drain",
    0x10: "Medical Herb",
    0x14: "Power Water",
    0x15: "Protect Milk",
    0x16: "Quick Chicken",
    0x17: "Running Pimento",
    0x18: "Cheerful Bread",
    0x19: "Burst Rock",
    0x1A: "Laser",
    0x21: "Fairy Powder",
    0x22: "Restore MP?",
    0x23: "Bright Honey",
    0x24: "Brave Apple",
    0x25: "Shining Ball",
    0x26: "Blizzard",
    0x27: "Holy Thunder",
    0x2A: "Right of Hope",
    0x37: "Freeze Game",
    0x49: "Ally Sleep",
    0x4A: "Fairy of Nothing (Egress 2?)",
    0x4F: "MP Ally Absorb",
    0x50: "Healing Seed",
    0x54: "Attack Increase",
    0x55: "Defense Increase",
    0x56: "Agility Increase",
    0x57: "Move Increase",
    0x58: "Max HP Increase",
    0x62: "Fairy Tear",
    0x63: "Max MP Increase",
    0x64: "Level Up",
    0x66: "Damage Fairy",
    0x68: "Bubble Breath",
    0x6A: "MP Recover",
    0x83: "Boost Item",
    0x84: "Unboost Item",
    0x85: "Attack Item",
    0x86: "Silence Fairy",
    0x87: "Muddle Fairy",
    0x88: "Desoul Fairy",
    0x89: "Sleep Fairy",
    0x8F: "MP Absorb Fairy",
    0x90: "Healing Drop",
    0x94: "Attack Increase",
    0x95: "Defense Increase",
    0x96: "Agility Increase",
    0x97: "Move Increase",
    0x98: "Max HP Increase",
    0xA2: "MP Restore",
    0xA3: "Max MP Increase",
    0xA4: "Level Up",
    0xC3: "Adjacent Boost",
    0xC4: "Adjacent Unboost",
    0xCF: "MP Absorb Fairy",
}

SPELL_TYPES = {
    0:   "Special Attack",
    3:   "Magic Drain",
    65:  "Heal Item",
    67:  "Buff Item",
    128: "Attack",
    130: "Debuff",
    193: "Heal",
    194: "Buff",
    195: "Egress",
}


# ---------- helpers ----------
def read_pointer(rom, ptr_addr):
    return int(rom.getBytes(ptr_addr + 1, 3), 16)


def spell_bank_index(code):
    """Индекс имени заклинания в банке pSpellNames."""
    if code <= 0x2B:
        return code
    if 0x40 <= code <= 0xFF:
        base = code & 0x3F
        if base <= 0x2B:
            return base
    return None


class Spell:
    __slots__ = ("addr", "code", "mp_cost", "animation", "type",
                 "max_range", "min_range", "aoe", "effect", "modified")

    def __init__(self, addr=0):
        self.addr = addr
        self.code = 0
        self.mp_cost = 0
        self.animation = 0
        self.type = 0
        self.max_range = 0
        self.min_range = 0
        self.aoe = 0
        self.effect = 0
        self.modified = False

    @classmethod
    def from_rom(cls, rom, addr):
        raw = rom.getBytes(addr, SPELL_LEN)
        s = cls(addr=addr)
        s.code      = int(raw[0:2],  16)
        s.mp_cost   = int(raw[2:4],  16)
        s.animation = int(raw[4:6],  16)
        s.type      = int(raw[6:8],  16)
        s.max_range = int(raw[8:10], 16)
        s.min_range = int(raw[10:12],16)
        s.aoe       = int(raw[12:14],16)
        s.effect    = int(raw[14:16],16)
        return s

    def to_hex(self):
        return "%02x%02x%02x%02x%02x%02x%02x%02x" % (
            self.code & 0xFF,
            self.mp_cost & 0xFF,
            self.animation & 0xFF,
            self.type & 0xFF,
            self.max_range & 0xFF,
            self.min_range & 0xFF,
            self.aoe & 0xFF,
            self.effect & 0xFF,
        )


# =========================================================
# Panel
# =========================================================
class SpellPanel(rompanel.ROMPanel):
    frameTitle = "Spells"
    canMaximize = False

    def init(self):
        if self.rom is None:
            return

        self.loading = True
        self.spell = None
        self.curIdx = 0

        if "spells" not in self.rom.data or not self.rom.data["spells"]:
            self.rom.data["spells"] = self._load_all()
        self.spells = self.rom.data["spells"]

        # ---------- Select ----------
        sbs_select = QGroupBox("Select")
        sel = QHBoxLayout(sbs_select)
        sel.setContentsMargins(8, 8, 8, 8)
        sel.setSpacing(8)

        self.spellList = QComboBox()
        self.spellList.setMinimumWidth(220)
        self._populate_list()
        self.spellList.currentIndexChanged.connect(self.OnSelectSpell)
        sel.addWidget(self.spellList)

        self.renameButton = QPushButton("Rename")
        self.renameButton.setFixedWidth(90)
        self.renameButton.clicked.connect(self.OnRename)
        sel.addWidget(self.renameButton)
        sel.addStretch()

        # ---------- Effect ----------
        sbs_effect = QGroupBox()
        ef = QHBoxLayout(sbs_effect)
        ef.setContentsMargins(12, 12, 12, 12)
        ef.setSpacing(8)
        l = QLabel("Effect"); l.setFont(self._labelFont())
        self.effectSpin = QSpinBox(); self.effectSpin.setRange(0, 255); self.effectSpin.setMaximumWidth(70)
        self.effectSpin.valueChanged.connect(self.OnEffectChanged)
        ef.addWidget(l)
        ef.addWidget(self.effectSpin)
        ef.addStretch()

        # ---------- Fields ----------
        sbs_fields = QGroupBox()
        fl = QGridLayout(sbs_fields)
        fl.setContentsMargins(12, 12, 12, 12)
        fl.setHorizontalSpacing(10)
        fl.setVerticalSpacing(8)

        def _label(txt):
            x = QLabel(txt); x.setFont(self._labelFont()); return x

        # Type
        self.typeCombo = QComboBox()
        for code in sorted(SPELL_TYPES.keys()):
            self.typeCombo.addItem(SPELL_TYPES[code], code)
        self.typeCombo.currentIndexChanged.connect(self.OnTypeChanged)

        # MP / Animation / Min / Max / AoE — спины
        self.mpSpin  = QSpinBox(); self.mpSpin.setRange(0, 255);  self.mpSpin.setMaximumWidth(70)
        self.mpSpin.valueChanged.connect(self.OnMpChanged)
        self.animSpin= QSpinBox(); self.animSpin.setRange(0, 255); self.animSpin.setMaximumWidth(70)
        self.animSpin.valueChanged.connect(self.OnAnimChanged)
        self.minSpin = QSpinBox(); self.minSpin.setRange(0, 255); self.minSpin.setMaximumWidth(70)
        self.minSpin.valueChanged.connect(self.OnMinChanged)
        self.maxSpin = QSpinBox(); self.maxSpin.setRange(0, 255); self.maxSpin.setMaximumWidth(70)
        self.maxSpin.valueChanged.connect(self.OnMaxChanged)
        self.aoeSpin = QSpinBox(); self.aoeSpin.setRange(0, 255); self.aoeSpin.setMaximumWidth(70)
        self.aoeSpin.valueChanged.connect(self.OnAoeChanged)

        fl.addWidget(_label("Type"),        0, 0); fl.addWidget(self.typeCombo, 0, 1)
        fl.addWidget(_label("MP Cost"),     1, 0); fl.addWidget(self.mpSpin,    1, 1)
        fl.addWidget(_label("Animation"),   2, 0); fl.addWidget(self.animSpin,  2, 1)
        fl.addWidget(_label("Min Range"),   0, 2); fl.addWidget(self.minSpin,   0, 3)
        fl.addWidget(_label("Max Range"),   1, 2); fl.addWidget(self.maxSpin,   1, 3)
        fl.addWidget(_label("AoE"),         2, 2); fl.addWidget(self.aoeSpin,   2, 3)
        fl.setColumnStretch(1, 1)
        fl.setColumnStretch(3, 1)

        # ---------- Layout ----------
        self.sizer.addWidget(sbs_select, 0, 0)
        self.sizer.addWidget(sbs_effect, 0, 1)
        self.sizer.addWidget(sbs_fields, 1, 0, 1, 2)
        self.sizer.setRowStretch(2, 1)

        self.loading = False
        self.changeSpell(0)

    # ---------- helpers ----------
    def _labelFont(self):
        f = QFont("MS Sans Serif", 9); f.setBold(False); return f

    def _load_all(self):
        result = []
        try:
            pSp = read_pointer(self.rom, ADDR_PSPELLS_PTR)
            for i in range(NUM_SPELLS):
                result.append(Spell.from_rom(self.rom, pSp + i * SPELL_LEN))
        except Exception:
            for _ in range(NUM_SPELLS):
                result.append(Spell(addr=0))
        return result

    def _populate_list(self):
        for i in range(NUM_SPELLS):
            code = self.spells[i].code if i < len(self.spells) else 0
            name = SPELL_CODES.get(code, f"Spell {i}")
            self.spellList.addItem(f"{i}: {name}", i)

    def _ensure_curFileStr(self):
        if not hasattr(self.rom, "curFileStr"):
            try: self.rom.startWriteProcess()
            except Exception: pass

    def _flush(self, s):
        if not s or not s.addr: return
        try:
            self._ensure_curFileStr()
            self.rom.writeBytes(s.addr, s.to_hex())
        except Exception:
            pass

    # ---------- name (ROM bank, pSpellNames @ spell_bank_index) ----------
    def _name_addr(self, bank_index):
        addr = read_pointer(self.rom, ADDR_SPELLNAMES_PTR)
        for _ in range(bank_index):
            length = int(self.rom.getBytes(addr, 1), 16)
            addr += 1 + length
        return addr

    def _get_bank_name(self, code):
        bi = spell_bank_index(code)
        if bi is None:
            return None
        try:
            addr = self._name_addr(bi)
            length = int(self.rom.getBytes(addr, 1), 16)
            raw = self.rom.getBytes(addr + 1, length)
            return bytes.fromhex(raw).decode("ascii", errors="replace")
        except Exception:
            return None

    def _set_bank_name(self, code, new_name):
        bi = spell_bank_index(code)
        if bi is None:
            raise ValueError("У этого кода нет имени в банке заклинаний")
        addr = self._name_addr(bi)
        old_len = int(self.rom.getBytes(addr, 1), 16)
        if len(new_name) != old_len:
            raise ValueError(f"Длина должна остаться {old_len}")
        self._ensure_curFileStr()
        self.rom.writeBytes(addr + 1, new_name.encode("ascii").hex())

    # ---------- change ----------
    def changeSpell(self, num=None):
        if num is not None:
            self.curIdx = num
        if not (0 <= self.curIdx < len(self.spells)):
            self.spell = None
            return

        self.spell = self.spells[self.curIdx]
        s = self.spell

        self.loading = True
        try:
            for i in range(self.typeCombo.count()):
                if self.typeCombo.itemData(i) == s.type:
                    self.typeCombo.setCurrentIndex(i); break

            self.mpSpin.setValue(s.mp_cost)
            self.animSpin.setValue(s.animation)
            self.minSpin.setValue(s.min_range)
            self.maxSpin.setValue(s.max_range)
            self.aoeSpin.setValue(s.aoe)
            self.effectSpin.setValue(s.effect)
        finally:
            self.loading = False

        self.updateModifiedIndicator(getattr(s, "modified", False))

    # ---------- signals ----------
    def OnSelectSpell(self, _idx):
        if self.loading: return
        data = self.spellList.currentData()
        if data is None: return
        self.changeSpell(data)

    def OnTypeChanged(self, _idx):
        if self.loading or self.spell is None: return
        code = self.typeCombo.currentData()
        if code is None: return
        self.spell.type = code
        self.spell.modified = True
        self._flush(self.spell); self._mark_modified()

    def OnMpChanged(self, v):
        if self.loading or self.spell is None: return
        self.spell.mp_cost = v; self.spell.modified = True
        self._flush(self.spell); self._mark_modified()

    def OnAnimChanged(self, v):
        if self.loading or self.spell is None: return
        self.spell.animation = v; self.spell.modified = True
        self._flush(self.spell); self._mark_modified()

    def OnMinChanged(self, v):
        if self.loading or self.spell is None: return
        self.spell.min_range = v; self.spell.modified = True
        self._flush(self.spell); self._mark_modified()

    def OnMaxChanged(self, v):
        if self.loading or self.spell is None: return
        self.spell.max_range = v; self.spell.modified = True
        self._flush(self.spell); self._mark_modified()

    def OnAoeChanged(self, v):
        if self.loading or self.spell is None: return
        self.spell.aoe = v; self.spell.modified = True
        self._flush(self.spell); self._mark_modified()

    def OnEffectChanged(self, v):
        if self.loading or self.spell is None: return
        self.spell.effect = v; self.spell.modified = True
        self._flush(self.spell); self._mark_modified()

    # ---------- rename ----------
    def OnRename(self):
        if self.spell is None:
            return
        code = self.spell.code

        old_name = self._get_bank_name(code)
        if old_name is None:
            QMessageBox.information(
                self, "Rename",
                f"У кода 0x{code:02X} нет имени в банке заклинаний.\n"
                "Переименование недоступно."
            )
            return

        max_len = len(old_name)
        new_name, ok = QInputDialog.getText(
            self, "Rename",
            f"Новое имя для '{old_name}' (не длиннее {max_len}):",
            text=old_name,
        )
        if not ok: return
        new_name = new_name.strip()
        if not new_name: return
        if len(new_name) > max_len:
            QMessageBox.warning(self, "Rename",
                                f"Слишком длинное имя.\nМаксимум — {max_len}.")
            return
        try:
            self._set_bank_name(code, new_name.ljust(max_len))
        except Exception as e:
            QMessageBox.critical(self, "Rename", f"Не удалось записать:\n{e}")
            return

        # Обновляем все записи в таблице, использующие тот же bank_index
        bi = spell_bank_index(code)
        for i in range(self.spellList.count()):
            idx = self.spellList.itemData(i)
            other = self.spells[idx]
            if spell_bank_index(other.code) == bi:
                # отображаем новое имя с суффиксом уровня, если он был
                suffix = SPELL_CODES.get(other.code, "")
                # вырезаем цифру уровня из старого имени, если была
                num = ""
                for ch in suffix.split():
                    if ch.isdigit():
                        num = " " + ch
                display = new_name + num if num else new_name
                self.spellList.setItemText(i, f"{idx}: {display}")

        self.spell.modified = True
        self._mark_modified()

    # ---------- internal ----------
    def _mark_modified(self):
        self.updateModifiedIndicator(True)
        try: self.parent.modify()
        except Exception: pass

    # ---------- panel hooks ----------
    def OnShow(self, event=None):
        if self.spell is not None:
            self.changeSpell(self.curIdx)

    def getCurrentData(self): return getattr(self, "spell", None)
    def getCurrentSpriteObject(self): return getattr(self, "spell", None)
    changeSelection = changeSpell