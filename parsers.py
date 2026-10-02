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
#  Flag info (порт MapFlagCopyEvent.getFlagInfo)
# ============================================================

def get_flag_info(flag: int) -> str:
    if flag < 32:
        return f"Party member {flag} is in the force."
    elif flag < 64:
        return f"Party member {flag - 32} is in the battle party."
    elif flag < 90:
        return f"Map follower {flag - 64} is present."
    elif flag < 128:
        return f"Temp battle flag {flag} is set."
    elif flag < 256:
        return f"Item flag {flag - 128} is acquired (found in chest or other)."
    elif flag < 280:
        return f"Temp map setup flag {flag} is set."
    elif flag < 400:
        return "???"
    elif flag < 450:
        return f"Battle {flag - 400} is unlocked."
    elif flag < 500:
        return f"Battle {flag - 450} intro has been seen."
    elif flag < 550:
        return f"Battle {flag - 500} has been completed."
    elif flag < 1000:
        return f"Game progress flag {flag - 550} is set."
    else:
        return "???"


# ============================================================
#  Хелперы
# ============================================================

def trim_and_remove_comments(line: str) -> str:
    if ";" in line:
        line = line[:line.index(";")]
    return line.strip()


def extract_comment(line: str) -> str | None:
    if ";" in line:
        c = line[line.index(";") + 1:].strip()
        return c if c else None
    return None


def get_value_int(s: str) -> int:
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
#  Парсеры
# ============================================================

def parse_areas_asm(path) -> list[MapArea]:
    """Порт MapAreaAsmProcessor для 2-areas.asm."""
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


def parse_warps_asm(path) -> list[MapWarpEvent]:
    """Порт MapWarpEventsAsmProcessor для 6-warp-events.asm."""
    path = Path(path)
    if not path.exists():
        return []

    warps: list[MapWarpEvent] = []
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        raw = lines[i]
        line = trim_and_remove_comments(raw)
        i += 1

        if not line.startswith("mWarp"):
            continue

        comment = extract_comment(raw)
        v = parse_ints_after_identifier(line)
        if len(v) < 2:
            continue
        triggerX, triggerY = v[0], v[1]

        # Следующая строка: warpNoScroll или warpScroll DIR
        if i >= len(lines):
            break
        next_line = trim_and_remove_comments(lines[i])
        i += 1

        warp_type = "warpNoScroll"
        scroll_dir = "DOWN"
        parts = next_line.split()
        if parts:
            if parts[0] == "warpNoScroll":
                warp_type = "warpNoScroll"
                scroll_dir = "DOWN"
            elif parts[0] == "warpScroll" and len(parts) >= 2:
                warp_type = "warpScroll"
                scroll_dir = parts[1]

        # warpMap
        destMap = "NONE"
        if i < len(lines):
            wm_line = trim_and_remove_comments(lines[i])
            i += 1
            if wm_line.startswith("warpMap"):
                mp = wm_line.split()[-1]
                destMap = mp.replace("MAP_", "")

        # warpDest
        destX, destY = 0, 0
        if i < len(lines):
            wd_line = trim_and_remove_comments(lines[i])
            i += 1
            if wd_line.startswith("warpDest"):
                v = parse_ints_after_identifier(wd_line)
                if len(v) >= 2:
                    destX, destY = v[0], v[1]

        # warpFacing
        facing = "DOWN"
        if i < len(lines):
            wf_line = trim_and_remove_comments(lines[i])
            i += 1
            if wf_line.startswith("warpFacing"):
                parts = wf_line.split()
                if len(parts) >= 2:
                    facing = parts[1]

        warps.append(MapWarpEvent(
            triggerX=triggerX, triggerY=triggerY,
            warpType=warp_type, scrollDirection=scroll_dir,
            destMap=destMap, destX=destX, destY=destY,
            facing=facing, comment=comment
        ))

    return warps


def parse_items_asm(path) -> list[MapItem]:
    """Порт MapItemAsmProcessor для 7-chest-items.asm / 8-other-items.asm."""
    path = Path(path)
    if not path.exists():
        return []

    items: list[MapItem] = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = trim_and_remove_comments(raw)
            if not line.startswith("mapItem"):
                continue
            comment = extract_comment(raw)
            # mapItem X, Y, flag, ITEM_NAME
            after = line.split(" ", 1)[1]
            parts = [p.strip() for p in after.split(",")]
            if len(parts) < 4:
                continue
            try:
                x = get_value_int(parts[0])
                y = get_value_int(parts[1])
                flag = get_value_int(parts[2])
                item_name = parts[3]
            except Exception:
                continue
            items.append(MapItem(x=x, y=y, flag=flag, item=item_name, comment=comment))
    return items


def _parse_copy_events(path, identifier: str, source_id: str,
                       size_id: str, dest_id: str,
                       is_roof: bool = False) -> list[MapCopyEvent]:
    """Общий парсер для flag/step/roof copies."""
    path = Path(path)
    if not path.exists():
        return []

    events: list[MapCopyEvent] = []
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        raw = lines[i]
        line = trim_and_remove_comments(raw)
        i += 1

        if not line.startswith(identifier):
            continue

        comment = extract_comment(raw)
        v = parse_ints_after_identifier(line)
        if is_roof:
            if len(v) < 2:
                continue
            triggerX, triggerY = v[0], v[1]
            flag = None
        else:
            if len(v) < 2:
                continue
            if identifier == "fbcFlag":
                # fbcFlag N — одиночное число
                flag = v[0] if v else 0
                triggerX = flag
                triggerY = flag
            else:
                triggerX, triggerY = v[0], v[1]
                flag = None

        # Ищем остальные 3 строки: Source, Size, Dest
        sourceX, sourceY = 0, 0
        width, height = 0, 0
        destX, destY = 0, 0

        # Source
        if i < len(lines):
            sl = trim_and_remove_comments(lines[i])
            i += 1
            if sl.startswith(source_id):
                v2 = parse_ints_after_identifier(sl)
                if len(v2) >= 2:
                    sourceX, sourceY = v2[0], v2[1]

        # Size
        if i < len(lines):
            zl = trim_and_remove_comments(lines[i])
            i += 1
            if zl.startswith(size_id):
                v2 = parse_ints_after_identifier(zl)
                if len(v2) >= 2:
                    width, height = v2[0], v2[1]

        # Dest
        if i < len(lines):
            dl = trim_and_remove_comments(lines[i])
            i += 1
            if dl.startswith(dest_id):
                v2 = parse_ints_after_identifier(dl)
                if len(v2) >= 2:
                    destX, destY = v2[0], v2[1]

        # Формируем source end coordinates
        if is_roof and sourceX == 0xFF and sourceY == 0xFF:
            src_end_x = width
            src_end_y = height
        else:
            src_end_x = sourceX + width - 1
            src_end_y = sourceY + height - 1

        events.append(MapCopyEvent(
            triggerX=triggerX, triggerY=triggerY,
            sourceStartX=sourceX, sourceStartY=sourceY,
            sourceEndX=src_end_x, sourceEndY=src_end_y,
            destStartX=destX, destStartY=destY,
            comment=comment
        ))

    return events


def parse_flag_events_asm(path) -> list[MapCopyEvent]:
    """Порт MapFlagEventsAsmProcessor для 3-flag-events.asm."""
    return _parse_copy_events(
        path, "fbcFlag", "fbcSource", "fbcSize", "fbcDest",
        is_roof=False
    )


def parse_step_events_asm(path) -> list[MapCopyEvent]:
    """Порт MapStepEventsAsmProcessor для 4-step-events.asm."""
    return _parse_copy_events(
        path, "sbc", "sbcSource", "sbcSize", "sbcDest",
        is_roof=False
    )


def parse_roof_events_asm(path) -> list[MapCopyEvent]:
    """Порт MapRoofEventsAsmProcessor для 5-roof-events.asm."""
    return _parse_copy_events(
        path, "slbc", "slbcSource", "slbcSize", "slbcDest",
        is_roof=True
    )


def parse_animations_asm(path) -> MapAnimSet:
    """Парсит 9-animations.asm."""
    path = Path(path)
    result = MapAnimSet()
    if not path.exists():
        return result

    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = trim_and_remove_comments(raw)
            if not line:
                continue
            if line.startswith("mAnimTileset"):
                v = parse_ints_after_identifier(line)
                if v:
                    result.tilesetIdx = v[0]
            elif line.startswith("mAnimFrame"):
                v = parse_ints_after_identifier(line)
                if len(v) >= 4:
                    start, length, dest, delay = v[0], v[1], v[2], v[3]
                    result.anims.append(MapAnim(
                        start=start, end=start + length,
                        dest=dest, delay=delay
                    ))
    return result