# sf2edit/special.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QCheckBox, QSpinBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

import rompanel


# ---------- ROM-адреса ----------
ADDR_BREATH_CHANCE = 147623   # 0x240A7
ADDR_KIWI_LVL2     = 147655   # 0x241C7
ADDR_KIWI_LVL3     = 147663   # 0x241CF
ADDR_KIWI_LVL4     = 147671   # 0x241D7
ADDR_KIWI_SPELL    = 147681   # 0x241E1
ADDR_SORC_SPELL    = 135501   # 0x2114D
ADDR_SPELLPOWER    = 47989    # 0x0BB75
ADDR_SUPER_ATTACK  = 1775083  # 0x1B14AB
ADDR_CURSE         = 40895    # 0x09FBF
ADDR_STUN          = 40921    # 0x09FD9
ADDR_TAUROS        = 40724    # 0x09F14

TAUROS_ON  = 102              # 0x66
TAUROS_OFF = 96               # 0x60


# Список имён базовых заклинаний (индексы 0..43 в банке pSpellNames)
BASE_SPELL_NAMES = [
    "Heal",           "Aura",           "Detox",          "Boost",
    "Slow",           "Attack",         "Dispel",         "Muddle",
    "Desoul",         "Sleep",          "Egress",         "Blaze",
    "Freeze",         "Bolt",           "Blast",          "Magic Drain",
    "Medical Herb",   "Flame Breath",   "Snow Breath",    "Demon Breath",
    "Power Water",    "Protect Milk",   "Quick Chicken",  "Running Pimento",
    "Cheerful Bread", "Burst Rock",     "Laser",          "Katon",
    "Raijin",         "Dao",            "Apollo",         "Neptune",
    "Atlas",          "Fairy Powder",   "Restore MP?",    "Bright Honey",
    "Brave Apple",    "Shining Ball",   "Blizzard",       "Holy Thunder",
    "Kraken Bubble",  "Kiwi Flame",     "Right of Hope",  "Odd Eye Laser",
]


class SpecialPanel(rompanel.ROMPanel):
    frameTitle = "Special"
    canMaximize = False

    def init(self):
        if self.rom is None:
            return

        self.loading = True

        # ============ Kiwi's Atomic Fire Breath ============
        sbs_kiwi = QGroupBox("Kiwi's Atomic Fire Breath")
        kl = QGridLayout(sbs_kiwi)
        kl.setContentsMargins(12, 12, 12, 12)
        kl.setHorizontalSpacing(10)
        kl.setVerticalSpacing(6)

        # Chance to use  1 : X
        lbl_chance = QLabel("Chance to use"); lbl_chance.setFont(self._labelFont())
        lbl_one_1  = QLabel("1 :");            lbl_one_1.setFont(self._labelFont())
        self.breathSpin = QSpinBox(); self.breathSpin.setRange(0, 255)
        self.breathSpin.setMaximumWidth(70)
        self.breathSpin.valueChanged.connect(self.OnBreathChanged)

        # Level 2 @ Level
        lbl_lvl2 = QLabel("Level 2"); lbl_lvl2.setFont(self._labelFont())
        lbl_at_2 = QLabel("@ Level"); lbl_at_2.setFont(self._labelFont())
        self.kiwiLvl2 = QSpinBox(); self.kiwiLvl2.setRange(0, 255)
        self.kiwiLvl2.setMaximumWidth(70)
        self.kiwiLvl2.valueChanged.connect(self.OnKiwiLvl2Changed)

        # Level 3 @ Level
        lbl_lvl3 = QLabel("Level 3"); lbl_lvl3.setFont(self._labelFont())
        lbl_at_3 = QLabel("@ Level"); lbl_at_3.setFont(self._labelFont())
        self.kiwiLvl3 = QSpinBox(); self.kiwiLvl3.setRange(0, 255)
        self.kiwiLvl3.setMaximumWidth(70)
        self.kiwiLvl3.valueChanged.connect(self.OnKiwiLvl3Changed)

        # Level 4 @ Level
        lbl_lvl4 = QLabel("Level 4"); lbl_lvl4.setFont(self._labelFont())
        lbl_at_4 = QLabel("@ Level"); lbl_at_4.setFont(self._labelFont())
        self.kiwiLvl4 = QSpinBox(); self.kiwiLvl4.setRange(0, 255)
        self.kiwiLvl4.setMaximumWidth(70)
        self.kiwiLvl4.valueChanged.connect(self.OnKiwiLvl4Changed)

        # Spell (выбор имени из банка)
        self.kiwiSpellCombo = QComboBox()
        self.kiwiSpellCombo.setMinimumWidth(180)
        for i, name in enumerate(BASE_SPELL_NAMES):
            self.kiwiSpellCombo.addItem(name, i)
        self.kiwiSpellCombo.currentIndexChanged.connect(self.OnKiwiSpellChanged)

        kl.addWidget(lbl_chance, 0, 0)
        kl.addWidget(lbl_one_1,  0, 1)
        kl.addWidget(self.breathSpin, 0, 2)
        kl.addWidget(lbl_lvl2, 1, 0)
        kl.addWidget(lbl_at_2, 1, 1)
        kl.addWidget(self.kiwiLvl2, 1, 2)
        kl.addWidget(lbl_lvl3, 2, 0)
        kl.addWidget(lbl_at_3, 2, 1)
        kl.addWidget(self.kiwiLvl3, 2, 2)
        kl.addWidget(lbl_lvl4, 3, 0)
        kl.addWidget(lbl_at_4, 3, 1)
        kl.addWidget(self.kiwiLvl4, 3, 2)
        kl.addWidget(self.kiwiSpellCombo, 4, 0, 1, 3)
        kl.setColumnStretch(3, 1)

        # ============ Basic SORC Spell ============
        sbs_sorc = QGroupBox("Basic SORC Spell")
        sl = QVBoxLayout(sbs_sorc)
        sl.setContentsMargins(12, 12, 12, 12)
        self.sorcCombo = QComboBox()
        self.sorcCombo.setMinimumWidth(200)
        for i, name in enumerate(BASE_SPELL_NAMES):
            self.sorcCombo.addItem(name, i)
        self.sorcCombo.currentIndexChanged.connect(self.OnSorcChanged)
        sl.addWidget(self.sorcCombo)

        # ============ Spellpower After Promotion ============
        sbs_pow = QGroupBox("Spellpower After Promotion")
        pl = QHBoxLayout(sbs_pow)
        pl.setContentsMargins(12, 12, 12, 12)
        self.powSpin = QSpinBox(); self.powSpin.setRange(0, 255)
        self.powSpin.setMaximumWidth(70)
        self.powSpin.valueChanged.connect(self.OnPowerChanged)
        pl.addWidget(self.powSpin)
        pl.addWidget(QLabel("/ 4"))
        pl.addStretch()

        # ============ Attack In Super Mode ============
        sbs_super = QGroupBox("Attack In Super Mode")
        spl = QHBoxLayout(sbs_super)
        spl.setContentsMargins(12, 12, 12, 12)
        self.superSpin = QSpinBox(); self.superSpin.setRange(0, 255)
        self.superSpin.setMaximumWidth(70)
        self.superSpin.valueChanged.connect(self.OnSuperChanged)
        spl.addWidget(self.superSpin)
        spl.addWidget(QLabel("/ 4"))
        spl.addStretch()

        # ============ Curse Paralysis Chance ============
        sbs_curse = QGroupBox("Curse Paralysis Chance")
        cl = QHBoxLayout(sbs_curse)
        cl.setContentsMargins(12, 12, 12, 12)
        cl.addWidget(QLabel("1 /"))
        self.curseSpin = QSpinBox(); self.curseSpin.setRange(0, 255)
        self.curseSpin.setMaximumWidth(70)
        self.curseSpin.valueChanged.connect(self.OnCurseChanged)
        cl.addWidget(self.curseSpin)
        cl.addStretch()

        # ============ Stun Paralysis Chance ============
        sbs_stun = QGroupBox("Stun Paralysis Chance")
        stl = QHBoxLayout(sbs_stun)
        stl.setContentsMargins(12, 12, 12, 12)
        stl.addWidget(QLabel("1 /"))
        self.stunSpin = QSpinBox(); self.stunSpin.setRange(0, 255)
        self.stunSpin.setMaximumWidth(70)
        self.stunSpin.valueChanged.connect(self.OnStunChanged)
        stl.addWidget(self.stunSpin)
        stl.addStretch()

        # ============ Taurus ============
        sbs_tauros = QGroupBox()
        tl = QHBoxLayout(sbs_tauros)
        tl.setContentsMargins(12, 12, 12, 12)
        self.taurosCheck = QCheckBox("Taurus Can Only Be Damaged By the Achilles Sword")
        self.taurosCheck.toggled.connect(self.OnTaurosChanged)
        tl.addWidget(self.taurosCheck)
        tl.addStretch()

        # ============ Layout ============
        self.sizer.addWidget(sbs_kiwi,   0, 0, 2, 1)
        self.sizer.addWidget(sbs_sorc,   2, 0)
        self.sizer.addWidget(sbs_pow,    0, 1)
        self.sizer.addWidget(sbs_super,  1, 1)
        self.sizer.addWidget(sbs_curse,  2, 1)
        self.sizer.addWidget(sbs_stun,   3, 0)
        self.sizer.addWidget(sbs_tauros, 3, 1)
        self.sizer.setColumnStretch(0, 1)
        self.sizer.setColumnStretch(1, 1)
        self.sizer.setRowStretch(4, 1)

        self.loading = False
        self._reload()

    # ---------- helpers ----------
    def _labelFont(self):
        f = QFont("MS Sans Serif", 9); f.setBold(False); return f

    def _ensure_curFileStr(self):
        if not hasattr(self.rom, "curFileStr"):
            try: self.rom.startWriteProcess()
            except Exception: pass

    def _read_byte(self, addr):
        try:
            return int(self.rom.getBytes(addr, 1), 16)
        except Exception:
            return 0

    def _write_byte(self, addr, value):
        self._ensure_curFileStr()
        try:
            self.rom.writeBytes(addr, "%02x" % (value & 0xFF))
        except Exception:
            pass

    def _reload(self):
        self.loading = True
        try:
            self.breathSpin.setValue(self._read_byte(ADDR_BREATH_CHANCE))
            self.kiwiLvl2.setValue(self._read_byte(ADDR_KIWI_LVL2))
            self.kiwiLvl3.setValue(self._read_byte(ADDR_KIWI_LVL3))
            self.kiwiLvl4.setValue(self._read_byte(ADDR_KIWI_LVL4))

            kiwi_spell = self._read_byte(ADDR_KIWI_SPELL)
            for i in range(self.kiwiSpellCombo.count()):
                if self.kiwiSpellCombo.itemData(i) == kiwi_spell:
                    self.kiwiSpellCombo.setCurrentIndex(i); break

            sorc = self._read_byte(ADDR_SORC_SPELL)
            for i in range(self.sorcCombo.count()):
                if self.sorcCombo.itemData(i) == sorc:
                    self.sorcCombo.setCurrentIndex(i); break

            self.powSpin.setValue(self._read_byte(ADDR_SPELLPOWER))
            self.superSpin.setValue(self._read_byte(ADDR_SUPER_ATTACK))
            self.curseSpin.setValue(self._read_byte(ADDR_CURSE))
            self.stunSpin.setValue(self._read_byte(ADDR_STUN))

            tauros = self._read_byte(ADDR_TAUROS)
            self.taurosCheck.setChecked(tauros == TAUROS_ON)
        finally:
            self.loading = False

    # ---------- signals ----------
    def OnBreathChanged(self, v):
        if self.loading: return
        self._write_byte(ADDR_BREATH_CHANCE, v); self._mark_modified()

    def OnKiwiLvl2Changed(self, v):
        if self.loading: return
        self._write_byte(ADDR_KIWI_LVL2, v); self._mark_modified()

    def OnKiwiLvl3Changed(self, v):
        if self.loading: return
        self._write_byte(ADDR_KIWI_LVL3, v); self._mark_modified()

    def OnKiwiLvl4Changed(self, v):
        if self.loading: return
        self._write_byte(ADDR_KIWI_LVL4, v); self._mark_modified()

    def OnKiwiSpellChanged(self, _idx):
        if self.loading: return
        data = self.kiwiSpellCombo.currentData()
        if data is None: return
        self._write_byte(ADDR_KIWI_SPELL, data); self._mark_modified()

    def OnSorcChanged(self, _idx):
        if self.loading: return
        data = self.sorcCombo.currentData()
        if data is None: return
        self._write_byte(ADDR_SORC_SPELL, data); self._mark_modified()

    def OnPowerChanged(self, v):
        if self.loading: return
        self._write_byte(ADDR_SPELLPOWER, v); self._mark_modified()

    def OnSuperChanged(self, v):
        if self.loading: return
        self._write_byte(ADDR_SUPER_ATTACK, v); self._mark_modified()

    def OnCurseChanged(self, v):
        if self.loading: return
        self._write_byte(ADDR_CURSE, v); self._mark_modified()

    def OnStunChanged(self, v):
        if self.loading: return
        self._write_byte(ADDR_STUN, v); self._mark_modified()

    def OnTaurosChanged(self, checked):
        if self.loading: return
        self._write_byte(ADDR_TAUROS, TAUROS_ON if checked else TAUROS_OFF)
        self._mark_modified()

    # ---------- internal ----------
    def _mark_modified(self):
        self.updateModifiedIndicator(True)
        try: self.parent.modify()
        except Exception: pass

    # ---------- panel hooks ----------
    def OnShow(self, event=None):
        self._reload()

    def getCurrentData(self): return None
    def getCurrentSpriteObject(self): return None