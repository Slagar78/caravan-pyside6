"""Парсеры ASM-файлов формата SF2DISASM в Python-модель (read-only).

Порт Java-классов com.sfc.sf2.map.io.*AsmProcessor.
Модели — dataclass'ы, повторяющие com.sfc.sf2.map.*.
"""
from dataclasses import dataclass, field
from pathlib import Path
import re


# ============================================================
#  Модели (порт Java-классов)
# ============================================================

@dataclass
class MapArea:
    """Порт com.sfc.sf2.map.MapArea."""
    layer1StartX: int = 0
    layer1StartY: int = 0
    layer1EndX: int = 0
    layer1EndY: int = 0
    foregroundLayer2StartX: int = 0
    foregroundLayer2StartY: int = 0
    backgroundLayer2StartX: int = 0
    backgroundLayer2StartY: int = 0
    layer1ParallaxX: int = 0
    layer1ParallaxY: int = 0
    layer2ParallaxX: int = 0
    layer2ParallaxY: int = 0
    layer1AutoscrollX: int = 0
    layer1AutoscrollY: int = 0
    layer2AutoscrollX: int = 0
    layer2AutoscrollY: int = 0
    layerType: int = 0
    defaultMusic: str = "NONE"


@dataclass
class MapWarpEvent:
    """Порт com.sfc.sf2.map.MapWarpEvent."""
    triggerX: int = 0
    triggerY: int = 0
    warpType: str = "warpNoScroll"
    scrollDirection: str = "RIGHT"
    destMap: str = "NONE"
    destX: int = 0
    destY: int = 0
    facing: str = "DOWN"
    comment: str | None = None


@dataclass
class MapItem:
    """Порт com.sfc.sf2.map.MapItem."""
    x: int = 0
    y: int = 0
    flag: int = 0
    item: str = "NOTHING"
    comment: str | None = None


@dataclass
class MapCopyEvent:
    """Порт com.sfc.sf2.map.MapCopyEvent."""
    triggerX: int = 0
    triggerY: int = 0
    sourceStartX: int = 0
    sourceStartY: int = 0
    sourceEndX: int = 0
    sourceEndY: int = 0
    destStartX: int = 0
    destStartY: int = 0
    comment: str | None = None

    def get_width(self) -> int:
        if self.sourceStartX == 0xFF:
            return self.sourceEndX
        return self.sourceEndX - self.sourceStartX + 1

    def get_height(self) -> int:
        if self.sourceStartY == 0xFF:
            return self.sourceEndY
        return self.sourceEndY - self.sourceStartY + 1


@dataclass
class MapAnim:
    """Порт com.sfc.sf2.map.animation.MapAnimationFrame (упрощённый)."""
    start: int = 0
    end: int = 0
    dest: int = 0
    delay: int = 0


@dataclass
class MapAnimSet:
    """Набор анимаций карты (9-animations.asm)."""
    tilesetIdx: int | None = None
    anims: list[MapAnim] = field(default_factory=list)


# ============================================================
#  Хелперы (порт com.sfc.sf2.helpers)
# ============================================================

def trim_and_remove_comments(line: str) -> str:
    """Убирает комментарий (`;...`) и пробелы по краям."""
    if ";" in line:
        line = line[:line.index(";")]
    return line.strip()


def extract_comment(line: str) -> str | None:
    """Возвращает текст после `;` или None."""
    if ";" in line:
        c = line[line.index(";") + 1:].strip()
        return c if c else None
    return None


def get_value_int(s: str) -> int:
    """Парсит int из строки. Понимает `0x..` и десятичное."""
    s = s.strip().rstrip(",").strip()
    if not s:
        return 0
    if s.lower().startswith("0x"):
        return int(s, 16)
    try:
        return int(s)
    except ValueError:
        return 0


def parse_ints_after_identifier(line: str) -> list[int]:
    """Вытаскивает все целые из строки после первого слова.

    Пример: 'mainLayerStart  5, 7' → [5, 7]
    """
    parts = line.split()
    values = []
    for p in parts[1:]:
        p = p.strip().rstrip(",").strip()
        if not p:
            continue
        if p.lstrip("-").isdigit() or p.lower().startswith("0x"):
            values.append(get_value_int(p))
    return values


# ============================================================
#  Парсеры — по одному на файл
# ============================================================

def parse_areas_asm(path) -> list[MapArea]:
    """Порт MapAreaAsmProcessor.parseAsmData для 2-areas.asm."""
    path = Path(path)
    if not path.exists():
        return []

    areas: list[MapArea] = []
    current: MapArea | None = None

    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = trim_and_remove_comments(raw)
            if not line:
                continue

            if line.startswith("mainLayerStart"):
                # Сохраняем предыдущую область ПЕРЕД созданием новой
                if current is not None:
                    areas.append(current)
                current = MapArea()
                v = parse_ints_after_identifier(line)
                if len(v) >= 2:
                    current.layer1StartX, current.layer1StartY = v[0], v[1]

            elif line.startswith("mainLayerEnd") and current:
                v = parse_ints_after_identifier(line)
                if len(v) >= 2:
                    current.layer1EndX, current.layer1EndY = v[0], v[1]

            elif line.startswith("scndLayerFgndStart") and current:
                v = parse_ints_after_identifier(line)
                if len(v) >= 2:
                    current.foregroundLayer2StartX, current.foregroundLayer2StartY = v[0], v[1]

            elif line.startswith("scndLayerBgndStart") and current:
                v = parse_ints_after_identifier(line)
                if len(v) >= 2:
                    current.backgroundLayer2StartX, current.backgroundLayer2StartY = v[0], v[1]

            elif line.startswith("mainLayerParallax") and current:
                v = parse_ints_after_identifier(line)
                if len(v) >= 2:
                    current.layer1ParallaxX, current.layer1ParallaxY = v[0], v[1]

            elif line.startswith("scndLayerParallax") and current:
                v = parse_ints_after_identifier(line)
                if len(v) >= 2:
                    current.layer2ParallaxX, current.layer2ParallaxY = v[0], v[1]

            elif line.startswith("mainLayerAutoscroll") and current:
                v = parse_ints_after_identifier(line)
                if len(v) >= 2:
                    current.layer1AutoscrollX, current.layer1AutoscrollY = v[0], v[1]

            elif line.startswith("scndLayerAutoscroll") and current:
                v = parse_ints_after_identifier(line)
                if len(v) >= 2:
                    current.layer2AutoscrollX, current.layer2AutoscrollY = v[0], v[1]

            elif line.startswith("mainLayerType") and current:
                v = parse_ints_after_identifier(line)
                if v:
                    current.layerType = v[0]

            elif line.startswith("areaDefaultMusic") and current:
                parts = line.split()
                if len(parts) >= 2:
                    music = parts[1]
                    if music.startswith("MUSIC_"):
                        music = music[6:]
                    current.defaultMusic = music

            elif line.startswith("endWord"):
                if current:
                    areas.append(current)
                    current = None

    # На случай, если файл без endWord — не потерять последнюю
    if current is not None:
        areas.append(current)

    return areas


def parse_tilesets_asm(path) -> tuple[int, list[int]]:
    """Парсит 00-tilesets.asm → (paletteIdx, [tilesetIdxes])."""
    path = Path(path)
    if not path.exists():
        return 0, []

    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = trim_and_remove_comments(raw)
            if line.startswith("tilesets:"):
                after = line.split(":", 1)[1].strip()
                nums_str = re.sub(r"^dc\.[bwl]\s*", "", after)
                nums = [get_value_int(x) for x in nums_str.split(",")]
                if not nums:
                    return 0, []
                return nums[0], nums[1:]
    return 0, []