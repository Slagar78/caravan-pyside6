import binascii
import data
import layout
import util
from util import h2i

class ROM(object):

    def __init__(self, file):
        self.file = file
        self.data = {}
        self.dataFile = None
        self.names = {}
        self.modified = False
        self.tables = {}
        self.addresses = {}
        self.values = {}
        self.values["num_menu_icons_unc"] = 7
        self.values["num_weapons"] = 83
        self.values["first_weapon_idx"] = 0x1a
        self.values["num_movetypes"] = 13
        self.values["num_terrain_types"] = 9

        # ---------------------------
        self.sectionData = {
            "dialogue": [
                data.TextBank,
                h2i("28000"),
                17,
                False,
            ],
            "menu_icons": [
                data.MenuIcon,
                h2i("28014"),
                28 + self.values["num_menu_icons_unc"],
                True,
            ],
            "menu_icon_sets": [
                data.Tileset,
                None,
                7,
                False,
            ],
            "other_icons": [
                data.OtherIcon,
                None,
                163,
                False,
            ],
            "tilesets": [
                data.Tileset,
                h2i("64000"),
                115,
                False,
            ],
            "palettes": [
                data.Palette,
                h2i("64004"),
                16,
                False,
            ],
            "maps": [
                data.Map,
                h2i("64008"),
                79,
                False,
            ],
            "sprites": [
                data.Sprite,
                h2i("220000"),  # h2i("C8000"),
                720,
                True,
            ],
            "backgrounds": [
                data.Background,
                h2i("100000"),
                30,
                False,
            ],
            "battle_sprites": [
                data.BattleSprite,
                [h2i("180000"), h2i("130000")],
                [32, 54],
                False,
            ],
            "battles": [
                data.Battle,
                h2i("200000"),  # h2i("1B30EE"),
                45,
                True,
            ],
            "battle_floors": [
                data.BattleFloor,
                h2i("1b8000"),
                30,
                False,
            ],
            "weapon_sprites": [
                data.WeaponSprite,
                h2i("1b8004"),
                23,
                False,
            ],
            "spell_animations": [
                data.SpellAnimation,
                h2i("1b800c"),
                23,
                False,
            ],
            "portraits": [
                data.Portrait,
                h2i("1c8000"),
                56,
                False,
            ],
            "items": [
                data.Item,
                None,
                128,
                False,
            ],
            "music": [
                data.Music,
                None,
                42,
                False,
            ],
        }

        self.addresses["text_font"] = h2i("29002")
        self.addresses["battle_map_info"] = h2i("43800")  # h2i("7A36")
        self.addresses["battle_npcs"] = h2i("43C00")  # h2i("448C4")
        self.addresses["battle_boss_flags"] = h2i("47C8E")
        self.addresses["battle_terrain_ptrs"] = h2i("e0000")  # h2i("1ad104")
        self.addresses["menu_icons_unc"] = h2i("28010")
        self.addresses["other_icons_ptr"] = h2i("1D8000")
        self.addresses["item_weapon_sprites"] = h2i("1f9e2")
        self.addresses["weapon_sprite_colors"] = h2i("1bee38")
        self.addresses["movetype_data"] = h2i("d824")

        # self.initialLayout = layout.ROMLayout()
        # self.initialLayout.parseROM(self)

        self.currentLayout = layout.ROMLayout()
        # self.currentLayout.copyLayout(self.initialLayout)
        self.parseGen = self.currentLayout.parseROM(self, 0x200)

    def initData(self):
        self.initSections()
        self.getSmallData()

    def initSections(self):
        for k, v in self.sectionData.items():
            if k not in self.tables and v[1]:
                self.initTable(k)
            self.handleSpecialCases(k)
            if k not in self.data:
                self.data[k] = []
                if v[1]:
                    iter_range = range(len(self.tables[k]) * v[0].entriesPerEntry)
                else:
                    iter_range = range(v[2] * v[0].entriesPerEntry)
                for idx, b in enumerate(iter_range):
                    adjusted = b // v[0].entriesPerGroup
                    name = str(adjusted) + ": "
                    nameIdx = idx // v[0].entriesPerGroup
                    custom = False
                    if k in self.names and nameIdx in self.names[k]:
                        name += self.names[k][nameIdx]
                        custom = True
                    elif v[0].namePattern:
                        name += v[0].namePattern % adjusted
                    obj = v[0](name=name)
                    obj.hasCustomName = custom
                    self.data[k].append(obj)

    def applyNames(self, data, section, key=None, subkey=None):
        names = {}
        if section in self.names:
            if key is not None and key in self.names[section]:
                names = self.names[section][key]
            elif key is None:
                names = self.names[section]
            if subkey is not None and subkey in names:
                names = names[subkey]
        for i, d in enumerate(data):
            if i in names:
                data[i].name = "%i: %s" % (i, names[i])
                data[i].hasCustomName = True
            elif d.namePattern:
                data[i].name = "%i: %s" % (i, d.namePattern % i)
                data[i].hasCustomName = False
            else:
                data[i].hasCustomName = False
        return data

    def expandROM(self, fn="expandtest.bin"):
        self.startWriteProcess(True)

        # -----------------
        # expand to 4mb
        if len(self.curFileStr) == 0x200000:
            self.curFileStr += b"\x00" * 0x200000

        version = int(self.curFileStr[0x3fffff:0x400000].hex(), 16)

        # -----------------
        # funcs
        def get(*args):
            if len(args) > 2:
                return [self.curFileStr[args[i]:args[i+1]] for i in range(len(args)-1)]
            return self.curFileStr[args[0]:args[1]]

        def setptr(addr, new):
            self.curFileStr = self.curFileStr[:addr] + bytes.fromhex(hex(new).split("x")[1].zfill(8)) + self.curFileStr[addr+4:]

        def setallptrs(data, faddr, taddr):
            diff = taddr - faddr
            num = len(data) // 4
            for n in range(0, len(data), 4):
                h = data[n:n+4].hex()
                if h != "ffffffff":
                    old = int(h, 16)
                    new = bytes.fromhex(hex(old + diff).split("x")[1].zfill(8))
                    data = data[:n] + new + data[n+4:]
            return data

        def repl(taddr, data, clrpoint=None, clrbyte=b"\x00"):
            cl = 0
            if clrpoint:
                cl = clrpoint - taddr - len(data)
            self.curFileStr = self.curFileStr[:taddr] + data + clrbyte * cl + self.curFileStr[taddr+len(data)+cl:]

        def clr(faddr, data):
            self.curFileStr = self.curFileStr[:faddr] + b"\x00" * len(data) + self.curFileStr[faddr+len(data):]

        conv = lambda s: s.replace(" ", "")

        # -----------------
        # load sections
        if version < 1:
            #   map palettes
            paletteTable, paletteData = get(0x9494a, 0x9498a, 0x94b6a)

            #   battle floors
            battleFloorTable, battleFloorData = get(0x1b8028, 0x1b80a0, 0x1b9a9a)

            #   weapon sprites
            weaponSpriteTable, weaponSpriteData = get(0x1b9a9a, 0x1b9af6, 0x1bee38)

            #   battle data
            battleMapCoordTable = get(0x7a36, 0x7b71)
            battleNPCTable = get(0x448c4, 0x4497a)
            battleUnitTable, battleUnitData = get(0x1b30ee, 0x1b31a2, 0x1b6daf)

            #   battle terrain
            battleTerrainTable, battleTerrainData = get(0x1ad104, 0x1ad1b8, 0x1b120a)

            #   dialogue
            dialogueData, dialogueTable = get(0x2eb34, 0x41fda, 0x4201e)

            #   spell animations
            spellAnimTable, spellAnimData = get(0x1beee0, 0x1bef3c, 0x1c46c2)

            #   enemy battle sprites
            enemyBSTable, enemyBSData = get(0x130004, 0x1300dc, 0x17fe4f)

            #   ally battle sprites
            allyBSTable, allyBSData = get(0x18001c, 0x18009c, 0x1aa16e)

            #   battle backgrounds
            battleBGTable, battleBGData = get(0x101ee0, 0x101f58, 0x12a2f8)

            #   portraits
            portraitTable, portraitData = get(0x1c8004, 0x1c80e4, 0x1d7e26)

            #   map data
            mapTable, mapData = get(0x94b8a, 0x94cc6, 0xc7ecc)
            # mapSetupTable, mapSetupData = get(0x4f6e2, 0x4fa70, 0x6348c)

            #   sprite data
            spriteTable, spriteData = get(0xc8000, 0xc8b40, 0xffc4a)
            specialSpriteData = get(0x25df6, 0x2784c)
            specialSpriteTable = get(0x25bfc, 0x25c24)

            #   big images
            titleScreenTiles, titleScreenLayout1, titleScreenLayout2 = get(0x10033e, 0x1014e0, 0x101be0, 0x101ee0)
            kissEndScreen = get(0x1b6dfa, 0x1b7c99)
            witchScreenLayout, witchScreenTiles = get(0x1c4702, 0x1c4e88, 0x1c67c4)
            witchEndScreenLayout, witchEndScreenTiles = get(0x1c67e4, 0x1c6f2c, 0x1c7f7c)
            jewelEndScreenLayout = get(0x1ee930, 0x1ef102)
            jewelEndScreenTiles = get(0x1ef142, 0x1ef4ba)
            suspendStringScreen = get(0x1ef4da, 0x1ef5a6)

        # -----------------
        # change pointers
        if version < 1:
            #   battle npc
            diff = 0x10000 - (0x4481c - 0x43c00)
            self.curFileStr = self.curFileStr[:0x4481c] + bytes.fromhex(hex(diff).split("x")[1]) + self.curFileStr[0x4481e:]

            #   battle terrain
            battleTerrainTable = setallptrs(battleTerrainTable, 0x1ad104, 0xe0000)

            #   battle units
            battleUnitTable = setallptrs(battleUnitTable, 0x1b30ee, 0x200000)

            #   map palettes
            setptr(0x64004, 0xc7000)
            paletteTable = setallptrs(paletteTable, 0x9494a, 0xc7000)

            #   battle floors
            setptr(0x1b8000, 0x30000)
            battleFloorTable = setallptrs(battleFloorTable, 0x1b8028, 0x30000)

            #   weapon sprites
            setptr(0x1b8004, 0x38000)
            weaponSpriteTable = setallptrs(weaponSpriteTable, 0x1b9a9a, 0x38000)

            #   dialogue
            setptr(0x28000, 0x18009c + len(dialogueData))
            dialogueTable = setallptrs(dialogueTable, 0x2eb34, 0x18009c)

            #   spell animations
            setptr(0x1b800c, 0xc8000)
            spellAnimTable = setallptrs(spellAnimTable, 0x1beee0, 0xc8000)

            #   enemy battle sprites
            setptr(0x130000, 0x270000)
            enemyBSTable = setallptrs(enemyBSTable, 0x130004, 0x270000)

            #   ally battle sprites
            setptr(0x180000, 0x2e0000)
            allyBSTable = setallptrs(allyBSTable, 0x18001c, 0x2e0000)

            #   battle backgrounds
            setptr(0x100000, 0x320000)
            battleBGTable = setallptrs(battleBGTable, 0x101ee0, 0x320000)

            #   portraits
            setptr(0x1c8000, 0x360000)
            portraitTable = setallptrs(portraitTable, 0x1c8004, 0x360000)

            #   maps
            setptr(0x64008, 0x380000)
            mapTable = setallptrs(mapTable, 0x94b8a, 0x380000)

            diff2 = int(mapTable[0:4].hex(), 16) - 0x380000
            for n in range(0, len(mapTable), 4):
                rel = int(mapTable[n:n+4].hex(), 16) - 0x380000 - diff2 + 6
                ptrs = setallptrs(mapData[rel:rel+40], 0x94b8a, 0x380000)
                mapData = mapData[:rel] + ptrs + mapData[rel+40:]

            # mapSetupTable = setallptrs(mapSetupTable, 0x4f6e2, 0x180004)

            #   sprites
            spriteTable = setallptrs(spriteTable, 0xc8000, 0x220000)
            specialSpriteTable = setallptrs(specialSpriteTable, 0x25df6, 0x215000)

            #   big images
            setptr(0x1b8014, 0x218000)      # witch layout
            setptr(0x1b8018, 0x218000 + len(witchScreenLayout))      # witch tiles

            setptr(0x1b8020, 0x1c8004)      # witch end layout
            setptr(0x1b8024, 0x1c8004 + len(witchEndScreenLayout))      # witch end tiles

            setptr(0x1ee010, 0x1cc000 + len(jewelEndScreenLayout))      # jewel end tiles
            setptr(0x1ee014, 0x1cc000)      # jewel end layout

            setptr(0x1ac064, 0x211000)      # kiss end

            setptr(0x1ee020, 0x210000)      # suspend string

        # -----------------
        # move sections
        if version < 1:
            clr(0x7a36, battleMapCoordTable)
            clr(0x25df6, specialSpriteData)
            clr(0x2eb34, dialogueData + dialogueTable)
            clr(0x448c4, battleNPCTable)
            # clr(0x4f6e2, mapSetupTable + mapSetupData)
            clr(0x9494a, paletteTable + paletteData)
            clr(0x94b8a, mapTable + mapData)
            clr(0xc8000, spriteTable + spriteData)
            clr(0x101ee0, battleBGTable + battleBGData)
            clr(0x130004, enemyBSTable + enemyBSData)
            clr(0x18001c, allyBSTable + allyBSData)
            clr(0x1ad104, battleTerrainTable + battleTerrainData)
            clr(0x1b30ee, battleUnitTable + battleUnitData)
            clr(0x1b8028, battleFloorTable + battleFloorData)
            clr(0x1b9a9a, weaponSpriteTable + weaponSpriteData)
            clr(0x1beee0, spellAnimTable + spellAnimData)
            clr(0x1c8004, portraitTable + portraitData)

            clr(0x10033e, titleScreenTiles + titleScreenLayout1 + titleScreenLayout2)
            clr(0x1b6dfa, kissEndScreen)
            clr(0x1c4702, witchScreenLayout + witchScreenTiles)
            clr(0x1c67e4, witchEndScreenLayout + witchEndScreenTiles)
            clr(0x1ee930, jewelEndScreenLayout)
            clr(0x1ef142, jewelEndScreenTiles)
            clr(0x1ef4da, suspendStringScreen)

            #   battle data
            repl(0x43800, battleMapCoordTable)
            repl(0x43c00, battleNPCTable)
            repl(0x200000, battleUnitTable + battleUnitData)

            #   battle terrain
            repl(0xe0000, battleTerrainTable + battleTerrainData, 0x100000)

            #   map palettes
            repl(0xc7000, paletteTable + paletteData, 0xc8000)

            #   battle floors
            repl(0x30000, battleFloorTable + battleFloorData, 0x38000)

            #   weapon sprites
            repl(0x38000, weaponSpriteTable + weaponSpriteData, 0x40000)

            #   spell animations
            repl(0xc8000, spellAnimTable + spellAnimData, 0xe0000)

            #   ally battle sprites
            repl(0x2e0000, allyBSTable + allyBSData)

            #   enemy battle sprites
            repl(0x270000, enemyBSTable + enemyBSData)

            #   dialogue
            repl(0x18009c, dialogueData + dialogueTable, 0x1aa16e)

            #   battle backgrounds
            repl(0x320000, battleBGTable + battleBGData)

            #   portraits
            repl(0x360000, portraitTable + portraitData)

            #   maps
            # repl(0x130004, mapSetupTable + mapSetupData)
            repl(0x380000, mapTable + mapData)

            #   sprites
            repl(0x220000, spriteTable + spriteData)
            repl(0x215000, specialSpriteData)
            repl(0x25bfc, specialSpriteTable)

            #   big images
            repl(0x1c0000, titleScreenTiles + titleScreenLayout1 + titleScreenLayout2)
            repl(0x211000, kissEndScreen)
            repl(0x218000, witchScreenLayout + witchScreenTiles)
            repl(0x1c8004, witchEndScreenLayout + witchEndScreenTiles)
            repl(0x1cc000, jewelEndScreenLayout)
            repl(0x1cc000 + len(jewelEndScreenLayout), jewelEndScreenTiles)
            repl(0x210000, suspendStringScreen)

        # -----------------
        # ASM hacks
        if version < 1:
            #   SRAM
            #       Game Init
            self.writeBytes(0x208, conv("4E F9 00 01 FD F0"))
            self.writeBytes(0x1FDF0, conv("13 FC 00 00 00 A1 30 F1 4E F9 00 00 70 D2"))
            #       sub_6EA6
            self.writeBytes(0x6EA6, conv("4E F9 00 01 FD FE"))
            self.writeBytes(0x1FDFE, conv("13 FC 00 01 00 A1 30 F1 48 E7 01 C0 41 F9 00 00 6E 94 4E F9 00 00 6E AE"))
            self.writeBytes(0x6F64, conv("4E F9 00 01 FE 18"))
            self.writeBytes(0x1FE18, conv("13 FC 00 00 00 A1 30 F1 4C DF 03 80 4E 75"))
            #       Start Chunk
            self.writeBytes(0x72E6, conv("4E F9 00 01 FE 26"))
            self.writeBytes(0x1FE26, conv("13 FC 00 01 00 A1 30 F1 7E 20 13 C7 00 20 00 81 4E F9 00 00 72 EE"))
            self.writeBytes(0x7312, conv("4E B9 00 01 FE 3C"))
            self.writeBytes(0x1FE3C, conv("13 C7 00 20 00 8F 13 FC 00 00 00 A1 30 F1 4E 75"))
            #       SaveErrorCode
            self.writeBytes(0x4F8, conv("4E F9 00 01 FE 4C"))
            self.writeBytes(0x1FE4C, conv("13 FC 00 01 00 A1 30 F1 13 F9 00 FF FF F8 00 20 00 81 4E F9 00 00 05 02"))
            self.writeBytes(0x53E, conv("4E F9 00 01 FE 64"))
            self.writeBytes(0x1FE64, conv("13 F9 00 FF FF FF 00 20 00 8F 4E F9 00 00 05 48"))
            #       SaveGame
            self.writeBytes(0x6F6A, conv("4E F9 00 01 FE 74"))
            self.writeBytes(0x1FE74, conv("48 E7 C1 E0 13 FC 00 01 00 A1 30 F1 41 F9 00 FF E8 00 4E F9 00 00 6F 74"))
            self.writeBytes(0x6FA6, conv("4E F9 00 01 FE 8C"))
            self.writeBytes(0x1FE8C, conv("13 FC 00 00 00 A1 30 F1 4C DF 07 83 4E 75"))
            #       LoadGame
            self.writeBytes(0x6FAC, conv("4E F9 00 01 FE 9A"))
            self.writeBytes(0x1FE9A, conv("48 E7 C1 E0 13 FC 00 01 00 A1 30 F1 43 F9 00 FF E8 00 4E F9 00 00 6F B6"))
            self.writeBytes(0x6FD4, conv("4E F9 00 01 FE B2"))
            self.writeBytes(0x1FEB2, conv("13 FC 00 00 00 A1 30 F1 4C DF 07 83 4E 75"))
            #       sub_168D8
            self.writeBytes(0x168DE, conv("4E F9 00 01 FE C0"))
            self.writeBytes(0x1FEC0, conv("48 E7 01 C0 13 FC 00 01 00 A1 30 F1 41 F9 00 20 00 B1 4E F9 00 01 68 E8"))
            self.writeBytes(0x16904, conv("4E F9 00 01 FE D8"))
            self.writeBytes(0x1FED8, conv("4C DF 03 80 13 FC 00 00 00 A1 30 F1 D2 FC 00 72 4E F9 00 01 69 0C"))
            #       sub_6FEC
            self.writeBytes(0x6FF0, conv("4E F9 00 01 FE EE"))
            self.writeBytes(0x1FEEE, conv("13 FC 00 01 00 A1 30 F1 08 B9 00 00 00 20 20 35 13 FC 00 00 00 A1 30 F1 4E 75"))
            self.writeBytes(0x6FFA, conv("4E F9 00 01 FF 08"))
            self.writeBytes(0x1FF08, conv("13 FC 00 01 00 A1 30 F1 08 B9 00 01 00 20 20 35 13 FC 00 00 00 A1 30 F1 4E 75"))
            #       Start Chunk Again
            self.writeBytes(0x73C6, conv("4E B9 00 01 FF 22"))
            self.writeBytes(0x1FF22, conv("13 FC 00 01 00 A1 30 F1 16 39 00 20 20 35 13 FC 00 00 00 A1 30 F1 4E 75"))
            #       WitchNew
            self.writeBytes(0x740A, conv("4E B9 00 01 FF 3A"))
            self.writeBytes(0x1FF3A, conv("13 FC 00 01 00 A1 30 F1 14 39 00 20 20 35 13 FC 00 00 00 A1 30 F1 4E 75"))
            self.writeBytes(0x744A, conv("4E F9 00 01 FF 52"))
            self.writeBytes(0x1FF52, conv("13 FC 00 01 00 A1 30 F1 08 39 00 07 00 20 20 35 67 00 00 10 13 FC 00 00 00 A1 30 F1 4E F9 00 00 74 56 13 FC 00 00 00 A1 30 F1 4E F9 00 00 74 76"))
            #       WitchLoad
            self.writeBytes(0x74E6, conv("4E B9 00 01 FF 82"))
            self.writeBytes(0x1FF82, conv("13 FC 00 01 00 A1 30 F1 14 39 00 20 20 35 13 FC 00 00 00 A1 30 F1 4E 75"))
            #       WitchCopy
            self.writeBytes(0x755C, conv("4E B9 00 01 FF 9A"))
            self.writeBytes(0x1FF9A, conv("13 FC 00 01 00 A1 30 F1 10 39 00 20 20 35 13 FC 00 00 00 A1 30 F1 4E 75"))
            #       WitchDel
            self.writeBytes(0x7578, conv("4E B9 00 01 FF 3A"))
            #   battle map coords
            self.writeBytes(0x427c, conv("60 00 37 B8"))
            self.writeBytes(0x7a36, conv("41 F9 00 04 38 00 4E F9 00 00 42 80"))
            self.writeBytes(0x783a, conv("41 F9 00 04 38 00"))
            self.writeBytes(0x79b2, conv("60 00 00 8E"))
            self.writeBytes(0x7a42, conv("41 F9 00 04 38 00 4E F9 00 00 79 B6"))
            #   battle units
            self.writeBytes(0x1b1640, conv("41 f9 00 20 00 00"))
            #   battle terrain
            self.writeBytes(0x1ad0e0, conv("41 f9 00 0e 00 00"))
            #   sprites
            self.writeBytes(0x60ee, conv("41 f9 00 22 00 00"))
            self.writeBytes(0x61c6, conv("41 f9 00 22 00 00"))
            self.writeBytes(0x23504, conv("41 f9 00 22 00 00"))
            self.writeBytes(0x470ec, conv("41 f9 00 22 00 00"))
            #   map setups
            # self.writeBytes(0x477a8, conv("60 00 7F 38"))
            # self.writeBytes(0x4f6e2, conv("41 F9 00 13 00 04 4E F9 00 04 47 AC"))
            #   title screen
            self.writeBytes(0x10003c, conv("60 00 03 0c"))
            self.writeBytes(0x10034a, conv("41 F9 00 1C 00 00 4E F9 00 10 00 40"))
            self.writeBytes(0x10005e, conv("41 F9 00 1C 11 A2 43 F8 C0 00"))
            self.writeBytes(0x100070, conv("41 F9 00 1C 11 A2 43 F8 C3 58"))
            self.writeBytes(0x100248, conv("60 00 00 F4"))
            self.writeBytes(0x10033e, conv("41 F9 00 1C 11 A2 4E F9 00 10 02 4C"))
            self.writeBytes(0x1000ac, conv("41 F9 00 1C 18 A2 43 F8 DC A8"))
            #   version byte
            self.writeBytes(0x3fffff, conv("01"))

        # -----------------
        # TEMP: done, so save
        outfile = open(fn, "wb")
        outfile.write(self.curFileStr)
        outfile.flush()
        outfile.close()

    # ---------------

    def getSmallData(self):
        self.getBasicMaps()
        # not fully implemented
        self.getItems()
        self.getBasicBattles()
        # self.getDialogue() -- too much to do all at once, call in proper place.
        self.getPalettes()
        # self.getSprites() -- too much to do all at once, call in proper place.
        # self.getMaps(0, len(self.data["maps"])-1)
        self.getOtherIcons()
        self.getTextFont()
        self.getMovetypeData()

    def getMovetypeData(self):
        addr = self.addresses["movetype_data"]
        num_bytes = self.values["num_terrain_types"]
        self.data["movetypes"] = []
        for i in range(self.values["num_movetypes"]):
            raw_str = self.getBytes(addr, num_bytes)
            mt = [raw_str[s:s+2] for s in range(0, len(raw_str), 2)]
            self.data["movetypes"].append(mt)
            addr += 16

    def getItems(self):
        # weapon sprite/palette idxes
        addr = self.addresses["item_weapon_sprites"]
        colorAddr = self.addresses["weapon_sprite_colors"]
        for ws in self.data["weapon_sprites"]:
            ws.colorPairs = []
        self.data["weapon_sprite_colors"] = []
        for i in range(42):
            self.data["weapon_sprite_colors"].append(self.getBytes(colorAddr, 4))
            colorAddr += 4
        for i in range(0, self.values["num_weapons"]):
            sprIdx = h2i(self.getBytes(addr, 1))
            colIdx = h2i(self.getBytes(addr+1, 1))
            if sprIdx < 23 and colIdx not in self.data["weapon_sprites"][sprIdx].colorPairs:
                self.data["weapon_sprites"][sprIdx].colorPairs.append(colIdx)
            addr += 2

    def getBasicBattles(self):
        map_info_reader = self.addresses["battle_map_info"]
        boss_reader = self.addresses["battle_boss_flags"]
        npc_reader = self.addresses["battle_npcs"]
        for i, addr in enumerate(self.tables["battles"]):
            reader = addr
            raw_bytes = ""
            raw_bytes += self.getBytes(reader, 4) + "\n"

            num_force = h2i(self.getBytes(reader, 1))
            num_enemies = h2i(self.getBytes(reader+1, 1))
            num_regions = h2i(self.getBytes(reader+2, 1))
            num_points = h2i(self.getBytes(reader+3, 1))

            force = []
            enemies = []
            regions = []
            points = []
            npcs = []

            reader += 4

            for a in range(num_force):
                unitDef = self.getBytes(reader, 12)
                raw_bytes += unitDef + "\n"
                idx = h2i(self.getBytes(reader, 1))
                x = h2i(self.getBytes(reader+1, 1))
                y = h2i(self.getBytes(reader+2, 1))
                unit = data.BattleUnit()
                unit.init(idx, x, y)
                unit.raw_bytes = unitDef
                force.append(unit)
                reader += 12

            for e in range(num_enemies):
                unitDef = self.getBytes(reader, 12)
                raw_bytes += unitDef + "\n"
                idx = h2i(self.getBytes(reader, 1))
                x = h2i(self.getBytes(reader+1, 1))
                y = h2i(self.getBytes(reader+2, 1))
                misc1 = self.getBytes(reader+10, 1)
                misc2 = self.getBytes(reader+11, 1)
                misc1 = h2i(misc1)
                misc2 = h2i(misc2)
                unit = data.BattleUnit()
                unit.init(idx+64, x, y)
                ai = h2i(self.getBytes(reader+3, 1))
                aic1 = h2i(self.getBytes(reader+6, 1))
                air1 = h2i(self.getBytes(reader+7, 1))
                aic2 = h2i(self.getBytes(reader+8, 1))
                air2 = h2i(self.getBytes(reader+9, 1))
                unit.ai = [ai, [aic1, air1], [aic2, air2]]
                unit.itemBroken = bool(h2i(self.getBytes(reader+4, 1)) // 128)
                unit.item = h2i(self.getBytes(reader+5, 1))
                unit.reinforce = (misc2 & 2) == 2
                unit.respawn = (misc2 & 1) == 1
                unit.misc1 = (misc1 & 96) == 96
                unit.raw_bytes = unitDef
                enemies.append(unit)
                reader += 12

            for r in range(num_regions):
                regionDef = self.getBytes(reader, 12)
                raw_bytes += regionDef + "\n"
                type = h2i(self.getBytes(reader, 1))
                x1 = h2i(self.getBytes(reader+2, 1))
                y1 = h2i(self.getBytes(reader+3, 1))
                x2 = h2i(self.getBytes(reader+4, 1))
                y2 = h2i(self.getBytes(reader+5, 1))
                x3 = h2i(self.getBytes(reader+6, 1))
                y3 = h2i(self.getBytes(reader+7, 1))
                x4 = h2i(self.getBytes(reader+8, 1))
                y4 = h2i(self.getBytes(reader+9, 1))
                region = data.BattleRegion()
                region.init(type, [x1, y1], [x2, y2], [x3, y3], [x4, y4])
                region.raw_bytes = regionDef
                regions.append(region)
                reader += 12

            for p in range(num_points):
                pointDef = self.getBytes(reader, 2)
                raw_bytes += pointDef + "\n"
                x = h2i(self.getBytes(reader, 1))
                y = h2i(self.getBytes(reader+1, 1))
                points.append([x, y])
                reader += 2

            # ----
            npcBattleNum = h2i(self.getBytes(npc_reader, 2))
            if npcBattleNum == i:
                npc_reader += 2
                next = self.getBytes(npc_reader, 2)
                while next != "ffff":
                    npcDef = self.getBytes(npc_reader, 8)
                    npc_x = h2i(self.getBytes(npc_reader, 1))
                    npc_y = h2i(self.getBytes(npc_reader+1, 1))
                    npc_facing = h2i(self.getBytes(npc_reader+2, 1))
                    npc_sprite = h2i(self.getBytes(npc_reader+3, 1))
                    npc_script = h2i(self.getBytes(npc_reader+4, 4))
                    npc = data.BattleNPC()
                    npc.init(npc_sprite, npc_x, npc_y, npc_facing, npc_script)
                    npc.raw_bytes = npcDef
                    npcs.append(npc)
                    npc_reader += 8
                    next = self.getBytes(npc_reader, 2)
                npc_reader += 2

            # ----
            map_index = self.getBytes(map_info_reader, 1)
            map_x1 = self.getBytes(map_info_reader+1, 1)
            map_y1 = self.getBytes(map_info_reader+2, 1)
            map_x2 = self.getBytes(map_info_reader+3, 1)
            map_y2 = self.getBytes(map_info_reader+4, 1)
            map_enter_x = self.getBytes(map_info_reader+5, 1)
            map_enter_y = self.getBytes(map_info_reader+6, 1)
            map_info_reader += 7

            # ----
            hasBoss = bool(h2i(self.getBytes(boss_reader, 1)))
            boss_reader += 1

            # ----
            battle = self.data["battles"][i]
            battle.init(force, enemies, regions, points)
            battle.raw_bytes = raw_bytes
            battle.extra = ""
            battle.npcs = npcs

            # if i != len(self.tables["battles"])-1:
            #     left = (self.tables["battles"][i+1] - reader)
            #     ##print hex(addr) + ", " + hex(reader) + " -- " + repr(left)
            #     battle.extra = self.getBytes(reader, left)
            #     battle.raw_bytes += battle.extra

            battle.map_index = h2i(map_index)
            battle.map_x1 = h2i(map_x1)
            battle.map_y1 = h2i(map_y1)
            battle.map_x2 = h2i(map_x2) + h2i(map_x1)
            battle.map_y2 = h2i(map_y2) + h2i(map_y1)
            battle.map_enter_x = h2i(map_enter_x)
            battle.map_enter_y = h2i(map_enter_y)
            battle.boss = hasBoss

    def getBattles(self, start, end):
        terrain_reader = self.addresses["battle_terrain_ptrs"] + start * 4
        for i in range(start, end+1):
            battle = self.data["battles"][i]
            terrain_addr = h2i(self.getBytes(terrain_reader, 4))
            terrain = data.Tileset()
            self.tilesetSubroutine(terrain, self.file, terrain_addr)
            terrain_reader += 4
            # print len(terrain.tiles)
            # print " / ".join([" ".join([p for p in t.pixels]) for t in terrain.tiles])
            # print hex(terrain_addr)
            battle.terrain = terrain
            battle.loaded = True

    def getTextFont(self):
        letters = " 0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_-.,!?"
        letters = [l for l in letters]
        letters.append("lquote")
        letters.append("rquote")
        letters2 = "'()#%&+/:"
        letters += [l for l in letters2]
        self.fontOrder = letters

        pos = self.addresses["text_font"]
        self.data["fonts"] = []
        self.data["fonts"].append(data.Font(name="Dialogue Font (VW)"))
        self.data["fonts"].append(data.Font(name="System Font"))

        font = self.data["fonts"][0]
        font.init()

        for num in range(len(letters)):
            bytes_str = self.getBytes(pos + num*32, 32)
            width = h2i(bytes_str[3])
            glyph = data.FontGlyph()
            glyph.init(width, [])
            for row in range(4, 64, 4):
                pixels = "".join([util.bin(int(bytes_str[i], 16), 4) for i in range(row, row+4)])
                glyph.pixels.append(pixels)
            font.glyphs[letters[num]] = glyph

    def getPalettes(self):
        names = ["Map Palette %02i" % i for i in range(16)]
        names.append("Sprite & UI Palette")
        # append more palette names

        for j, a in enumerate(self.tables["palettes"]):
            raw = self.getBytes(a, 32)
            raw = [raw[i*4:i*4+4] for i in range(16)]
            p = self.data["palettes"][j]
            if not p.hasCustomName:
                p.setIndexedName(names[j])
            p.init(["#%s%s%s" % (r[3]*2, r[2]*2, r[1]*2) for r in raw])
            if names[j].startswith("Map Palette"):
                p.isMapPalette = True
            # self.data["palettes"].append(p)

    def getBasicMaps(self):
        for idx, addr in enumerate(self.tables["maps"]):
            map = self.data["maps"][idx]
            done = False
            reader = addr
            raw_bytes = ""
            func = self.getBytes

            # if type(source) == type(""):
            #     func = lambda pos, num: source[pos*2:pos*2+num*2]
            # else:
            #     func = self.getBytes

            pal = func(reader, 1)
            paletteIdx = h2i(pal)
            raw_bytes += pal + " "

            tilesetIdxes = []
            for t in range(5):
                tilesetIdx = func(reader+t+1, 1)
                tilesetIdxes.append(h2i(tilesetIdx))
                raw_bytes += tilesetIdx + " "
            raw_bytes += "\n"

            reader += 6

            sectionAddrs = []
            for t in range(10):
                addr = func(reader, 4)
                sectionAddrs.append(h2i(addr))
                reader += 4
                raw_bytes += addr + "\n"

            for t in range(10):
                reader = sectionAddrs[t]
                raw_bytes += func(reader, 2) + "\n"

            # ----
            # map setups
            """
            setups = []
            reader = h2i("4f6e2")
            ...
            """
            # ----

            map.init(paletteIdx, tilesetIdxes, sectionAddrs)  # , setupAddrs)
            map.raw_bytes = raw_bytes

    def getMaps(self, start, end):
        # for i,addr in enumerate(self.tables["sprites"]):
        for i in range(start, end+1):
            self.mapSubroutine(self.file, i)

    def mapSubroutine(self, source, idx):
        map = self.data["maps"][idx]
        addr = self.tables["maps"][idx]

        done = False
        reader = addr
        raw_bytes = hex(addr) + "\n"

        if type(source) == str:
            func = lambda pos, num: source[pos*2:pos*2+num*2]
        else:
            func = self.getBytes

        pal = func(reader, 1)
        paletteIdx = h2i(pal)
        raw_bytes += pal + " "

        tilesetIdxes = []
        for t in range(5):
            tilesetIdx = func(reader+t+1, 1)
            tilesetIdxes.append(h2i(tilesetIdx))
            raw_bytes += tilesetIdx + " "
        raw_bytes += "\n"

        reader += 6

        sectionAddrs = []
        for t in range(10):
            addr = func(reader, 4)
            if addr != "ffffffff":
                sa = h2i(addr)
            else:
                sa = None
            sectionAddrs.append(sa)
            reader += 4
            if addr != "ffffffff":
                raw_bytes += "%s -- %s\n" % (addr, hex(h2i(func(h2i(addr), 2)))[2:])
            else:
                raw_bytes += addr + "\n"

        # print [hex(s) for s in sectionAddrs if s]

        # ----
        # map setups
        raw_bytes += "-----------------\n"

        reader = h2i("4f6e2")
        readIdx = None

        while readIdx != idx:
            if readIdx is not None:
                reader += 4
                value = ""
                while value != "fffd":
                    value = func(reader, 2)
                    reader += 6
                if func(reader-4, 2) == "ffff":
                    readIdx = None
                    break
                reader -= 4
            readIdx = h2i(func(reader, 2))
            reader += 2

        setups = []
        setupAddrs = []
        configs = [[], [], [], [], [], []]

        if readIdx == idx:
            value = ""
            while True:
                addr = h2i(func(reader, 4))
                setupAddrs.append(addr)
                reader += 4

                setupSectionIdxes = []
                for a in range(6):
                    sa = h2i(func(addr+a*4, 4))
                    if sa not in configs[a]:
                        configs[a].append(sa)
                    setupSectionIdxes.append(configs[a].index(sa))

                flag = func(reader, 2)
                reader += 2

                ms = data.MapSetup()
                ms.init(h2i(flag), setupSectionIdxes)
                setups.append(ms)

                if flag == "fffd":
                    ms.flag = None
                    break

            defaultSetupIdx = setupAddrs[-1]
            raw_bytes += hex(defaultSetupIdx) + "\n"

            reader = defaultSetupIdx
            for a in range(6):
                adr = func(reader, 4)
                raw_bytes += "%s -- %s\n" % (adr, hex(h2i(func(h2i(adr), 1)))[2:])
                reader += 4

        raw_bytes = raw_bytes[:-1]

        # ----
        map.init(paletteIdx, tilesetIdxes, sectionAddrs, setupAddrs)
        map.raw_bytes = raw_bytes

        map.setups = setups
        map.setups = self.applyNames(map.setups, "map_setups", idx)
        map.configs = configs

        map.blocks = self.mapBlockSubroutine(source, sectionAddrs[0], map, idx)
        map.layoutData = self.mapLayoutSubroutine(source, sectionAddrs[1], idx)

        lastX = 0
        lastY = 0

        for y in range(64):
            xcnt = 63
            while map.layoutData[y*64+xcnt] & 0x3ff == 0 and xcnt > 0:
                xcnt -= 1
            if xcnt > lastX:
                lastX = xcnt

        for x in range(64):
            ycnt = 63
            while map.layoutData[ycnt*64+x] & 0x3ff == 0 and ycnt > 0:
                ycnt -= 1
            if ycnt > lastY:
                lastY = ycnt

        map.width = lastX + 1
        map.height = lastY + 1

        # ----
        # setup basics
        # reader =

        # ----
        # area data
        reader = sectionAddrs[2]
        areas = []

        while func(reader, 2) != "ffff":
            bytes = func(reader, 30)

            l1x1 = int(bytes[0:4], 16)
            l1y1 = int(bytes[4:8], 16)
            l1x2 = int(bytes[8:12], 16)
            l1y2 = int(bytes[12:16], 16)
            layerType = int(bytes[56:58], 16)

            if layerType == 0:  # foreground layer
                l2x = int(bytes[16:20], 16)
                l2y = int(bytes[20:24], 16)

                l2xp = int(bytes[32:36], 16)
                l2yp = int(bytes[36:40], 16)
                l1xp = int(bytes[40:44], 16)
                l1yp = int(bytes[44:48], 16)

                l2xs = (int(bytes[48:50], 16) + 128) % 256 - 128
                l2ys = (int(bytes[50:52], 16) + 128) % 256 - 128
                l1xs = (int(bytes[52:54], 16) + 128) % 256 - 128
                l1ys = (int(bytes[54:56], 16) + 128) % 256 - 128
            else:
                l2x = int(bytes[24:28], 16)
                l2y = int(bytes[28:32], 16)

                l1xp = int(bytes[32:36], 16)
                l1yp = int(bytes[36:40], 16)
                l2xp = int(bytes[40:44], 16)
                l2yp = int(bytes[44:48], 16)

                l1xs = (int(bytes[48:50], 16) + 128) % 256 - 128
                l1ys = (int(bytes[50:52], 16) + 128) % 256 - 128
                l2xs = (int(bytes[52:54], 16) + 128) % 256 - 128
                l2ys = (int(bytes[54:56], 16) + 128) % 256 - 128

            music = int(bytes[58:60], 16)

            area = data.MapArea()
            area.init(l1x1, l1y1, l1x2, l1y2, l2x, l2y, l1xp, l1yp, l2xp, l2yp, l1xs, l1ys, l2xs, l2ys, layerType, music)
            areas.append(area)
            reader += 30

        areas = self.applyNames(areas, "map_areas", idx)
        map.areas = areas

        # ----
        # copies data
        copies = []
        copyType = 0

        for saIdx in range(3, 6):
            reader = sectionAddrs[saIdx]

            while func(reader, 2) != "ffff":
                bytes = func(reader, 8)

                if copyType == 0:
                    flag = int(bytes[0:4], 16)
                    stepx = 0
                    stepy = 0
                else:
                    stepx = int(bytes[0:2], 16)
                    stepy = int(bytes[2:4], 16)

                srcx = int(bytes[4:6], 16)
                srcy = int(bytes[6:8], 16)
                width = int(bytes[8:10], 16)
                height = int(bytes[10:12], 16)
                destx = int(bytes[12:14], 16)
                desty = int(bytes[14:16], 16)
                mbc = data.MapBlockCopy()
                mbc.init(stepx, stepy, srcx, srcy, width, height, destx, desty, copyType)

                if copyType == 0:
                    mbc.flag = flag

                copies.append(mbc)
                reader += 8

            copyType += 1

        copies = self.applyNames(copies, "map_copies", idx)
        map.copies = copies

        # ----
        # warp data
        reader = sectionAddrs[6]
        warps = []

        while func(reader, 2) != "ffff":
            bytes = func(reader, 8)
            x = int(bytes[0:2], 16)
            y = int(bytes[2:4], 16)
            dmap = int(bytes[4:8], 16)
            dx = int(bytes[8:10], 16)
            dy = int(bytes[10:12], 16)
            facing = int(bytes[12:14], 16)
            myst = int(bytes[14:16], 16)

            warp = data.MapWarp()
            warp.init(x, y, dmap, dx, dy, facing, myst)
            warps.append(warp)
            reader += 8

        warps = self.applyNames(warps, "map_warps", idx)
        map.warps = warps

        # ----
        # item data
        items = []
        isChest = True

        for saIdx in range(7, 9):
            reader = sectionAddrs[saIdx]

            while func(reader, 2) != "ffff":
                bytes = func(reader, 4)
                x = int(bytes[0:2], 16)
                y = int(bytes[2:4], 16)
                flag = int(bytes[4:6], 16)
                itemIdx = int(bytes[6:8], 16)
                item = data.MapItem()
                item.init(x, y, flag, itemIdx, isChest)
                items.append(item)
                reader += 4

            isChest = False

        # THIS IS TEMPORARY. REPLACE WITH ACTUAL ITEM NAMES ONCE ITEM LOADING IS IN.
        for i, a in enumerate(items):
            if a.itemIdx > 127:
                last = str((a.itemIdx - 127) * 10) + " Gold"
            else:
                last = self.data["items"][a.itemIdx].getIndexedName()
            a.name = "%i: %s" % (i, last)

        map.items = items

        # ----
        # animation data
        reader = sectionAddrs[9]
        anims = []
        num = 0
        tsIdx = None

        if reader is not None:
            bytes = func(reader, 2)
            tsIdx = int(bytes[0:4], 16)
            reader += 4

            while func(reader, 2) < "8000":
                bytes = func(reader, 8)

                start = int(bytes[0:4], 16)
                length = int(bytes[4:8], 16)
                dest = int(bytes[8:12], 16)
                delay = int(bytes[12:16], 16)

                anim = data.MapAnim()
                anim.init(start, start+length, dest, delay)
                anims.append(anim)

                reader += 8
                num += 1

        anims = self.applyNames(anims, "map_anims", idx)
        map.animTSIdx = tsIdx
        map.anims = anims

        # ----
        map.loaded = True
        return map
        
    def mapBlockSubroutine(self, source, addr, map, idx):

        # test map data load

        if type(source) == str:
            func = lambda pos, num: source[pos*2:pos*2+num*2]
        else:
            func = self.getBytes

        def getNextBarrel(barrel, reader):
            prev = len(barrel)
            barrel += "".join([format(int(l, 16), '04b') for l in func(reader, 2)])
            reader += 2
            return barrel, reader

        reader = addr
        cmds = "".join([format(int(l, 16), '04b') for l in func(reader, 2)])
        reader += 2
        barrel = cmds[-2:]
        cmd = ""

        # print cmds

        num_cmds = h2i(hex(int("00" + cmds[:-2], 2))[2:])

        stack = [0x0100] * 9 + \
            [0x032e, 0x032f, 0x0b2e, 0x033e, 0x033f, 0x0b3e, 0x034e, 0x034f, 0x0b4e,
             0x032c, 0x032d, 0x0b2c, 0x033c, 0x033d, 0x0b3c, 0x034e, 0x034f, 0x0b4e]

        sets = {}

        # print "-------------"
        # print hex(num_cmds)

        pcmds = []

        while num_cmds > 0:

            while barrel != "":

                cmd += barrel[0]
                barrel = barrel[1:]

                pcmd = cmd

                if cmd in ["00", "01", "100", "101", "110", "111"]:

                    if cmd == "00":
                        pcmd += " -- copy last tile (%s)" % hex(stack[-1])[2:]
                        stack += [stack[-1]]

                    elif cmd == "01":
                        pcmd += " -- copy last tile, and "

                        if stack[-1] & 0x0800:
                            pcmd += "subtract 1 (%s)" % hex(stack[-1]-1)[2:]
                            stack += [stack[-1]-1]
                        else:
                            pcmd += "add 1 (%s)" % hex(stack[-1]+1)[2:]
                            stack += [stack[-1]+1]

                    elif cmd == "100":
                        ofs = (stack[-1] & 0x03ff) * 2 + (stack[-1] & 0x0800)
                        if ofs not in sets:
                            val = 0
                        else:
                            val = sets[ofs]
                        pcmd += " -- copy from sets using last offset %s -> %s -> (%s)" % (hex(stack[-1])[2:], hex(ofs), hex(val)[2:])
                        stack += [val]

                    elif cmd == "101":
                        ofs = (stack[-3] & 0x03ff) * 2 + (stack[-3] & 0x0800) + 0x1000
                        if ofs not in sets:
                            val = 0
                        else:
                            val = sets[ofs]
                        pcmd += " -- copy from sets using 3rd last offset %s -> %s -> (%s)" % (hex(stack[-3])[2:], hex(ofs), hex(val)[2:])
                        stack += [val]

                    elif cmd == "110" or cmd == "111":

                        pcmd += " -- "
                        if cmd == "110":
                            top = stack[-1] & int("1001100000000000", 2)
                        else:
                            if len(barrel) < 3:
                                barrel, reader = getNextBarrel(barrel, reader)
                            top = int("%s00%s%s00000000000" % (barrel[0], barrel[1], barrel[2]), 2)
                            pcmd += barrel[:3] + " "
                            barrel = barrel[3:]

                        if len(barrel) < 1:
                            barrel, reader = getNextBarrel(barrel, reader)
                        flag = barrel[0]
                        barrel = barrel[1:]
                        pcmd += flag + ", "

                        if flag == "0":

                            if len(barrel) < 6:
                                barrel, reader = getNextBarrel(barrel, reader)
                            bottom = int(barrel[:5], 2)
                            negate = barrel[5]
                            pcmd += barrel[:5] + " " + negate

                            barrel = barrel[6:]

                            if negate == "1":
                                bottom = -bottom

                            bottom += stack[-1] & 0x07ff

                        else:

                            if len(barrel) < 9:
                                barrel, reader = getNextBarrel(barrel, reader)
                            bottom = int(barrel[:9], 2)
                            pcmd += barrel[:9]

                            barrel = barrel[9:]

                            if bottom >= 384:
                                if len(barrel) < 1:
                                    barrel, reader = getNextBarrel(barrel, reader)
                                bottom *= 2
                                bottom += int(barrel[0])
                                bottom -= 384
                                pcmd += "-" + barrel[0]

                                barrel = barrel[1:]

                            bottom += 256

                        full = bottom | top

                        ofs1 = (stack[-1] & 0x03ff) * 2 + (stack[-1] & 0x0800)
                        ofs2 = (stack[-3] & 0x03ff) * 2 + (stack[-3] & 0x0800) + 0x1000
                        sets[ofs1] = full
                        sets[ofs2] = full

                        stack += [full]

                        pcmd += " -> " + hex(full)[2:] + " at %s, %s" % (hex(ofs1), hex(ofs2))

                    pcmds.append(pcmd + "\n")

                    if not len(stack) % 9:
                        pcmds.append("\n%s -- FF%s\n" % (hex(len(stack)//9), hex(0x2000 + len(stack) * 2)[2:]))

                    cmd = ""
                    num_cmds -= 1

                    # if idx == 42:
                    #     raw_input()

            barrel, reader = getNextBarrel(barrel, reader)

            # print repr(num_cmds)
            # print repr(barrel)

        """f = file("output/blockdef%i.dat" % idx, "w")
        f.writelines(pcmds)
        f.flush()
        f.close()"""

        # print repr([hex(s) for s in stack])
        # stack = [s for s in stack if ((s >= 256) and ((s & 0x7ff) < 0x380))]

        # print "FF%s" % hex(0x2000 + len(stack) * 2)[2:]
        # ---------------------
        # ---------------------

        blocks = []

        for idx in range(0, len(stack)//9*9, 9):
            tileIdxes = stack[idx:idx+9]
            tiles = []
            ptileIdxes = []

            for ti in tileIdxes:

                bti = ti
                base = (ti & 0x7ff) - 256
                set_val = base // 128
                ti = ti % 128

                # print repr(hex(base+256))

                if set_val < 5 and map.tilesetIdxes[set_val] != 255:

                    if not self.data["tilesets"][map.tilesetIdxes[set_val]].loaded:
                        self.getTilesets(map.tilesetIdxes[set_val], map.tilesetIdxes[set_val])

                    tiles.append(self.data["tilesets"][map.tilesetIdxes[set_val]].tiles[ti])

                    ptileIdxes.append(bti)

                else:

                    tiles.append(self.data["tilesets"][map.tilesetIdxes[0]].tiles[0])
                    ptileIdxes.append(0x100)

            block = data.Block()
            block.init(tileIdxes, tiles)
            block.createPixelArray()
            blocks.append(block)

        return blocks

    def mapLayoutSubroutine(self, source, addr, idx):

        if type(source) == str:
            func = lambda pos, num: source[pos*2:pos*2+num*2]
        else:
            func = self.getBytes

        def getNextBarrel(barrel, reader):
            prev = len(barrel)
            barrel += "".join([format(int(l, 16), '04b') for l in func(reader, 2)])
            # print ">>> Reading from %s... (%s)%s" % (hex(reader)[2:], barrel[:prev], barrel[prev:])
            reader += 2
            return barrel, reader

        # ---------------------
        # ---------------------
        # test map data load

        reader = addr
        barrel = ""

        # print cmds

        highest = 2
        mapdata = []
        uminis = {}
        lminis = {}

        # print "--------------"

        pcmds = []
        cmd = ""

        try:

            while len(mapdata) < 0x1000:

                next = True
                miniadd = True
                blk = 0

                if len(barrel) < 1:
                    barrel, reader = getNextBarrel(barrel, reader)
                cmd += barrel[0]
                barrel = barrel[1:]

                pcmd = hex(0xFF0000 + len(mapdata) * 2)[2:] + ": " + cmd

                if cmd == "00":

                    highest += 1
                    blk = highest

                    if len(barrel) < 1:
                        barrel, reader = getNextBarrel(barrel, reader)
                        pcmd
                    cmd += barrel[0]
                    barrel = barrel[1:]

                    pcmd += " %s " % cmd[-1]

                    if cmd[-1] == "0":

                        if len(barrel) < 1:
                            barrel, reader = getNextBarrel(barrel, reader)
                        cmd += barrel[0]
                        barrel = barrel[1:]

                        pcmd += cmd[-1]

                        if cmd[-1] == "1":
                            blk |= 0xc000

                    else:

                        if len(barrel) < 1:
                            barrel, reader = getNextBarrel(barrel, reader)
                        cmd += barrel[0]
                        barrel = barrel[1:]

                        pcmd += cmd[-1]

                        if cmd[-1] == "0":

                            if len(barrel) < 1:
                                barrel, reader = getNextBarrel(barrel, reader)
                            cmd += barrel[0]
                            pcmd += " " + barrel[0]
                            barrel = barrel[1:]

                            blk |= (1 + int(cmd[-1])) * 0x4000

                        else:

                            if len(barrel) < 6:
                                barrel, reader = getNextBarrel(barrel, reader)
                            cmd += barrel[:6]
                            pcmd += " " + barrel[:6]
                            top = int(barrel[:6] + ("0"*10), 2)
                            barrel = barrel[6:]

                            blk |= top

                    pcmd += " -- add next block incrementally"

                    mapdata.append(blk)

                elif cmd == "01":

                    pcmd += " "

                    cnt = 0

                    while cmd == "01" or cmd[-1] == "0":

                        if len(barrel) < 1:
                            barrel, reader = getNextBarrel(barrel, reader)
                        cmd += barrel[0]
                        pcmd += barrel[0]
                        barrel = barrel[1:]

                        cnt += 1

                    pcmd += " "

                    cnt -= 1
                    mcnt = cnt
                    num = 0

                    while cnt > 0:

                        if len(barrel) < 1:
                            barrel, reader = getNextBarrel(barrel, reader)
                        cmd += barrel[0]
                        pcmd += barrel[0]
                        num = num * 2 + int(barrel[0])
                        barrel = barrel[1:]

                        cnt -= 1

                    num += 2 ** mcnt

                    if len(barrel) < 1:
                        barrel, reader = getNextBarrel(barrel, reader)
                    cmd += barrel[0]
                    typ = int(barrel[0])
                    pcmd += " " + barrel[0]
                    barrel = barrel[1:]

                    blks = []
                    for n in range(num):
                        blk = mapdata[-[0x0040, 0x0001][typ]]
                        mapdata.append(blk)
                        if n < 5:
                            blks.append(blk)

                    pcmd += " -- copy %s block %i times" % (["up","left"][typ], num)

                    miniadd = False

                elif cmd == "1":

                    """if len(mapdata) > 0 and mapdata[-1]&0x3ff in lminis:
                        print "left %s: %s" % (hex(mapdata[-1]&0x3ff)[2:].zfill(4), repr([hex(i)[2:].zfill(4) for i in lminis[mapdata[-1]&0x3ff]]))
                    elif len(mapdata) > 1:
                        print "left %s: no stack" % hex(mapdata[-1]&0x3ff)[2:].zfill(4)
                    if len(mapdata) > 64 and mapdata[-64]&0x3ff in uminis:
                        print "top %s: %s" % (hex(mapdata[-64]&0x3ff)[2:].zfill(4), repr([hex(i)[2:].zfill(4) for i in uminis[mapdata[-64]&0x3ff]]))
                    elif len(mapdata) > 64:
                        print "top %s: no stack" % hex(mapdata[-64]&0x3ff)[2:].zfill(4)"""

                    customOvr = len(mapdata) >= 1 and (mapdata[-1] & 0x3ff) not in lminis and len(mapdata) >= 64 and (mapdata[-64] & 0x3ff) not in uminis

                    if len(mapdata) == 0:
                        customOvr = True

                    if not customOvr:

                        if len(barrel) < 1:
                            barrel, reader = getNextBarrel(barrel, reader)
                        cmd += barrel[0]
                        pcmd += barrel[0]
                        barrel = barrel[1:]

                        if cmd[-1] == "1" and (mapdata[-1] & 0x3ff) in lminis:

                            if len(mapdata) >= 64 and (mapdata[-64] & 0x3ff) not in uminis:
                                customOvr = True

                            else:

                                if len(barrel) < 1:
                                    barrel, reader = getNextBarrel(barrel, reader)
                                cmd += barrel[0]
                                pcmd += barrel[0]
                                barrel = barrel[1:]

                    if cmd[-1] == "0" and not customOvr:

                        cnt = 0
                        pcmd += " "
                        lst = []

                        listIdx = 0

                        left = False
                        top = False

                        if len(mapdata) > 1 and (mapdata[-1] & 0x3ff) in lminis and len(cmd) < 3:
                            listIdx += mapdata[-1] & 0x3ff
                            left = True
                            name = "left"
                            lst = lminis[listIdx]
                        elif len(mapdata) > 64 and (mapdata[-64] & 0x3ff) in uminis:
                            listIdx += mapdata[-64] & 0x3ff
                            top = True
                            name = "top"
                            lst = uminis[listIdx]
                        if listIdx == 0 and not left and not top:
                            name = "zero"
                            lst = uminis[listIdx]

                        if len(lst) == 1:
                            blk = lst[0]

                        else:

                            while cmd[-1] != "1" and cnt < len(lst)-1:

                                if len(barrel) < 1:
                                    barrel, reader = getNextBarrel(barrel, reader)
                                cmd += barrel[0]
                                pcmd += barrel[0]
                                barrel = barrel[1:]

                                cnt += 1

                            blk = lst[cnt - int(cmd[-1])]

                        mapdata.append(blk)

                        pcmd += " -- %s stack's %s->(%s) idx#%i" % (name, hex(listIdx)[2:], repr([hex(n)[2:] for n in lst]), cnt)

                    else:

                        start = len(cmd)
                        cnt = highest
                        pcmd += " "

                        while cnt != 0:

                            if len(barrel) < 1:
                                barrel, reader = getNextBarrel(barrel, reader)
                            cmd += barrel[0]
                            pcmd += barrel[0]
                            barrel = barrel[1:]

                            cnt //= 2

                        blk = int(cmd[start:], 2)

                        if len(barrel) < 1:
                            barrel, reader = getNextBarrel(barrel, reader)
                        cmd += barrel[0]
                        barrel = barrel[1:]

                        pcmd += " %s" % cmd[-1]

                        if cmd[-1] == "0":

                            if len(barrel) < 1:
                                barrel, reader = getNextBarrel(barrel, reader)
                            cmd += barrel[0]
                            barrel = barrel[1:]

                            pcmd += cmd[-1]

                            if cmd[-1] == "1":
                                blk |= 0xc000

                        else:

                            if len(barrel) < 1:
                                barrel, reader = getNextBarrel(barrel, reader)
                            cmd += barrel[0]
                            barrel = barrel[1:]

                            pcmd += cmd[-1]

                            if cmd[-1] == "0":

                                if len(barrel) < 1:
                                    barrel, reader = getNextBarrel(barrel, reader)
                                cmd += barrel[0]
                                pcmd += " " + barrel[0]
                                barrel = barrel[1:]

                                blk |= (1 + int(cmd[-1])) * 0x4000

                            else:

                                if len(barrel) < 6:
                                    barrel, reader = getNextBarrel(barrel, reader)
                                cmd += barrel[:6]
                                pcmd += " " + barrel[:6]
                                top = int(barrel[:6] + ("0"*10), 2)
                                barrel = barrel[6:]

                                blk |= top

                        pcmd += " -- make custom block idx"
                        mapdata.append(blk)

                else:
                    next = False

                if next == True:

                    if miniadd:

                        pcmd += " -- (%s)\n" % hex(blk)[2:].zfill(4)

                        if len(mapdata) > 1:
                            last = mapdata[-2] & 0x3ff
                        else:
                            last = 0

                        if last not in lminis:
                            lminis[last] = []
                        if len(lminis[last]) == 0 or lminis[last][0] != blk:
                            lminis[last].insert(0, blk)
                            if lminis[last].count(blk) > 1:
                                lminis[last].pop(lminis[last].index(blk, 1))
                            lminis[last] = lminis[last][:4]

                        if len(mapdata) > 64:
                            last = mapdata[-65] & 0x3ff
                        else:
                            last = 0

                        if last not in uminis:
                            uminis[last] = []
                        if len(uminis[last]) == 0 or uminis[last][0] != blk:
                            uminis[last].insert(0, blk)
                            if uminis[last].count(blk) > 1:
                                uminis[last].pop(uminis[last].index(blk, 1))
                            uminis[last] = uminis[last][:4]

                    else:
                        pcmd += " -- %s\n" % repr([hex(blk)[2:].zfill(4) for blk in blks])

                    pcmds.append(pcmd)
                    cmd = ""

                    # print pcmd[:-1]

                    # if idx == 4: # and pcmd[:6] >= "ff0480":
                        # print repr(lminis)
                        # print repr(uminis)
                        # raw_input()
                    #     pass

        except Exception as e:
            pcmds.append("\nDied:\n(((%s)))\n -- %s\n" % (pcmd, str(e)))
            # print pcmds[-1]

        """f = file("output/mapdef%i.dat" % idx, "w")
        f.writelines(pcmds)
        f.write("----------------\n")
        f.write(repr(lminis))
        f.write(repr(uminis))
        f.flush()
        f.close()"""

        return mapdata

    # ---------------------
    # ---------------------

    def getSprites(self, start, end):

        # for i,addr in enumerate(self.tables["sprites"]):
        for i in range(start, end+1):
            spr = self.data["sprites"][i]
            spr.init(24, 24)
            self.spriteSubroutine(spr, self.file, self.tables["sprites"][i])

    def getPortraits(self, start, end):

        # for i,addr in enumerate(self.tables["sprites"]):
        for i in range(start, end+1):

            p = self.data["portraits"][i]
            addr = self.tables["portraits"][i]

            numEyeChanges = h2i(self.getBytes(addr, 2))
            eyeBytes = self.getBytes(addr, numEyeChanges * 4 + 2)  # not implemented
            addr += numEyeChanges * 4 + 2

            numMouthChanges = h2i(self.getBytes(addr, 2))
            mouthBytes = self.getBytes(addr, numMouthChanges * 4 + 2)  # not implemented
            addr += numMouthChanges * 4 + 2

            p.init()
            p.eyeBytes = eyeBytes
            p.mouthBytes = mouthBytes

            # -------

            cols = self.getBytes(addr, 32)
            acols = []
            for c in range(16):
                a, b, g, r = cols[c*4:c*4+4]
                acols.append("#" + r + r + g + g + b + b)
            p.palette.init(acols)
            addr += 32

            p.frame.init()
            self.tilesetSubroutine(p.frame, self.file, addr)

            # print p.frame.pixels
            # print p.frame.raw_pixels
            # print p.frame.raw_pixels2
            # print "---"

            p.loaded = True

    def getWeaponSprites(self, start, end):

        # for i,addr in enumerate(self.tables["sprites"]):
        for i in range(start, end+1):

            ws = self.data["weapon_sprites"][i]
            addr = self.tables["weapon_sprites"][i]

            ws.init()

            # -------

            cols = "042a0eee0000" + "042a" * 11

            for cp in ws.colorPairs:

                pal = data.Palette()

                ccols = cols + self.data["weapon_sprite_colors"][cp]
                acols = []
                for c in range(16):
                    a, b, g, r = ccols[c*4:c*4+4]
                    acols.append("#" + r + r + g + g + b + b)

                pal.init(acols)
                ws.palettes.append(pal)

            ff = data.WeaponSpriteFrame()
            ff.init()
            self.tilesetSubroutine(ff, self.file, addr)

            size = len(ff.pixels) // 4
            for frm in range(4):
                cf = data.WeaponSpriteFrame()
                cf.init()
                # cf.pixels = "".join([p[frm*64:(frm+1)*64] for p in ff.pixels])
                cf.tiles = ff.tiles[frm*64:(frm+1)*64]
                ws.frames.append(cf)

            ws.loaded = True

    def getSpellAnimations(self, start, end):

        # for i,addr in enumerate(self.tables["sprites"]):
        for i in range(start, end+1):

            sa = self.data["spell_animations"][i]
            addr = self.tables["spell_animations"][i]

            sa.init()

            # -------

            # 9, 13, 14
            # TODO: replace from sprite palette
            cols = "042a0eee0000" + "042a" * 6 + "%s" + "042a" * 3 + "%s%s" + "042a"

            acols = [self.getBytes(addr+i, 2) for i in range(2, 8, 2)]
            addr += 8

            pal = data.Palette()
            spal = self.getDataByName("palettes", "Sprite & UI Palette")
            cols = spal.colors[:]
            rnums = [9, 13, 14]

            for c in range(3):
                i = rnums[c]
                a, b, g, r = acols[c]
                cols[i] = "#" + r + r + g + g + b + b
            pal.init(cols)

            sa.palette = pal

            sa.frame.init()
            self.tilesetSubroutine(sa.frame, self.file, addr)

            # print len(sa.frame.tiles)

            # size = len(ff.pixels)/4
            """for frm in range(4):
                cf = data.WeaponSpriteFrame()
                cf.init(8*8,8*8)
                cf.pixels = "".join([p[frm*64:(frm+1)*64] for p in ff.pixels])
                ws.frames.append(cf)"""

            sa.loaded = True

    def getBattleFloors(self, start, end):

        # for i,addr in enumerate(self.tables["sprites"]):
        for i in range(start, end+1):

            wf = self.data["battle_floors"][i]
            addr = self.tables["battle_floors"][i]

            col1 = self.getBytes(addr, 4)
            col2 = self.getBytes(addr+4, 2)
            cols = "042a0eee0000" + col1 + "042a" * 3 + col2 + "042a" * 7

            addr += 6

            frmOfs = h2i(self.getBytes(addr, 2))

            # print hex(addr), hex(frmOfs)

            wf.init()

            # -------

            acols = []
            for c in range(16):
                a, b, g, r = cols[c*4:c*4+4]
                acols.append("#" + r + r + g + g + b + b)
            wf.palette.init(acols)

            wf.frame.init()
            self.tilesetSubroutine(wf.frame, self.file, addr+frmOfs)

            wf.loaded = True

    def getBackgrounds(self, start, end):

        # for i,addr in enumerate(self.tables["sprites"]):
        for i in range(start, end+1):

            bk = self.data["backgrounds"][i]
            addr = self.tables["backgrounds"][i]

            frmOfs1 = h2i(self.getBytes(addr, 2))
            frmOfs2 = h2i(self.getBytes(addr+2, 2))
            myst = h2i(self.getBytes(addr+4, 2))
            addr += 6

            # print hex(addr)
            # print hex(frmOfs1), hex(frmOfs2)
            # print hex(frmOfs1+addr-6), hex(frmOfs2+addr+2-6)

            bk.init()

            # -------

            cols = self.getBytes(addr, 32)
            acols = []
            for c in range(16):
                a, b, g, r = cols[c*4:c*4+4]
                acols.append("#" + r + r + g + g + b + b)
            bk.myst = myst
            bk.palette.init(acols)
            addr -= 6

            bk.frame.init()
            self.tilesetSubroutine(bk.frame, self.file, [addr+frmOfs1, addr+2+frmOfs2])

            bk.loaded = True

    def getBattleSprites(self, start, end):

        # for i,addr in enumerate(self.tables["sprites"]):
        for i in range(start, end+1):

            bs = self.data["battle_sprites"][i]
            addr = self.tables["battle_sprites"][i]
            raw_bytes = self.getBytes(addr, 6)

            animSpd = h2i(self.getBytes(addr, 2))
            myst = self.getBytes(addr+2, 2)

            ofsPal = h2i(self.getBytes(addr+4, 2))
            palAddr = addr
            numFrms = ofsPal // 2 - 1
            addr += 6

            ofsFrms = []

            for n in range(numFrms):
                raw_bytes += self.getBytes(addr, 2)
                ofsFrms.append(addr+h2i(self.getBytes(addr, 2)))
                addr += 2

            numPals = (ofsFrms[0] - addr) // 32

            bs.init(animSpd, myst, numFrms, numPals)

            # -------

            pAddr = palAddr + ofsPal + 4
            for p in range(numPals):
                cols = self.getBytes(pAddr, 32)
                acols = []
                for c in range(16):
                    a, b, g, r = cols[c*4:c*4+4]
                    acols.append("#" + r + r + g + g + b + b)
                bs.palettes[p].init(acols)
                pAddr += 32

            raw_bytes += self.getBytes(addr, pAddr - addr)

            for f in range(len(ofsFrms)):

                bs.frames[f].init()
                """if i < 32:
                    bs.frames[f].init(12*8,12*8)
                else:
                    bs.frames[f].init(16*8,12*8)"""
                # bs.frames[f].init(12*8,12*8)
                # self.spriteSubroutine(bs.frames[f], self.file, ofsFrms[f])
                bs.frames[f] = self.tilesetSubroutine(bs.frames[f], self.file, ofsFrms[f])
                raw_bytes += bs.frames[f].raw_bytes

            bs.loaded = True
            bs.raw_bytes = raw_bytes

    def spriteSubroutine(self, sprite, source, addr=0):
        if type(addr) != type([]):
            pixels, raw_bytes = sprite.decompress(self, source, addr)
        else:
            pixels = ""
            raw_bytes = ""
            for a in addr:
                p, r = sprite.decompress(self, source, a)
                pixels += p
                raw_bytes += r

        sprite.raw_bytes = raw_bytes
        sprite.rearrangePixels(pixels, sprite.__class__ is data.Sprite)
        sprite.loaded = True
        return sprite

    def getMenuIcons(self, start, end):

        if start < self.values["num_menu_icons_unc"]:

            addr = h2i(self.getBytes(self.addresses["menu_icons_unc"], 4))

            for n in range(self.values["num_menu_icons_unc"]):

                if not self.data["menu_icons"][n].loaded and n >= start and n <= end:

                    pixels = ""

                    for i in range(18):
                        tile = self.uncompressedTileSubroutine(self.file, addr)
                        pixels += "".join(tile)
                        addr += 32

                    curIcon = self.data["menu_icons"][n]
                    curIcon.init(24, 24)
                    curIcon.direction = "h"
                    curIcon.rearrangePixels(pixels)
                    curIcon.loaded = True
                    curIcon.compressed = False

                addr += 32*18

        else:

            ofs = self.values["num_menu_icons_unc"]
            start -= ofs
            end -= ofs

            start = int(start // 4)
            end = int(end // 4)

            for idx in range(start, end+1):

                iconSet = self.tilesetSubroutine(data.Tileset(), self.file, self.tables["menu_icons"][idx])
                iconSet.iconIdxes = range(idx*4+ofs, idx*4+ofs+4)
                iconSet.loaded = True

                pixels = "".join([s.raw_pixels for s in iconSet.tiles])

                self.data["menu_icon_sets"][idx] = iconSet

                for j in range(4):

                    icon = self.data["menu_icons"][idx*4+j+ofs]
                    icon.init(24, 24)
                    icon.loaded = True

                    pixels1 = [pixels[i:i+8]+pixels[i+64:i+72]+pixels[i+128:i+136] for i in range((j*18+0)*64, (j*18+1)*64, 8)]
                    pixels2 = [pixels[i:i+8]+pixels[i+64:i+72]+pixels[i+128:i+136] for i in range((j*18+3)*64, (j*18+4)*64, 8)]
                    pixels3 = [pixels[i:i+8]+pixels[i+64:i+72]+pixels[i+128:i+136] for i in range((j*18+6)*64, (j*18+7)*64, 8)]
                    icon.pixels = pixels1+pixels2+pixels3
                    icon.raw_pixels = "".join(pixels1+pixels2+pixels3)

                    pixels1 = [pixels[i:i+8]+pixels[i+64:i+72]+pixels[i+128:i+136] for i in range((j*18+9)*64, (j*18+10)*64, 8)]
                    pixels2 = [pixels[i:i+8]+pixels[i+64:i+72]+pixels[i+128:i+136] for i in range((j*18+12)*64, (j*18+13)*64, 8)]
                    pixels3 = [pixels[i:i+8]+pixels[i+64:i+72]+pixels[i+128:i+136] for i in range((j*18+15)*64, (j*18+16)*64, 8)]
                    icon.pixels2 = pixels1+pixels2+pixels3
                    icon.raw_pixels2 = "".join(pixels1+pixels2+pixels3)

    def getTilesets(self, start, end):

        # for i,addr in enumerate(self.tables["sprites"]):
        for i in range(start, end+1):
            self.tilesetSubroutine(self.data["tilesets"][i], self.file, self.tables["tilesets"][i])

    def tilesetSubroutine(self, tileset, source, addr=0):

        tileset.init()

        if type(addr) != type([]):
            pixels, raw_bytes = tileset.decompress(self, source, addr)
        else:
            pixels = ""
            raw_bytes = ""
            for a in addr:
                p, r = tileset.decompress(self, source, a)
                pixels += p
                # print len(pixels)//64
                raw_bytes += r

        # pixels, raw_bytes = tileset.decompress(self, source, addr)

        """for p in range(len(pixels)//64):
            #print "Making tile %i... (%s)" % (tile_ctr, hex(0x3000 + tile_ctr*0x20))
            tile = data.Tile("Tile %i" % p, [pixels[i:i+8] for i in range(0, 64, 8)])
            pixels = pixels[64:]
            tileset.tiles.append(tile)"""

        tileset.setPixels(pixels)

        # tileset.cmdstr = cmd_str
        tileset.raw_bytes = raw_bytes
        # tileset.offset_strings = offset_strings

        tileset.loaded = True

        # print repr(raw_bytes)

        return tileset

    def getDialogue(self, bank):

        symbols = ""
        letters = ""

        line = (bank % 4) * 64
        num = min(64, [256, h2i("ab")][(bank//4) == 16] - line)

        # print repr(bank) + ", " + repr(line) + ", " + repr(num)
        # print repr(num)

        # num = 1
        # if not line:
        #     line = 1
        #     num = 255

        # D0, D1, D2, D3, D4, D5, D6, D7 = 0
        # A0, A1, A2, A3, A4, A5, A6, A7 = 0

        f = self.file

        addr_reader = 0

        # ------------------------------------

        b = bank

        ##print repr(b)
        # if b >= len(self.data["dialogue"]):
        #     self.data["dialogue"].append([])
        # else:
        #     self.data["dialogue"][b] = []

        curBank = self.data["dialogue"][b]
        curBank.init()

        for n in range(num):

            bank_addr = self.tables["dialogue"][b//4]

            ##print ' ' + repr(n)
            symbols = ""
            letters = ""

            linectr = 0
            addr_reader = bank_addr
            for linectr in range(line+n):
                skip = h2i(self.getBytes(addr_reader, 1)) + 1
                # debug(hex(addr_reader) + " + " + repr(skip)
                addr_reader += skip

            length = self.getBytes(addr_reader, 1)
            whole_barrel = length + ": "
            length = h2i(length)

            ##print repr(length)
            addr_reader += 1

            ##print hex(addr_reader)
        # ------------------------------------

            mem_slot_1 = 0
            mem_slot_2 = 0
            mem_slot_3 = h2i("FE")

            addr_string = addr_reader
            tree_length = 0
            symbol_ctr = 0
            symbol = ""

            cmd = False

            while symbol != "fe":

                # D6 = Huffman length (script)
                # D7 = Huffman barrel (script)
                huff_length = mem_slot_2
                huff_barrel = mem_slot_1

                # grab starting huffman tree
                huff_tree = (mem_slot_3 % 256) * 2

                # start of pointer table for trees
                addr_tree_ptrs_ptr = h2i("2E196")

                # debug("&&& " + hex(huff_tree) + " , " + hex(addr_tree_ptrs_ptr + huff_tree))

                # load tree offset
                huff_tree = h2i(self.getBytes(addr_tree_ptrs_ptr + huff_tree, 2))

                # debug("&&& " + hex(huff_tree))

                addr_tree_data_ptr = h2i("2E394") + huff_tree
                addr_tree_reader = addr_tree_data_ptr

                # debug("&&& " + hex(addr_tree_reader))

                tree_data = 0

                tree_length = 0
                symbol_offset = 0

                done = False

                # debug("&&& Starting...")

                while True:

                    while True:

                        tree_length -= 1
                        if tree_length == -1:
                            tree_length = 7
                            tree_data = h2i(self.getBytes(addr_tree_reader, 1))
                            ##print hex(addr_tree_reader) + " >>> Loading tree... " + hex(tree_data)
                            addr_tree_reader += 1

                        tree_data = util.add(tree_data, tree_data, 255)

                        # debug(hex(tree_length) + " " + hex(tree_data) + " " + hex(huff_length) + " " + hex(huff_barrel))

                        if util.carry:
                            done = True
                            # debug("FINISHED")
                            # debug("")
                            break

                        huff_length -= 1
                        if huff_length == -1:
                            huff_length = 7
                            huff_barrel = h2i(self.getBytes(addr_reader, 1))
                            whole_barrel += hex(huff_barrel)[2:].zfill(2) + " "
                            ##print ">>> Loading string..." + hex(huff_barrel)
                            addr_reader += 1

                        huff_barrel = util.add(huff_barrel, huff_barrel, 255)

                        # debug(hex(tree_length) + " " + hex(tree_data) + " " + hex(huff_length) + " " + hex(huff_barrel))

                        if util.carry:
                            # debug("BREAK 1 -- Skip left sub-tree")
                            # debug("")
                            break

                    symbol_ctr = 0

                    if done:
                        break

                    while True:

                        tree_length -= 1
                        if tree_length == -1:
                            tree_length = 7
                            tree_data = h2i(self.getBytes(addr_tree_reader, 1))
                            # debug(">>> Loading tree..." + hex(tree_data))
                            addr_tree_reader += 1

                        tree_data = util.add(tree_data, tree_data, 255)

                        # debug(hex(tree_length) + " " + hex(tree_data) + " " + hex(symbol_ctr) + " " + hex(symbol_offset))

                        if util.carry:
                            symbol_offset -= 1
                            symbol_ctr -= 1
                            if symbol_ctr == -1:
                                # debug("BREAK 2")
                                # debug("")
                                break
                        else:
                            symbol_ctr += 1

                        # debug(hex(tree_length) + " " + hex(tree_data) + " " + hex(symbol_ctr) + " " + hex(symbol_offset))

                # debug(hex(tree_length) + " " + hex(tree_data) + " " + hex(symbol_ctr) + " " + hex(symbol_offset))

                symbol = self.getBytes(addr_tree_data_ptr + symbol_offset - 1, 1)
                letter = ""

                symbols += symbol + " "

                if symbol != "fe":

                    if cmd:
                        letter = str(h2i(symbol)) + "}"
                        cmd = False

                    else:

                        if symbol == "fc" or symbol == "fd":
                            cmd = True
                        else:
                            cmd = False

                        if symbol in self.symTable:
                            letter = self.symTable[symbol[:]]

                        else:
                            letter = h2i(symbol)
                            if letter > 37:
                                letter += 6
                            if letter > 11:
                                letter += 6
                            else:
                                letter -= 1
                            letter += 47
                            if letter == 47:
                                letter = 32
                            try:
                                letter = chr(letter)
                            except:
                                # print symbol
                                pass
                            if letter == "6":
                                letter = " "

                            # debug(symbol)
                            # debug(hex(((h2i(symbol) - 1) << 5) + 0x29002))

                    letters += letter

                mem_slot_1 = huff_barrel
                mem_slot_2 = huff_length
                mem_slot_3 = h2i(symbol)

                # debug("-------------")

            textline = data.TextLine()
            textline.init(letters)
            textline.symbols = symbols
            textline.raw_bytes = whole_barrel
            textline.originalText = textline.text

            curBank.lines.append(textline)

            """found = False
            for token in ["_", "{LQUOT}", "{RQUOT}", "#", "%", "&", "+", "/", ":"]:
                p = textline.text.find(token)
                if p != -1 and textline.text[p-1] != "{" and textline.text[p+1] != "}":
                    print textline.text
                    found = True
            if found:
                f = open("misclines.txt", "a+")
                f.write("%i: %s\n" % (bank*64 + n, textline.text))
                f.flush()
                f.close()"""

            ##print hex(addr_string-1)[2:] + ": " + hex(b)[2:] + hex(line+n)[2:] + ": " + letters

        # print repr(len(curBank.lines))
        curBank.loaded = True

        # print ""

    def getOtherIcons(self):

        addr = h2i(self.getBytes(self.addresses["other_icons_ptr"], 4))

        for n in range(len(self.data["other_icons"])):

            pixels = ""

            for i in range(6):
                tile = self.uncompressedTileSubroutine(self.file, addr)
                pixels += "".join(tile)
                addr += 32

            curIcon = self.data["other_icons"][n]
            curIcon.init(16, 24)
            curIcon.direction = "h"
            curIcon.rearrangePixels(pixels, False)
            curIcon.loaded = True

    def uncompressedTileSubroutine(self, source, addr, width=8, height=8):

        func = self.getBytes

        pixels = []

        for row in range(height):
            pixels.append(func(addr, width//2))
            addr += width//2

        return pixels

    # -------------

    def getDataByName(self, subset, name):
        for d in self.data[subset]:
            if d.name and d.name.endswith(name):
                return d

    def getBytes(self, addr, num):
        ##print hex(addr)
        # raw_input()
        self.file.seek(addr)
        r = self.file.read(num)
        h = r.hex()
        ##print repr(h)
        return h

    def getPendingBytes(self, addr, num):

        r = self.curFileStr[addr:addr+num]
        h = r.hex()
        ##print repr(h)
        return h

    def writeBytes(self, addr, bytes_str, insert=False):

        # print hex(addr)
        # print hex(addr+len(bytes_str)//2)
        h = bytes.fromhex(bytes_str)

        # for i,c in enumerate(h):
        #     if c != self.curFileStr[addr+i]:
        #         print "different: " + c + " - " + self.curFileStr[addr+i]

        if insert:
            ofs = addr
        else:
            ofs = addr + len(h)

        self.curFileStr = self.curFileStr[:addr] + h + self.curFileStr[ofs:]

    # -----------------------

    def handleSpecialCases(self, sectionName):

        if sectionName == "palettes":

            self.tables["palettes"].append(h2i("309E"))

    def initTable(self, sectionName, entryLength=4):

        if sectionName in self.sectionData:

            self.tables[sectionName] = []

            data = self.sectionData[sectionName]
            addrs = data[1]
            lens = data[2]

            if type(addrs) != type([]):
                addrs = [addrs]
                lens = [lens]

            for i, d in enumerate(addrs):

                if not data[3]:
                    startAddr = h2i(self.getBytes(d, 4))
                else:
                    startAddr = d

                # if length:
                for v in range(lens[i]):
                    self.tables[sectionName].append(h2i(self.getBytes(startAddr + v * entryLength, entryLength)))

                """elif end:
                    token = ""
                    while token.lower() != end.lower():
                        if token:
                            self.tables[tableName].append(h2i(token))
                        token = self.getBytes(startAddr + v*bytes)[2:]"""

    def filterModified(self, section):
        return [data for data in section if data.modified]

    # ------------------------------

    def startWriteProcess(self, force=False):

        self.file.seek(0)

        if force or not hasattr(self, "curFileStr"):
            self.curFileStr = self.file.read()

    def reformDataSection(self, table, dataset=None, suppl=None):

        if suppl:
            last = suppl[-1]
        else:
            last = dataset[-1]

        spots = []
        for i, addr in enumerate(table):
            s = Spot()
            s.idx = i
            s.addr = addr
            spots.append(s)
        srt = sorted(spots)
        datas = []
        addr = srt[0].addr
        for i in range(len(srt)-1):
            l = srt[i+1].addr - srt[i].addr
            d = self.getBytes(addr, l)
            srt[i].data = d
            # print d
            addr += l

        if suppl:
            for i, s in enumerate(suppl):
                if s:
                    spots[i].data = s

        else:
            for i, s in enumerate(dataset):
                if s.modified:
                    newdata = s.raw_hexlify(rom=self)
                    spots[i].data = newdata

        # print repr(srt)

        if not srt[-1].data:
            if suppl:
                srt[-1].data = last
            else:
                srt[-1].data = None  # last.raw_hexlify(rom=self, dontprint=True)

        ptrstr = []
        datastr = []
        for i, s in enumerate(srt[:-1]):
            srt[i+1].addr = s.addr + len(s.data)//2
            datastr.append(s.data)
        datastr.append(srt[-1].data)
        # print repr(srt[-1].data)
        for i, s in enumerate(spots):
            ptrstr.append(hex(s.addr).split("x")[1].zfill(8))
        # self.writeBytes(0x220000, ptrstr + datastr)

        table = [s.addr for s in spots]

        return table, ptrstr, datastr

    def writeAllData(self):

        funcs = [
            self.writeDialogue,
            self.writeMenuIcons,
            self.writeFonts,
            self.writeTilesets,
            self.writePalettes,
            self.writeMaps,
            self.writeSprites,
            self.writeBattles,
            self.writeOtherIcons,
            self.writeBattleSprites,
            self.writePortraits,
            self.writeBackgrounds,
            # self.writeBattleFloors,
            # self.writeWeaponSprites,
        ]

        gens = []
        texts = []
        pieces = []

        self.startWriteProcess()

        for curFunc in funcs:

            gen = curFunc()
            gens.append(gen)

            texts.append(next(gen))
            pieces.append(next(gen))

        yield (texts, pieces)

        for i, curFunc in enumerate(funcs):

            gen = gens[i]

            result = next(gen)

            while result:

                yield result

                result = next(gen)

        yield None

        # self.hackery()

        self.finishWriteProcess()

        yield self.curFileStr

    def hackery(self):

        # halve stat up algos

        tAddr = 0x1ee02c
        fAddr = 0x1ee02d

        for thing in range(29*5):

            repl = self.getBytes(fAddr, 1)
            self.writeBytes(tAddr, repl)
            tAddr += 1
            fAddr += 2

    def writeDialogue(self):

        yield "dialogue/text banks"

        table = self.tables["dialogue"]
        banks = self.data["dialogue"]

        conglomeratedBanks = []
        for b in range(0, len(banks), 4):
            conglomeratedBanks.append([])
            for b2 in range(b, b+4):
                if banks[b2].loaded:
                    conglomeratedBanks[b//4] += banks[b2].lines

        bankModified = [len(self.filterModified(bank)) for bank in conglomeratedBanks]
        numModified = len(list(filter(lambda a: a > 0, bankModified)))

        yield numModified
        # yield len(conglomeratedBanks)

        if numModified:

            bankModified[-1] = 1

            for idx in range(len(conglomeratedBanks)):

                if bankModified[idx]:

                    bank = []

                    for i in range(4):
                        if not banks[idx*4+i].loaded:
                            yield "Filling in gaps for bank %i..." % idx
                            self.getDialogue(idx*4+i)
                        bank += self.data["dialogue"][idx*4+i].lines

                    # print [l.text for l in bank]

                    conglomeratedBanks[idx] = "00".join([l.raw_hexlify(self) for l in bank]) + "00"

                else:

                    conglomeratedBanks[idx] = ""

            """print conglomeratedBanks[1]
            gb = self.getBytes(table[1], table[2] - table[1])
            print gb
            print len(conglomeratedBanks[1]), len(gb)
            i = 0
            j = 0
            cnt = 0
            while i < len(conglomeratedBanks[0]):
                i += 1
                if conglomeratedBanks[0][j:i] != gb[j:i]:
                    #print cnt
                    #print conglomeratedBanks[0][j:i+1]
                    #print gb[j:i+1]
                    j = i
                    cnt += 1"""

            table, ptrstr, datastr = self.reformDataSection(table, suppl=conglomeratedBanks)
            ptrstr = "".join(ptrstr)
            datastr = "".join(datastr)
            datastr += "ff" * ((len(datastr)//2) % 2)

            gb2 = self.getBytes(0x28000, 4)

            """print len(datastr)
            print len(datastr)//2
            print gb2
            print hex(0x18009c + len(datastr)//2).split("x")[1].zfill(8)"""

            self.tables["dialogue"] = table
            self.writeBytes(0x18009c, datastr + ptrstr)
            self.writeBytes(0x28000, hex(0x18009c + len(datastr)//2).split("x")[1].zfill(8))

        """            yield (i+1) * 12.5

                #print "\n".join([l.text for l in bank])
                addr = self.tables["dialogue"][idx]

                yield "Constructing byte array for bank %i..." % idx

                bytes = [l.raw_hexlify(self)+"00" for l in bank]

                #for i,b in enumerate(bytes):
                #    if b != bank[i].raw_bytes:
                #        print repr(i)
                #        print b
                #        print bank[i].raw_bytes
                #        print ""
                yield 75

                bytes = "".join(bytes)

                yield "Writing byte array for bank %i..." % idx

                self.writeBytes(addr, bytes)

                yield "Moving on..."
        """

        yield None

    def writeMenuIcons(self):

        yield "menu icons"

        icons = self.data["menu_icons"]
        iconSets = self.data["menu_icon_sets"]
        setModified = [0]

        ofs = self.values["num_menu_icons_unc"]

        for i in range(ofs):
            if icons[i].modified:
                setModified[0] += 1

        for i, s in enumerate(iconSets):

            if not s.loaded:
                self.getMenuIcons(i*4+ofs, i*4+ofs)
                s = iconSets[i]
            s.icons = [icons[idx] for idx in s.iconIdxes]
            setModified.append(s.icons[0].modified or s.icons[1].modified or s.icons[2].modified or s.icons[3].modified)

        yield sum(setModified)
        # yield len(conglomeratedBanks)

        addr = h2i(self.getBytes(self.addresses["menu_icons_unc"], 4))

        for i in range(ofs):

            if icons[i].modified:

                yield "Constructing byte array for icon %i..." % i

                r1 = "".join(icons[i].raw_pixels) if isinstance(icons[i].raw_pixels, list) else icons[i].raw_pixels
                r2 = "".join(icons[i].raw_pixels2) if isinstance(icons[i].raw_pixels2, list) else icons[i].raw_pixels2
                bytes_data = r1 + r2

                yield 66

                yield "Writing byte array for icon %i..." % i

                self.writeBytes(addr, bytes_data)

                yield "Moving on..."

            addr += 32*18

        for idx in range(len(iconSets)):

            if setModified[idx+1]:

                yield "Transforming pixel arrays for icon set %i..." % idx

                iconSets[idx].tiles = []

                for t in iconSets[idx].icons:

                    for pixels in [t.pixels, t.pixels2]:

                        for row in range(3):

                            tile1 = data.Tile("")
                            tile1.init([pixels[i][0:8] for i in range(row*8, row*8+8)])
                            tile2 = data.Tile("")
                            tile2.init([pixels[i][8:16] for i in range(row*8, row*8+8)])
                            tile3 = data.Tile("")
                            tile3.init([pixels[i][16:24] for i in range(row*8, row*8+8)])
                            iconSets[idx].tiles.append(tile1)
                            iconSets[idx].tiles.append(tile2)
                            iconSets[idx].tiles.append(tile3)

                addr = self.tables["menu_icons"][idx]

                yield 33

                yield "Constructing byte array for icon set %i..." % idx

                bytes_data = iconSets[idx].raw_hexlify()

                yield 66

                yield "Writing byte array for icon set %i..." % idx

                self.writeBytes(addr, bytes_data)

                yield "Moving on..."

        yield None

    def writeFonts(self):

        yield "fonts"

        fonts = self.data["fonts"]
        fontModified = [f.modified for f in fonts]

        yield sum(fontModified)
        # yield len(conglomeratedBanks)

        for idx in range(len(fonts)):

            if fontModified[idx]:

                bytes_data = "".join([fonts[idx].glyphs[g].raw_hexlify() for g in self.fontOrder])

                addr = self.addresses["text_font"]

                yield "Writing byte array for dialogue font..."

                self.writeBytes(addr, bytes_data)

                yield "Moving on..."

        yield None

    def writeTilesets(self):

        yield "tilesets"

        table = self.tables["tilesets"]
        dataset = self.data["tilesets"]
        tilesetsModified = [t.modified for t in dataset]

        yield sum(tilesetsModified)
        # yield len(conglomeratedBanks)

        if sum(tilesetsModified):

            table, ptrstr, datastr = self.reformDataSection(table, dataset)
            ptrstr = "".join(ptrstr)
            for i, d in enumerate(datastr):
                if d is None:
                    self.getTilesets(i, i)
                    datastr[i] = dataset[i].raw_hexlify(rom=self)
            datastr = "".join(datastr)
            self.tables["tilesets"] = table
            self.writeBytes(0x6400c, ptrstr + datastr)

        """for idx in range(len(tilesets)):

            if tilesetsModified[idx]:

                yield "Constructing byte array for tileset %i..." % idx

                bytes_data = tilesets[idx].raw_hexlify()

                yield 50

                addr = self.tables["tilesets"][idx]

                yield "Writing byte array for tileset %i..." % idx

                self.writeBytes(addr, bytes_data)

                yield "Moving on..." """

        yield None

    def writePalettes(self):

        yield "palettes"

        palettes = self.data["palettes"]
        palettesModified = [p.modified for p in palettes]

        yield sum(palettesModified)
        # yield len(conglomeratedBanks)

        for idx in range(len(palettes)):

            if palettesModified[idx]:

                yield "Constructing byte array for palette %i..." % idx

                bytes_data = palettes[idx].raw_hexlify()

                yield 50

                addr = self.tables["palettes"][idx]

                yield "Writing byte array for palette %i..." % idx

                self.writeBytes(addr, bytes_data)

                yield "Moving on..."

        yield None

    def writeSprites(self):

        yield "character sprites"

        dataset = self.data["sprites"]
        table = self.tables["sprites"]
        spritesModified = [s.modified for s in dataset]

        yield sum(spritesModified)
        # yield len(conglomeratedBanks)

        # ----------------------
        # flexible test

        if sum(spritesModified):

            table, ptrstr, datastr = self.reformDataSection(table, dataset)
            ptrstr = "".join(ptrstr)
            for i, d in enumerate(datastr):
                if d is None:
                    self.getSprites(i, i)
                    datastr[i] = dataset[i].raw_hexlify(rom=self)
            datastr = "".join(datastr)
            self.tables["sprites"] = table
            self.writeBytes(0x220000, ptrstr + datastr)

        # ----------------------

        """for idx in range(len(sprites)):

            if spritesModified[idx]:

                yield "Constructing byte array for sprite %i..." % idx

                bytes_data = sprites[idx].raw_hexlify()

                yield 50

                addr = self.tables["sprites"][idx]

                yield "Writing byte array for sprite %i..." % idx

                #print repr(bytes_data)
                #print repr(sprites[idx].raw_bytes)

                self.writeBytes(addr, bytes_data)

                yield "Moving on..." """

        yield None

    def writeMaps(self):

        yield "maps"

        table = self.tables["maps"]
        dataset = self.data["maps"]
        mapsModified = [m.modified for m in dataset]

        yield sum(mapsModified)
        # yield len(conglomeratedBanks)

        if sum(mapsModified):

            for idx in range(len(dataset)):
                if mapsModified[idx]:
                    dataset[idx].reorderByBlock()

            table, ptrstr, datastr = self.reformDataSection(table, dataset)
            for i, d in enumerate(datastr):
                if d is None:
                    self.getMaps(i, i)
                    datastr[i] = dataset[i].raw_hexlify(rom=self)

            for j, d in enumerate(datastr):
                subptr = [d[i:i+8] for i in range(12, 8*10+12, 8)]
                oldofs = self.tables["maps"][j]
                newofs = int(ptrstr[j], 16)
                for i, s in enumerate(subptr):
                    if s != "ffffffff":
                        subptr[i] = hex(int(s, 16) - oldofs + newofs).split("x")[1].zfill(8)
                subptr = "".join(subptr)
                datastr[j] = datastr[j][:12] + subptr + datastr[j][12+len(subptr):]

            # print [hex(i).split("x")[1].zfill(8) for i in self.tables["maps"]]
            # print ptrstr

            self.tables["maps"] = table

            ptrstr = "".join(ptrstr)
            datastr = "".join(datastr)

            self.writeBytes(0x380000, ptrstr + datastr)

        """ for idx in range(len(maps)):

            if mapsModified[idx]:

                yield "Storing map %i's basic properties..." % idx

                map = self.data["maps"][idx]
                addr = self.tables["maps"][idx]
                bytes_data = "".join(["%02x" % s for s in [map.paletteIdx]+map.tilesetIdxes])

                self.writeBytes(addr, bytes_data)

                yield 10

                yield "Recreating map %i in correct order..." % idx

                maps[idx].reorderByBlock()

                yield 20

                yield "Constructing byte array for map %i..." % idx

                blockBytes, layoutBytes = maps[idx].raw_hexlify()

                yield 40

                addr = maps[idx].sectionAddrs[0]

                yield "Writing block byte array for map %i..." % idx

                self.writeBytes(addr, blockBytes)

                yield 60

                addr = maps[idx].sectionAddrs[1]

                yield "Writing layout byte array for map %i..." % idx

                #print repr(bytes_data)
                #print repr(sprites[idx].raw_bytes)

                self.writeBytes(addr, layoutBytes)

                yield 80

                yield "Writing event data for map %i..." % idx

                areaBytes = "".join([d.hexlify() for d in maps[idx].areas])
                copyFlagBytes = "".join([d.hexlify() for d in maps[idx].copies if d.copyType == 0]) + "ffff"
                copyPermBytes = "".join([d.hexlify() for d in maps[idx].copies if d.copyType == 1]) + "ffff"
                copyTempBytes = "".join([d.hexlify() for d in maps[idx].copies if d.copyType == 2]) + "ffff"
                warpBytes = "".join([d.hexlify() for d in maps[idx].warps])
                chestBytes = "".join([d.hexlify() for d in maps[idx].items if d.isChest])
                nonChestBytes = "".join([d.hexlify() for d in maps[idx].items if not d.isChest])
                animBytes = "".join([d.hexlify() for d in maps[idx].anims])

                self.writeBytes(maps[idx].sectionAddrs[2], areaBytes)
                self.writeBytes(maps[idx].sectionAddrs[3], copyFlagBytes)
                self.writeBytes(maps[idx].sectionAddrs[4], copyPermBytes)
                self.writeBytes(maps[idx].sectionAddrs[5], copyTempBytes)
                self.writeBytes(maps[idx].sectionAddrs[6], warpBytes)
                self.writeBytes(maps[idx].sectionAddrs[7], chestBytes)
                self.writeBytes(maps[idx].sectionAddrs[8], nonChestBytes)
                self.writeBytes(maps[idx].sectionAddrs[9], animBytes)

                yield "Moving on..." """

        yield None

    def writeBattles(self):

        yield "battle data"

        battles = self.data["battles"]
        dataset = battles
        tp = self.addresses["battle_terrain_ptrs"]
        table = [int(self.getBytes(tp+i*4, 4), 16) for i in range(len(dataset))]
        battlesModified = [b.modified for b in battles]

        yield sum(battlesModified)
        # yield len(conglomeratedBanks)

        if sum(battlesModified):

            terrain = [b.terrain for b in dataset]
            for i in range(len(terrain)):
                if terrain[i]:
                    terrain[i] = terrain[i].raw_hexlify()

            table, ptrstr, datastr = self.reformDataSection(table, suppl=terrain)
            for i, d in enumerate(datastr):
                if d is None:
                    self.getBattles(i, i)
                    datastr[i] = dataset[i].terrain.raw_hexlify(rom=self)

            # print repr([len(str(t)) for t in terrain])

            ptrstr = "".join(ptrstr)
            datastr = "".join(datastr)

            self.writeBytes(0xe0000, ptrstr + datastr)

            # -------------

            table = self.tables["battles"]

            table, ptrstr, datastr = self.reformDataSection(table, dataset)
            ptrstr = "".join(ptrstr)
            for i, d in enumerate(datastr):
                if d is None:
                    self.getBattles(i, i)
                    datastr[i] = dataset[i].raw_hexlify(rom=self)
            datastr = "".join(datastr)
            self.tables["battles"] = table
            self.writeBytes(0x200000, ptrstr + datastr)

        for idx in range(len(battles)):

            if battlesModified[idx]:

                yield "Updating boss table..."

                addr = self.addresses["battle_boss_flags"] + idx

                self.writeBytes(addr, ["00", "ff"][battles[idx].boss])

                yield 10

                # ----

                if battles[idx].npcs:

                    yield "Updating NPCs..."

                    addr = self.addresses["battle_npcs"]
                    bytes_data = "".join([npc.raw_hexlify() for npc in battles[idx].npcs]) + "ffff"

                    npcBatIdx = h2i(self.getBytes(addr, 2))
                    addr += 2

                    while npcBatIdx < idx:

                        next_ = self.getBytes(addr, 2)
                        while next_ != "ffff":
                            addr += 8
                            next_ = self.getBytes(addr, 2)
                        addr += 2
                        npcBatIdx = h2i(self.getBytes(addr, 2))
                        addr += 2

                    self.writeBytes(addr, bytes_data)

                yield 30

                # ----

                yield "Updating battle camera range..."

                addr = self.addresses["battle_map_info"] + idx * 7

                bytes_data = hex(battles[idx].map_index)[2:].zfill(2)
                bytes_data += hex(battles[idx].map_x1)[2:].zfill(2)
                bytes_data += hex(battles[idx].map_y1)[2:].zfill(2)
                bytes_data += hex(battles[idx].map_x2 - battles[idx].map_x1)[2:].zfill(2)
                bytes_data += hex(battles[idx].map_y2 - battles[idx].map_y1)[2:].zfill(2)

                self.writeBytes(addr, bytes_data)

                yield 50

                # ----

                yield "Moving on..."

        yield None

    def writeOtherIcons(self):
        yield "item/spell icons"

        icons = self.data["other_icons"]
        iconModified = [icon for icon in icons if icon.modified]
        yield len(iconModified)

        addr = h2i(self.getBytes(self.addresses["other_icons_ptr"], 4))

        for idx in range(len(icons)):
            # Получаем raw_pixels как строку (даже если это список)
            raw_pixels = icons[idx].raw_pixels
            if isinstance(raw_pixels, list):
                raw_str = "".join(raw_pixels)
            else:
                raw_str = raw_pixels

            if icons[idx].modified:
                yield "Constructing byte array for icon set %i..." % idx
                bytes_data = raw_str
                yield 50
                yield "Writing byte array for icon set %i..." % idx
                self.writeBytes(addr, bytes_data)
                yield "Moving on..."

            # Смещаем адрес на длину данных иконки (в байтах)
            addr += len(raw_str) // 2

        yield None

    def writeBattleSprites(self):

        yield "battle sprites"

        num_allies, num_enemies = self.sectionData["battle_sprites"][2]
        idxlist = [0, num_allies, num_enemies]
        loclist = [0x2e0000, 0x270000]

        bsModified = [t.modified for t in self.data["battle_sprites"]]

        yield sum(bsModified)

        for s in [0, 1]:

            start = idxlist[s]
            end = idxlist[s+1] + start

            table = self.tables["battle_sprites"][start:end]
            dataset = self.data["battle_sprites"][start:end]

            bsModified = [t.modified for t in dataset]

            if sum(bsModified):

                table, ptrstr, datastr = self.reformDataSection(table, dataset)
                ptrstr = "".join(ptrstr)
                for i, d in enumerate(datastr):
                    if d is None:
                        self.getBattleSprites(i+start, i+start)
                        datastr[i] = dataset[i].raw_hexlify(rom=self)

                datastr = "".join(datastr)
                self.tables["battle_sprites"][start:end] = table

                self.writeBytes(loclist[s], ptrstr + datastr)

        yield None

    def writePortraits(self):

        yield "portraits"

        table = self.tables["portraits"]
        dataset = self.data["portraits"]
        portraitsModified = [t.modified for t in dataset]

        yield sum(portraitsModified)
        # yield len(conglomeratedBanks)

        if sum(portraitsModified):

            table, ptrstr, datastr = self.reformDataSection(table, dataset)
            ptrstr = "".join(ptrstr)
            for i, d in enumerate(datastr):
                if d is None:
                    self.getPortraits(i, i)
                    datastr[i] = dataset[i].raw_hexlify(rom=self)
            datastr = "".join(datastr)
            self.tables["portraits"] = table
            self.writeBytes(0x360000, ptrstr + datastr)

        yield None

    def writeBackgrounds(self):

        yield "backgrounds"

        table = self.tables["backgrounds"]
        dataset = self.data["backgrounds"]
        backgroundsModified = [t.modified for t in dataset]

        yield sum(backgroundsModified)
        # yield len(conglomeratedBanks)

        if sum(backgroundsModified):

            table, ptrstr, datastr = self.reformDataSection(table, dataset)
            ptrstr = "".join(ptrstr)
            for i, d in enumerate(datastr):
                if d is None:
                    self.getBackgrounds(i, i)
                    datastr[i] = dataset[i].raw_hexlify(rom=self)
            datastr = "".join(datastr)
            self.tables["backgrounds"] = table
            self.writeBytes(0x320000, ptrstr + datastr)

        yield None

    def writeBattleFloors(self):    # BROKEN

        yield "battle floors"

        table = self.tables["battle_floors"]
        dataset = self.data["battle_floors"]
        floorsModified = [t.modified for t in dataset]

        yield sum(floorsModified)
        # yield len(conglomeratedBanks)

        if sum(floorsModified):

            table, ptrstr, datastr = self.reformDataSection(table, dataset)
            ofs = len([d for d in datastr if d != ""])*8+2 - 8
            ofsList = []
            ptrstr = "".join(ptrstr)
            for i, d in enumerate(datastr):
                ofsList.append(ofs)
                if d is None:
                    self.getBattleFloors(i, i)
                    datastr[i] = dataset[i].raw_hexlify(rom=self)
                ofs += len(datastr[i])//2
                # print datastr[i]
            datastr = "".join(datastr)
            # print [hex(o) for o in ofsList]
            self.tables["battle_floors"] = table
            self.writeBytes(0x30000, ptrstr + datastr)

        yield None

    # -------------------------

    def finishWriteProcess(self):

        for b in self.data["dialogue"]:
            if b.loaded:
                for l in b.lines:
                    if hasattr(l, "originalText"):
                        l.originalText = l.text

    def massModify(self, modified=True):

        for k in self.data.keys():
            for v in self.data[k]:

                if hasattr(v, "modified"):
                    v.modified = modified

                if hasattr(v, "massModify"):
                    v.massModify(modified)

    def close(self):
        self.file.close()
        del self.data

    # ------------------------------

    symTable = {"40": "_",
                "41": "-",
                "42": ".",
                "43": ",",
                "44": "!",
                "45": "?",
                "46": "{LQUOT}",
                "47": "{RQUOT}",
                "48": "'",
                "49": "(",
                "4a": ")",
                "4b": "#",
                "4c": "%",
                "4d": "&",
                "4e": "+",
                "4f": "/",
                "50": ":",

                "ee": "{DICT}",
                "ef": "{N}",

                "f1": "{#}",
                "f2": "{NAME}",
                "f3": "{LEADER}",
                "f4": "{ITEM}",
                "f5": "{SPELL}",
                "f6": "{CLASS}",

                "f7": "{W2}",
                "f8": "{D1}",
                "f9": "{D3}",
                "f0": "{D2}",
                "fa": "{W1}",
                "fb": "{CLEAR}",

                "fc": "{NAME;",
                "fd": "{COLOR;",

                "fe": ""}


class Spot(object):
    def __init__(self):
        self.idx = None
        self.addr = None
        self.data = None

    def __lt__(self, other):
        if self.addr != other.addr:
            return self.addr < other.addr
        return self.idx < other.idx

    def __eq__(self, other):
        return self.addr == other.addr and self.idx == other.idx

    def __repr__(self):
        return "(%i, %x, %s)" % (self.idx, self.addr, self.data is not None)