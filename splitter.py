"""Раскладывает карты из ROM в ASM-файлы формата SF2DISASM.

Работает с объектом rom.ROM (Python-Caravan).
Читает .bin секции прямо из ROM-файла по адресам из py_map.sectionAddrs.
Генерирует .asm файлы из уже распарсенных py_map.areas / warps / items / copies / anims.
"""
import os
from pathlib import Path


# ============================================================
#  Основные функции
# ============================================================

def split_all_maps(rom, output_dir, progress_callback=None):
    """Раскладывает все 79 карт в output_dir/mapXX/.

    progress_callback(current, total, map_id) — вызывается перед каждой картой.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    total = len(rom.data["maps"])

    for map_id in range(total):
        if progress_callback:
            progress_callback(map_id + 1, total, map_id)

        # Загружаем карту, если ещё не загружена
        py_map = rom.data["maps"][map_id]
        if not getattr(py_map, "loaded", False):
            rom.getMaps(map_id, map_id)
            py_map = rom.data["maps"][map_id]

        split_one_map(rom, py_map, map_id, output_dir)

    # Генерируем entries.asm (общий файл)
    _write_entries_asm(output_dir, total)


def split_one_map(rom, py_map, map_id, output_dir):
    """Раскладывает одну карту в output_dir/mapXX/."""
    map_dir = Path(output_dir) / f"map{map_id:02d}"
    map_dir.mkdir(parents=True, exist_ok=True)

    _write_tilesets(py_map, map_id, map_dir)
    _write_bin_sections(rom, py_map, map_dir)
    _write_areas(py_map, map_id, map_dir)
    _write_flag_events(py_map, map_id, map_dir)
    _write_step_events(py_map, map_id, map_dir)
    _write_roof_events(py_map, map_id, map_dir)
    _write_warps(py_map, map_id, map_dir)
    _write_chest_items(py_map, map_id, map_dir)
    _write_other_items(py_map, map_id, map_dir)
    _write_animations(py_map, map_id, map_dir)


# ============================================================
#  .bin секции — читаем сырые байты из ROM
# ============================================================

def _read_bin_section(rom, start_addr, end_addr):
    """Читает байты из ROM-файла между двумя адресами."""
    if start_addr is None or end_addr is None:
        return b""
    if end_addr <= start_addr:
        return b""
    rom.file.seek(start_addr)
    return rom.file.read(end_addr - start_addr)


def _write_bin_sections(rom, py_map, map_dir):
    """Пишет 0-blocks.bin и 1-layout.bin — точные копии из ROM."""
    addrs = py_map.sectionAddrs

    # 0-blocks.bin
    if addrs[0] is not None and addrs[1] is not None:
        data = _read_bin_section(rom, addrs[0], addrs[1])
        if data:
            with open(map_dir / "0-blocks.bin", "wb") as f:
                f.write(data)

    # 1-layout.bin
    if addrs[1] is not None and addrs[2] is not None:
        data = _read_bin_section(rom, addrs[1], addrs[2])
        if data:
            with open(map_dir / "1-layout.bin", "wb") as f:
                f.write(data)


# ============================================================
#  .asm генераторы
# ============================================================

def _write_tilesets(py_map, map_id, map_dir):
    """00-tilesets.asm"""
    path = map_dir / "00-tilesets.asm"
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"; ASM FILE data\\maps\\entries\\map{map_id:02d}\\00-tilesets.asm :\n")
        f.write(f"; Map {map_id:02d} palette and tilesets\n\n")
        idxes = ", ".join(str(t) for t in py_map.tilesetIdxes)
        f.write(f"tilesets:   dc.b {py_map.paletteIdx}, {idxes}\n")
        f.write("            even\n")


def _write_areas(py_map, map_id, map_dir):
    """2-areas.asm"""
    path = map_dir / "2-areas.asm"
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"; ASM FILE data\\maps\\entries\\map{map_id:02d}\\2-areas.asm :\n")
        f.write(f"; Map {map_id:02d} areas\n\n")
        for area in py_map.areas:
            f.write(f"\t\t\t\tmainLayerStart      {area.l1x1:3d}, {area.l1y1:3d}\n")
            f.write(f"\t\t\t\tmainLayerEnd        {area.l1x2:3d}, {area.l1y2:3d}\n")
            f.write(f"\t\t\t\tscndLayerFgndStart  {area.l2x:3d}, {area.l2y:3d}\n")
            f.write(f"\t\t\t\tscndLayerBgndStart  {0:3d}, {0:3d}\n")
            f.write(f"\t\t\t\tmainLayerParallax   {area.l1xp:3d}, {area.l1yp:3d}\n")
            f.write(f"\t\t\t\tscndLayerParallax   {area.l2xp:3d}, {area.l2yp:3d}\n")
            f.write(f"\t\t\t\tmainLayerAutoscroll {area.l1xs:3d}, {area.l1ys:3d}\n")
            f.write(f"\t\t\t\tscndLayerAutoscroll {area.l2xs:3d}, {area.l2ys:3d}\n")
            f.write(f"\t\t\t\tmainLayerType       {area.layerType:3d}\n")
            f.write(f"\t\t\t\tareaDefaultMusic    MUSIC_{_music_name(area.music)}\n\n")
        f.write("\t\t\t\tendWord\n")


def _write_flag_events(py_map, map_id, map_dir):
    """3-flag-events.asm — copies[copyType==0]"""
    path = map_dir / "3-flag-events.asm"
    flag_copies = [c for c in py_map.copies if c.copyType == 0]
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"; ASM FILE data\\maps\\entries\\map{map_id:02d}\\3-flag-events.asm :\n\n")
        for c in flag_copies:
            f.write(f"\t\t\t\tfbcFlag {c.flag:3d}\n")
            f.write(f"\t\t\t\t\tfbcSource {c.srcx:2d}, {c.srcy:2d}\n")
            f.write(f"\t\t\t\t\tfbcSize   {c.width:2d}, {c.height:2d}\n")
            f.write(f"\t\t\t\t\tfbcDest   {c.destx:2d}, {c.desty:2d}\n")
        f.write("\t\t\t\tendWord\n")


def _write_step_events(py_map, map_id, map_dir):
    """4-step-events.asm — copies[copyType==1]"""
    path = map_dir / "4-step-events.asm"
    step_copies = [c for c in py_map.copies if c.copyType == 1]
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"; ASM FILE data\\maps\\entries\\map{map_id:02d}\\4-step-events.asm :\n\n")
        for c in step_copies:
            f.write(f"\t\t\t\tsbc {c.x:2d}, {c.y:2d}\n")
            f.write(f"\t\t\t\t\tsbcSource {c.srcx:2d}, {c.srcy:2d}\n")
            f.write(f"\t\t\t\t\tsbcSize   {c.width:2d}, {c.height:2d}\n")
            f.write(f"\t\t\t\t\tsbcDest   {c.destx:2d}, {c.desty:2d}\n")
        f.write("\t\t\t\tendWord\n")


def _write_roof_events(py_map, map_id, map_dir):
    """5-roof-events.asm — copies[copyType==2]"""
    path = map_dir / "5-roof-events.asm"
    roof_copies = [c for c in py_map.copies if c.copyType == 2]
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"; ASM FILE data\\maps\\entries\\map{map_id:02d}\\5-roof-events.asm :\n\n")
        for c in roof_copies:
            f.write(f"\t\t\t\tslbc {c.x:2d}, {c.y:2d}\n")
            f.write(f"\t\t\t\t\tslbcSource {c.srcx:3d}, {c.srcy:3d}\n")
            f.write(f"\t\t\t\t\tslbcSize   {c.width:3d}, {c.height:3d}\n")
            f.write(f"\t\t\t\t\tslbcDest   {c.destx:3d}, {c.desty:3d}\n")
        f.write("\t\t\t\tendWord\n")


def _write_warps(py_map, map_id, map_dir):
    """6-warp-events.asm"""
    path = map_dir / "6-warp-events.asm"
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"; ASM FILE data\\maps\\entries\\map{map_id:02d}\\6-warp-events.asm :\n\n")
        for w in py_map.warps:
            f.write(f"\t\t\t\tmWarp {w.x:3d}, {w.y:3d}\n")
            if w.mystery == 0 or w.mystery == 1:
                f.write("\t\t\t\t\twarpNoScroll\n")
            else:
                f.write("\t\t\t\t\twarpScroll RIGHT\n")
            f.write(f"\t\t\t\t\twarpMap    MAP_{w.destmap:02d}\n")
            f.write(f"\t\t\t\t\twarpDest   {w.destx:2d}, {w.desty:2d}\n")
            f.write(f"\t\t\t\t\twarpFacing {_facing_name(w.destfacing)}\n")
        f.write("\t\t\t\tendWord\n")


def _write_chest_items(py_map, map_id, map_dir):
    """7-chest-items.asm"""
    path = map_dir / "7-chest-items.asm"
    chests = [i for i in py_map.items if i.isChest]
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"; ASM FILE data\\maps\\entries\\map{map_id:02d}\\7-chest-items.asm :\n\n")
        for i in chests:
            f.write(f"\t\t\t\tmapItem {i.x:2d}, {i.y:2d}, {i.flag:3d}, {_item_name(i.itemIdx)}\n")
        f.write("\t\t\t\tendWord\n")


def _write_other_items(py_map, map_id, map_dir):
    """8-other-items.asm"""
    path = map_dir / "8-other-items.asm"
    others = [i for i in py_map.items if not i.isChest]
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"; ASM FILE data\\maps\\entries\\map{map_id:02d}\\8-other-items.asm :\n\n")
        for i in others:
            f.write(f"\t\t\t\tmapItem {i.x:2d}, {i.y:2d}, {i.flag:3d}, {_item_name(i.itemIdx)}\n")
        f.write("\t\t\t\tendWord\n")


def _write_animations(py_map, map_id, map_dir):
    """9-animations.asm"""
    path = map_dir / "9-animations.asm"
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"; ASM FILE data\\maps\\entries\\map{map_id:02d}\\9-animations.asm :\n\n")
        if not py_map.anims:
            f.write("\t\t\t\tendWord\n")
            return
        ts_idx = py_map.animTSIdx if py_map.animTSIdx is not None else 0
        f.write(f"\t\t\t\tmAnimTileset {ts_idx:3d}\n")
        for a in py_map.anims:
            f.write(f"\t\t\t\tmAnimFrame {a.start:3d}, {a.end - a.start:3d}, "
                    f"{a.dest:3d}, {a.delay:3d}\n")
        f.write("\t\t\t\tendWord\n")


def _write_entries_asm(output_dir, total_maps):
    """entries.asm — общая таблица указателей."""
    path = Path(output_dir) / "entries.asm"
    with open(path, "w", encoding="utf-8") as f:
        f.write("; ASM FILE data\\maps\\entries.asm :\n")
        f.write("; Map entries\n\n")
        f.write("pt_MapData:\n")
        for i in range(total_maps):
            f.write(f"\t\t\t\tdc.l Map{i:02d}\n")
        f.write("\n")

        for i in range(total_maps):
            f.write(f'Map{i:02d}:          include "data\\maps\\entries\\map{i:02d}\\00-tilesets.asm"\n')
            f.write(f"\t\t\t\tdc.l Map{i:02d}s0_Blocks\n")
            f.write(f"\t\t\t\tdc.l Map{i:02d}s1_Layout\n")
            f.write(f"\t\t\t\tdc.l Map{i:02d}s2_Areas\n")
            f.write(f"\t\t\t\tdc.l Map{i:02d}s3_FlagEvents\n")
            f.write(f"\t\t\t\tdc.l Map{i:02d}s4_StepEvents\n")
            f.write(f"\t\t\t\tdc.l Map{i:02d}s5_RoofEvents\n")
            f.write(f"\t\t\t\tdc.l Map{i:02d}s6_WarpEvents\n")
            f.write(f"\t\t\t\tdc.l Map{i:02d}s7_ChestItems\n")
            f.write(f"\t\t\t\tdc.l Map{i:02d}s8_OtherItems\n")
            f.write(f"\t\t\t\tdc.l Map{i:02d}s9_Animations\n")

            f.write(f'Map{i:02d}s2_Areas:      include "data\\maps\\entries\\map{i:02d}\\2-areas.asm"\n')
            f.write(f'Map{i:02d}s3_FlagEvents: include "data\\maps\\entries\\map{i:02d}\\3-flag-events.asm"\n')
            f.write(f'Map{i:02d}s4_StepEvents: include "data\\maps\\entries\\map{i:02d}\\4-step-events.asm"\n')
            f.write(f'Map{i:02d}s5_RoofEvents: include "data\\maps\\entries\\map{i:02d}\\5-roof-events.asm"\n')
            f.write(f'Map{i:02d}s6_WarpEvents: include "data\\maps\\entries\\map{i:02d}\\6-warp-events.asm"\n')
            f.write(f'Map{i:02d}s7_ChestItems: include "data\\maps\\entries\\map{i:02d}\\7-chest-items.asm"\n')
            f.write(f'Map{i:02d}s8_OtherItems: include "data\\maps\\entries\\map{i:02d}\\8-other-items.asm"\n')
            f.write(f'Map{i:02d}s0_Blocks:     incbin "data/maps/entries/map{i:02d}/0-blocks.bin"\n')
            f.write(f'Map{i:02d}s1_Layout:     incbin "data/maps/entries/map{i:02d}/1-layout.bin"\n')
            f.write(f'Map{i:02d}s9_Animations: include "data\\maps\\entries\\map{i:02d}\\9-animations.asm"\n')
            f.write("\n")


# ============================================================
#  Хелперы
# ============================================================

def _music_name(idx):
    """MUSIC_XX — пока просто число."""
    if idx == 255 or idx is None:
        return "NONE"
    return f"music_{idx:02d}"


def _item_name(idx):
    """ITEM_XXX — пока просто число."""
    if idx == 127:
        return "NOTHING"
    if idx > 127:
        # Золото
        return f"GOLD_{(idx - 127) * 10}"
    return f"ITEM_{idx:03d}"


def _facing_name(idx):
    names = ["RIGHT", "UP", "LEFT", "DOWN"]
    if 0 <= idx <= 3:
        return names[idx]
    return "DOWN"