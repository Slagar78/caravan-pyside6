# caravan-pyside6/data/classes.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QComboBox, QLineEdit, QCheckBox,
    QSpinBox, QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

import rompanel


# ---------- ROM-адреса ----------
ADDR_PCLASS_PTR    = 0x1EE00C      # pClassData = LoadPointer(2023436)
ADDR_ITEMNAMES_PTR = 65668         # pItemNames

NUM_CLASSES        = 32
CLASS_NAME_OFFSET  = 128           # class names start after 128 item names


CLASS_NAMES = [
    "SDMN", "KNTE", "WARR", "MAGE", "PRST", "ARCH", "BDMN", "WFMN",
    "RNGR", "PHNK", "THIF", "TORT", "HERO", "PLDN", "PGNT", "GLDT",
    "BRN",  "WIZ",  "SORC", "VICR", "MMNK", "SNIP", "BRGN", "BDBT",
    "WRBR", "BWKT", "PHNX", "NINJ", "MNST", "RBT",  "GLM",  "RDBN",
]

MOVE_TYPES = [
    (16,  "Warrior"),
    (32,  "Horse"),
    (48,  "Stealthy"),
    (64,  "Brass Gunner"),
    (80,  "Fly"),
    (96,  "Float"),
    (112, "Water"),
    (128, "Archer"),
    (144, "Ranger"),
    (160, "Sniper"),
    (176, "Mage"),
    (192, "Priest"),
]

# Bit 3 у критического ниббла = 150% dmg / effects.
# Bit 3 = 0 → 125% damage, варианты только по шансу (индексы 1,3,5,7)
# Bit 3 = 1 → 150% damage, индексы 0,2,4,6 по шансу + 8..15 по эффекту
CRITICAL_OPTIONS = [
    "150% dmg, 1/32",     # 0
    "125% dmg, 1/32",     # 1
    "150% dmg, 1/16",     # 2
    "125% dmg, 1/16",     # 3
    "150% dmg, 1/8",      # 4
    "125% dmg, 1/8",      # 5
    "150% dmg, 1/4",      # 6
    "125% dmg, 1/4",      # 7
    "150% dmg, None",     # 8
    "150% dmg, Poison",   # 9
    "150% dmg, Sleep",    # 10
    "150% dmg, Stun",     # 11
    "150% dmg, Muddle",   # 12
    "150% dmg, Slow",     # 13
    "150% dmg, MP Drain", # 14
    "150% dmg, Silence",  # 15
]

DOUBLE_OPTIONS = [
    (0x00, "1/32"),
    (0x10, "1/16"),
    (0x20, "1/8"),
    (0x30, "1/4"),
]

COUNTER_OPTIONS = [
    (0x00, "1/32"),
    (0x40, "1/16"),
    (0x80, "1/8"),
    (0xC0, "1/4"),
]

RESIST_CHECKS = [
    ("25% Wind",      0x01),
    ("50% Wind",      0x02),
    ("25% Lightning", 0x04),
    ("50% Lightning", 0x08),
    ("25% Ice",       0x10),
    ("50% Ice",       0x20),
    ("25% Fire",      0x40),
    ("50% Fire",      0x80),
]


# ---------- helpers ----------
def read_pointer(rom, ptr_addr):
    """SF2-style 3-byte BE pointer, stored at ptr_addr+1..ptr_addr+3."""
    return int(rom.getBytes(ptr_addr + 1, 3), 16)


class CharacterClass:
    __slots__ = ("addr", "move", "other_res", "elem_res",
                 "move_type", "atk_chances", "modified")

    def __init__(self, addr=0, move=0, other_res=0, elem_res=0,
                 move_type=0, atk_chances=0):
        self.addr = addr
        self.move = move
        self.other_res = other_res
        self.elem_res = elem_res
        self.move_type = move_type
        self.atk_chances = atk_chances
        self.modified = False

    @classmethod
    def from_rom(cls, rom, addr):
        raw = rom.getBytes(addr, 5)
        return cls(
            addr=addr,
            move=int(raw[0:2], 16),
            other_res=int(raw[2:4], 16),
            elem_res=int(raw[4:6], 16),
            move_type=int(raw[6:8], 16),
            atk_chances=int(raw[8:10], 16),
        )

    def to_hex(self):
        return "%02x%02x%02x%02x%02x" % (
            self.move & 0xFF,
            self.other_res & 0xFF,
            self.elem_res & 0xFF,
            self.move_type & 0xFF,
            self.atk_chances & 0xFF,
        )


# =========================================================
# Panel
# =========================================================
class ClassPanel(rompanel.ROMPanel):
    frameTitle = "Class"
    canMaximize = False

    # ---------- init ----------
    def init(self):
        if self.rom is None:
            return

        self.loading = True
        self.cls = None
        self.curClassIdx = 0

        # кэш
        if "classes" not in self.rom.data or not self.rom.data["classes"]:
            self.rom.data["classes"] = self._load_all_classes()
        self.classes = self.rom.data["classes"]

        # ---------- Select ----------
        sbs_select = QGroupBox("Select")
        sel = QHBoxLayout(sbs_select)
        sel.setContentsMargins(8, 8, 8, 8)
        sel.setSpacing(8)

        self.classList = QComboBox()
        self.classList.setMinimumWidth(220)
        self.classList.addItems(CLASS_NAMES)
        self.classList.currentIndexChanged.connect(self.OnSelectClass)
        sel.addWidget(self.classList)

        self.renameButton = QPushButton("Rename")
        self.renameButton.setFixedWidth(90)
        self.renameButton.clicked.connect(self.OnRename)
        sel.addWidget(self.renameButton)
        sel.addStretch()

        # ---------- Class info ----------
        sbs_info = QGroupBox()
        info = QGridLayout(sbs_info)
        info.setContentsMargins(14, 14, 14, 14)
        info.setHorizontalSpacing(10)
        info.setVerticalSpacing(10)

        lbl_name = QLabel("Name")
        lbl_name.setFont(self._labelFont())
        self.nameEdit = QLineEdit()
        self.nameEdit.setReadOnly(True)
        self.nameEdit.setMinimumWidth(160)

        lbl_mt = QLabel("Move Type")
        lbl_mt.setFont(self._labelFont())
        self.moveTypeCombo = QComboBox()
        self.moveTypeCombo.setMinimumWidth(160)
        for code, name in MOVE_TYPES:
            self.moveTypeCombo.addItem(name, code)
        self.moveTypeCombo.currentIndexChanged.connect(self.OnMoveTypeChanged)

        lbl_move = QLabel("Move")
        lbl_move.setFont(self._labelFont())
        self.moveSpin = QSpinBox()
        self.moveSpin.setRange(0, 255)
        self.moveSpin.setMaximumWidth(70)
        self.moveSpin.valueChanged.connect(self.OnMoveChanged)

        lbl_other = QLabel("Other Resistance")
        lbl_other.setFont(self._labelFont())
        self.otherResSpin = QSpinBox()
        self.otherResSpin.setRange(0, 255)
        self.otherResSpin.setMaximumWidth(70)
        self.otherResSpin.valueChanged.connect(self.OnOtherResChanged)

        info.addWidget(lbl_name, 0, 0)
        info.addWidget(self.nameEdit, 0, 1, 1, 3)
        info.addWidget(lbl_mt, 1, 0)
        info.addWidget(self.moveTypeCombo, 1, 1)
        info.addWidget(lbl_move, 1, 2)
        info.addWidget(self.moveSpin, 1, 3)
        info.addWidget(lbl_other, 2, 0)
        info.addWidget(self.otherResSpin, 2, 1)
        info.setColumnStretch(1, 1)
        info.setColumnStretch(3, 1)

        # ---------- Resistance ----------
        sbs_res = QGroupBox("Resistance - select both for weakness")
        res = QGridLayout(sbs_res)
        res.setContentsMargins(14, 14, 14, 14)
        res.setHorizontalSpacing(12)
        res.setVerticalSpacing(8)

        self.resChecks = []
        for i, (label, bit) in enumerate(RESIST_CHECKS):
            cb = QCheckBox(label)
            cb.toggled.connect(self.OnResChanged)
            self.resChecks.append((bit, cb))
            res.addWidget(cb, i // 2, i % 2)

        # ---------- Critical ----------
        sbs_crit = QGroupBox("Critical Attack Chance")
        crit = QHBoxLayout(sbs_crit)
        crit.setContentsMargins(14, 14, 14, 14)
        crit.setSpacing(10)
        crit.addWidget(QLabel("Type / chance:"))
        self.critCombo = QComboBox()
        self.critCombo.setMinimumWidth(200)
        self.critCombo.addItems(CRITICAL_OPTIONS)
        self.critCombo.currentIndexChanged.connect(self.OnCriticalChanged)
        crit.addWidget(self.critCombo)
        crit.addStretch()

        # ---------- Double / Counter ----------
        sbs_dc = QGroupBox("Double / Counter Attack Chance")
        dc = QGridLayout(sbs_dc)
        dc.setContentsMargins(14, 14, 14, 14)
        dc.setHorizontalSpacing(10)
        dc.setVerticalSpacing(8)

        dc.addWidget(QLabel("Double:"), 0, 0)
        self.doubleCombo = QComboBox()
        for code, name in DOUBLE_OPTIONS:
            self.doubleCombo.addItem(name, code)
        self.doubleCombo.currentIndexChanged.connect(self.OnDoubleChanged)
        dc.addWidget(self.doubleCombo, 0, 1)

        dc.addWidget(QLabel("Counter:"), 1, 0)
        self.counterCombo = QComboBox()
        for code, name in COUNTER_OPTIONS:
            self.counterCombo.addItem(name, code)
        self.counterCombo.currentIndexChanged.connect(self.OnCounterChanged)
        dc.addWidget(self.counterCombo, 1, 1)
        dc.setColumnStretch(1, 1)

        # ---------- Layout ----------
        self.sizer.addWidget(sbs_select, 0, 0, 1, 2)
        self.sizer.addWidget(sbs_info, 1, 0)
        self.sizer.addWidget(sbs_res, 1, 1)
        self.sizer.addWidget(sbs_crit, 2, 0)
        self.sizer.addWidget(sbs_dc, 2, 1)
        self.sizer.setColumnStretch(0, 1)
        self.sizer.setColumnStretch(1, 1)

        self.loading = False
        self.changeClass(0)

    # ---------- helpers ----------
    def _labelFont(self):
        f = QFont("MS Sans Serif", 9)
        f.setBold(False)
        return f

    def _load_all_classes(self):
        result = []
        try:
            pCls = read_pointer(self.rom, ADDR_PCLASS_PTR)
            for i in range(NUM_CLASSES):
                result.append(CharacterClass.from_rom(self.rom, pCls + i * 5))
        except Exception:
            for _ in range(NUM_CLASSES):
                result.append(CharacterClass(addr=0))
        return result

    def _ensure_curFileStr(self):
        if not hasattr(self.rom, "curFileStr"):
            try:
                self.rom.startWriteProcess()
            except Exception:
                pass

    def _flushClass(self, c):
        if not c or not c.addr:
            return
        try:
            self._ensure_curFileStr()
            self.rom.writeBytes(c.addr, c.to_hex())
        except Exception:
            pass

    # ---------- class name (ROM bank, pItemNames @ 128+) ----------
    def _name_addr(self, class_idx):
        addr = read_pointer(self.rom, ADDR_ITEMNAMES_PTR)
        # пропускаем 128 имён предметов + padding-байт 0xFF после 127-го
        for i in range(128):
            length = int(self.rom.getBytes(addr, 1), 16)
            addr += 1 + length
            if i == 127:
                addr += 1
        # пропускаем class_idx имён классов
        for _ in range(class_idx):
            length = int(self.rom.getBytes(addr, 1), 16)
            addr += 1 + length
        return addr

    def _set_class_name(self, class_idx, new_name):
        addr = self._name_addr(class_idx)
        old_len = int(self.rom.getBytes(addr, 1), 16)
        if len(new_name) != old_len:
            raise ValueError(f"Длина должна остаться {old_len}")
        self._ensure_curFileStr()
        self.rom.writeBytes(addr + 1, new_name.encode("ascii").hex())

    # ---------- class data ----------
    def changeClass(self, num=None):
        if num is not None:
            self.curClassIdx = num

        if not (0 <= self.curClassIdx < len(self.classes)):
            self.cls = None
            return

        self.cls = self.classes[self.curClassIdx]

        self.loading = True
        try:
            self.nameEdit.setText(CLASS_NAMES[self.curClassIdx])

            # Move Type
            mt_idx = 0
            for i in range(self.moveTypeCombo.count()):
                if self.moveTypeCombo.itemData(i) == self.cls.move_type:
                    mt_idx = i
                    break
            self.moveTypeCombo.setCurrentIndex(mt_idx)

            self.moveSpin.setValue(self.cls.move)
            self.otherResSpin.setValue(self.cls.other_res)

            # Resist
            er = self.cls.elem_res
            for bit, cb in self.resChecks:
                cb.setChecked(bool(er & bit))

            # Critical
            crit_idx = self.cls.atk_chances & 0x0F
            if 0 <= crit_idx < self.critCombo.count():
                self.critCombo.setCurrentIndex(crit_idx)

            # Double
            dbl = self.cls.atk_chances & 0x30
            for i in range(self.doubleCombo.count()):
                if self.doubleCombo.itemData(i) == dbl:
                    self.doubleCombo.setCurrentIndex(i)
                    break

            # Counter
            ctr = self.cls.atk_chances & 0xC0
            for i in range(self.counterCombo.count()):
                if self.counterCombo.itemData(i) == ctr:
                    self.counterCombo.setCurrentIndex(i)
                    break
        finally:
            self.loading = False

        self.updateModifiedIndicator(getattr(self.cls, "modified", False))

    # ---------- signals ----------
    def OnSelectClass(self, idx):
        if self.loading:
            return
        self.changeClass(idx)

    def OnMoveTypeChanged(self, idx):
        if self.loading or self.cls is None or idx < 0:
            return
        self.cls.move_type = self.moveTypeCombo.itemData(idx)
        self.cls.modified = True
        self._flushClass(self.cls)
        self._mark_modified()

    def OnMoveChanged(self, val):
        if self.loading or self.cls is None:
            return
        self.cls.move = val
        self.cls.modified = True
        self._flushClass(self.cls)
        self._mark_modified()

    def OnOtherResChanged(self, val):
        if self.loading or self.cls is None:
            return
        self.cls.other_res = val
        self.cls.modified = True
        self._flushClass(self.cls)
        self._mark_modified()

    def OnResChanged(self, _checked):
        if self.loading or self.cls is None:
            return
        val = 0
        for bit, cb in self.resChecks:
            if cb.isChecked():
                val |= bit
        self.cls.elem_res = val
        self.cls.modified = True
        self._flushClass(self.cls)
        self._mark_modified()

    def OnCriticalChanged(self, _idx):
        if self.loading or self.cls is None:
            return
        self._rebuild_atk_chances()

    def OnDoubleChanged(self, _idx):
        if self.loading or self.cls is None:
            return
        self._rebuild_atk_chances()

    def OnCounterChanged(self, _idx):
        if self.loading or self.cls is None:
            return
        self._rebuild_atk_chances()

    def _rebuild_atk_chances(self):
        val = 0
        val |= (self.critCombo.currentIndex() & 0x0F)
        dbl = self.doubleCombo.currentData()
        ctr = self.counterCombo.currentData()
        if dbl is not None:
            val |= (dbl & 0x30)
        if ctr is not None:
            val |= (ctr & 0xC0)
        self.cls.atk_chances = val
        self.cls.modified = True
        self._flushClass(self.cls)
        self._mark_modified()

    # ---------- rename ----------
    def OnRename(self):
        if self.cls is None:
            return
        idx = self.curClassIdx
        old_name = CLASS_NAMES[idx]
        max_len = len(old_name)

        new_name, ok = QInputDialog.getText(
            self, "Rename",
            f"Новое имя для класса {old_name} (не длиннее {max_len} символов):",
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

        padded = new_name.ljust(max_len)

        try:
            self._set_class_name(idx, padded)
        except Exception as e:
            QMessageBox.critical(self, "Rename",
                                 f"Не удалось записать имя:\n{e}")
            return

        CLASS_NAMES[idx] = new_name
        self.classList.setItemText(idx, new_name)
        self.nameEdit.setText(new_name)
        self.cls.modified = True
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
        if self.cls is not None:
            self.changeClass(self.curClassIdx)

    def getCurrentData(self):
        return getattr(self, "cls", None)

    def getCurrentSpriteObject(self):
        return getattr(self, "cls", None)

    changeSelection = changeClass