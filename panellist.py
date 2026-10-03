import sys
sys.path.append("panels")

import default
import backgrounds, battles, battle_floors, battle_sprites, spell_anims, dialogue, fonts, other_icons, maps, menu_icons, palettes, portraits, romviewer, sprites, tiles, weapon_sprites
import map_editor

from sf2edit import characters
from sf2edit import classes

panelList = {
    "Battles": battles.BattlePanel,
    "Battle Backgrounds": backgrounds.BackgroundPanel,
    "Battle Floors": battle_floors.BattleFloorPanel,
    "Battle Sprites": battle_sprites.BattleSpritePanel,
    "Spell Animations": spell_anims.SpellAnimationPanel,
    "Dialogue": dialogue.DialoguePanel,
    "Fonts": fonts.FontPanel,
    "Item/Spell Icons": other_icons.OtherIconPanel,
    "Map Editor (ASM)": map_editor.MapEditorPanel,
    # "Map Definitions": maps.MapPanel,
    "Menu Icons": menu_icons.MenuIconPanel,
    "Palettes": palettes.PalettePanel,
    "Portraits": portraits.PortraitPanel,
    "Characters": characters.CharacterPanel,
    "Classes": classes.ClassPanel,
    "ROM Viewer": romviewer.ROMViewerPanel,
    "Sprites": sprites.SpritePanel,
    "Map Tiles": tiles.TilePanel,
    "Weapon Sprites": weapon_sprites.WeaponSpritePanel,
}

sf2editList = ["Classes", "Promotions", "Monsters", "Spells", "Items", "Shops"]   # ← (3) УБРАН "Characters"

def getPanelClass(name):
    if name in panelList:
        return panelList[name]
    elif name in sf2editList:
        return default.SF2EditPanel
    else:
        return default.DefaultPanel