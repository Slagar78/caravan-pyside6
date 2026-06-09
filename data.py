import sys
sys.path.append("plugins/data")
sys.path.append("plugins/dialogs")

import math
import binascii
import compress
from PySide6.QtWidgets import QApplication
from util import *

symTable = {" ": "01",
            "_": "40",
            "-": "41",
            ".": "42",
            ",": "43",
            "!": "44",
            "?": "45",
            "{LQUOT}": "46",
            "{RQUOT}": "47",
            "'": "48",
            "(": "49",
            ")": "4a",
            "#": "4b",
            "%": "4c",
            "&": "4d",
            "+": "4e",
            "/": "4f",
            ":": "50",
            "{DICT}": "ee",
            "{N}": "ef",
            "{#}": "f1",
            "{NAME}": "f2",
            "{LEADER}": "f3",
            "{ITEM}": "f4",
            "{SPELL}": "f5",
            "{CLASS}": "f6",
            "{W2}": "f7",
            "{D1}": "f8",
            "{D3}": "f9",
            "{D2}": "f0",
            "{W1}": "fa",
            "{CLEAR}": "fb",
            # "fc" : pull a party member's name out, see below
            # "fd" : a font color, see below
            }

class DataObject(object):
    namePattern = None
    entriesPerEntry = 1
    entriesPerGroup = 1

    def __init__(self, *args, **kwargs):
        self.name = None
        if "name" in kwargs:
            self.name = kwargs["name"]
        self.modified = False
        self.loaded = False
        self.hasCustomName = False
        self.args = args
        for k, v in kwargs.items():
            self.__dict__[k] = v

    def raw_hexlify(self, *args, **kwargs):
        all = self.hexlify(*args, **kwargs)
        if isinstance(all, (list, tuple)):
            rtr = [h.strip().replace("\n","").replace(" ","").replace(":","") for h in all]
        else:
            rtr = all.strip().replace("\n","").replace(" ","").replace(":","")
        return rtr

    def massModify(self, modified=True):
        for k, v in self.__dict__.items():
            if isinstance(v, list):
                for sub in v:
                    if hasattr(sub, "modified"):
                        sub.modified = modified
            elif isinstance(v, dict):
                for sub in v.keys():
                    if hasattr(v[sub], "modified"):
                        v[sub].modified = modified
            elif hasattr(v, "massModify"):
                v.massModify(modified)
            elif hasattr(v, "modified"):
                v.modified = modified

    def setIndexedName(self, string):
        if self.name:
            loc = self.name.find(": ")
            if loc != -1:
                self.name = self.name[:loc+2] + string
        else:
            self.name = string

    def getIndexedName(self):
        loc = self.name.find(": ")
        if loc != -1:
            return self.name[loc+2:]
        return self.name


class Battle(DataObject):
    namePattern = "Battle %i"

    def init(self, force=None, enemies=None, regions=None, points=None):
        if force is None: force = []
        if enemies is None: enemies = []
        if regions is None: regions = []
        if points is None: points = []
        self.force = force
        self.enemies = enemies
        self.regions = regions
        self.points = points
        self.npcs = []
        self.terrain = None

    def hexlify(self, *args, **kwargs):
        h = ""
        h += hex(len(self.force))[2:].zfill(2)
        h += hex(len(self.enemies))[2:].zfill(2)
        h += hex(len(self.regions))[2:].zfill(2)
        h += hex(len(self.points))[2:].zfill(2)
        h += "\n".join([f.hexlify() for f in self.force])
        h += "\n".join([f.hexlify(True) for f in self.enemies])
        h += "\n".join([f.hexlify() for f in self.regions])
        h += "\n".join([hex(f[0])[2:].zfill(2)+hex(f[1])[2:].zfill(2) for f in self.points])
        return h


class BattleUnit(DataObject):
    def init(self, idx, x, y):
        self.idx = idx
        self.x = x
        self.y = y
        self.ai = [0, [255, 15], [255, 15]]
        self.item = 0x7f
        self.itemBroken = False
        self.misc1 = False
        self.reinforce = False
        self.respawn = False
        self.rest = ""

    def hexlify(self, enemy=False):
        minus = 0
        if enemy:
            minus = 64
        h = hex(self.idx-minus)[2:].zfill(2)
        h += hex(self.x)[2:].zfill(2)
        h += hex(self.y)[2:].zfill(2)
        h += hex(self.ai[0])[2:].zfill(2)
        h += ["00", "80"][self.itemBroken]
        h += hex(self.item)[2:].zfill(2)
        h += hex(self.ai[1][0])[2:].zfill(2) + hex(self.ai[1][1])[2:].zfill(2)
        h += hex(self.ai[2][0])[2:].zfill(2) + hex(self.ai[2][1])[2:].zfill(2)
        misc1 = 0
        misc1 |= self.misc1 * 96
        misc2 = 0
        misc2 |= self.reinforce * 2
        misc2 |= self.respawn * 1
        h += hex(misc1)[2:].zfill(2) + hex(misc2)[2:].zfill(2)
        return h


class BattleNPC(DataObject):
    def init(self, idx, x, y, facing=3, script=h2i("451e0")):
        self.idx = idx
        self.x = x
        self.y = y
        self.facing = facing
        self.script = script

    def hexlify(self, *args, **kwargs):
        h = hex(self.x)[2:].zfill(2) + hex(self.y)[2:].zfill(2) + hex(self.facing)[2:].zfill(2) + hex(self.idx)[2:].zfill(2)
        h += hex(self.script)[2:].zfill(8)
        return h


class BattleRegion(DataObject):
    namePattern = "Region %i"

    def init(self, type, p1, p2, p3, p4):
        self.type = type
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3
        self.p4 = p4

    def hexlify(self, *args, **kwargs):
        type = hex(self.type)[2:].zfill(2)
        p1 = hex(self.p1[0])[2:].zfill(2) + hex(self.p1[1])[2:].zfill(2)
        p2 = hex(self.p2[0])[2:].zfill(2) + hex(self.p2[1])[2:].zfill(2)
        p3 = hex(self.p3[0])[2:].zfill(2) + hex(self.p3[1])[2:].zfill(2)
        p4 = hex(self.p4[0])[2:].zfill(2) + hex(self.p4[1])[2:].zfill(2)
        return "%s00%s%s%s%s0000" % (type, p1, p2, p3, p4)


class Palette(DataObject):
    namePattern = "Palette %i"

    def init(self, colors=None):
        if colors is None: colors = []
        self.colors = colors
        self.isMapPalette = False

    def rgbaTuples(self):
        t = []
        for i, p in enumerate(self.colors):
            t.append((int(p[1], 16)*17, int(p[3], 16)*17, int(p[5], 16)*17, [0,255][i>0]))
        return t

    def hexlify(self, *args, **kwargs):
        return ' '.join(["0" + c[5] + c[3] + c[1] for c in self.colors])
        
class Map(DataObject):
    namePattern = "Map %i"

    def init(self, paletteIdx=0, tilesetIdxes=None, sectionAddrs=None, setupAddrs=None):
        if tilesetIdxes is None: tilesetIdxes = []
        if sectionAddrs is None: sectionAddrs = []
        if setupAddrs is None: setupAddrs = []
        self.paletteIdx = paletteIdx
        self.tilesetIdxes = tilesetIdxes[:]
        self.sectionAddrs = sectionAddrs[:]
        self.sectionLengths = []
        self.setupAddrs = setupAddrs[:]

    def reorderByBlock(self):
        repl = {}
        highest = 2
        blockIdxes = [b & 0x3ff for b in self.layoutData]
        newBlocks = self.blocks[:3]
        used = [0,1,2]
        for i, idx in enumerate(blockIdxes):
            if idx not in used:
                highest += 1
                repl[idx] = highest
                used.append(idx)
                newBlocks.append(self.blocks[idx])
        for i, idx in enumerate(blockIdxes):
            if idx > 2:
                blockIdxes[i] = repl[idx]
        self.layoutData = [self.layoutData[i] & 0xfc00 | blockIdxes[i] for i in range(len(self.layoutData))]
        self.blocks = newBlocks + [b for b in self.blocks if b not in newBlocks]

    def hexlify(self, addr=None, inp=False, **kwargs):
        # -------------------
        # block data hexlify
        done = 0
        bits = ""
        sets = {}
        lastWord = 0
        allTiles = []
        for b in self.blocks:
            allTiles += b.tileIdxes
        done = 27
        bits += bin(len(allTiles)-27, 14)

        while done < len(allTiles):
            add = ""
            next = allTiles[done]
            pos = 0xff2000 + done*2
            top = next & 0x9800
            bottom = next & 0x03ff
            lofs = (allTiles[done-1] & 0x7ff) * 2 + (allTiles[done-1] & 0x800)
            uofs = (allTiles[done-3] & 0x7ff) * 2 + (allTiles[done-3] & 0x800) + 0x1000
            adjOfs = -((next & 0x800) // 0x800 * 2 - 1)

            if next == allTiles[done-1]:
                add += "00"
                desc = "copy left tile"
                done += 1
            elif next == allTiles[done-1] + adjOfs:
                add += "01"
                desc = "copy left tile %s 1" % ["","+","-"][adjOfs]
                done += 1
            elif lofs in sets and sets[lofs] == next:
                add += "100"
                desc = "copy from left set"
                done += 1
            elif uofs in sets and sets[uofs] == next:
                add += "101"
                desc = "copy from upper set"
                done += 1
            else:
                add += "11"
                desc = "customize: "
                if done > 0 and top == allTiles[done-1] & 0x9800:
                    add += "0 "
                    desc += "copy left bitmask, "
                else:
                    add += "1 %i%i%i " % (int(top&0x8000)//0x8000, int(top&0x1000)//0x1000, int(top&0x0800)//0x0800)
                    desc += "custom bitmask, "
                if done > 0 and abs(bottom - (allTiles[done-1] & 0x07ff)) < 32:
                    dist = bottom - (allTiles[done-1] & 0x7ff)
                    negate = dist <= 0
                    desc += "left value %s %i" % (["+","-"][negate], abs(dist))
                    add += "0 %s %i" % (bin(abs(dist), 5), negate)
                else:
                    desc += "custom value"
                    comp = (bottom - 0x100 + 0x180) // 2
                    big = comp > 0x180
                    extra = bottom - (comp * 2 - 0x80)
                    if big:
                        add += "1 %s" % bin(comp, 9)
                        add += " %i" % extra
                    else:
                        add += "1 %s" % bin(bottom - 0x100, 9)
                done += 1
                ofs1 = (allTiles[done-2] & 0x03ff) * 2 + (allTiles[done-2] & 0x0800)
                ofs2 = (allTiles[done-4] & 0x03ff) * 2 + (allTiles[done-4] & 0x0800) + 0x1000
                sets[ofs1] = next
                sets[ofs2] = next

            bits += add.replace(" ","")
            if len(bits) > lastWord*16+15:
                lastWord = len(bits) // 16
            # (опущены отладочные печати)
        if len(bits) % 16:
            bits += "0" * (16 - (len(bits) % 16))
        blockStr = "".join([hex(int(bits[i:i+4], 2))[2:] for i in range(0, len(bits), 4)])

        # -------------------
        # map data hexlify
        done = 0
        bits = ""
        highest = 2
        lminis = {}
        uminis = {}
        lastWord = 0

        while done < 64*64:
            next = self.layoutData[done]
            pos = 0xff0000 + done*2
            xpos = done % 64
            ypos = done // 64
            top = next & 0xfc00
            bottom = next & 0x03ff
            add = ""
            desc = ""
            leftSame = 0
            topSame = 0
            leftList = None
            topList = None

            if done > 0 and (self.layoutData[done-1] & 0x3ff) in lminis:
                leftList = lminis[self.layoutData[done-1] & 0x3ff]
            if done > 63 and (self.layoutData[done-64] & 0x3ff) in uminis:
                topList = uminis[self.layoutData[done-64] & 0x3ff]
            if done > 0 and done < 64 and not topList:
                topList = uminis.get(0)

            didCopy = False

            # подсчёт одинаковых блоков слева и сверху
            if done > 0:
                while done+leftSame < 64*64 and self.layoutData[done+leftSame] == self.layoutData[done-1]:
                    leftSame += 1
            if done > 63:
                while done+topSame < 64*64 and self.layoutData[done-64+topSame] == self.layoutData[done+topSame]:
                    topSame += 1

            if leftSame or topSame:
                if leftSame >= topSame:
                    add += "01 "
                    size = int(math.log(leftSame, 2))
                    add += "0" * size + "1 "
                    add += bin(leftSame - (2 ** size), size) + " 1"
                    desc = "copy left %i times." % leftSame
                    done += leftSame
                    didCopy = True
                else:
                    add += "01 "
                    size = int(math.log(topSame, 2))
                    add += "0" * size + "1 "
                    add += bin(topSame - (2 ** size), size) + " 0"
                    desc = "copy top %i times." % topSame
                    done += topSame
                    didCopy = True
            elif leftList and next in leftList:
                add += "10"
                idx = leftList.index(next)
                if len(leftList) > 1:
                    add += " " + idx * "0"
                    if idx < len(leftList)-1:
                        add += "1"
                desc = "left stack's (%s) idx#%i" % (repr([hex(n)[2:] for n in leftList]), idx)
                done += 1
            elif topList and next in topList:
                if leftList:
                    add += "1"
                add += "10"
                idx = topList.index(next)
                if len(topList) > 1:
                    add += " " + idx * "0"
                    if idx < len(topList)-1:
                        add += "1"
                desc = "top stack's (%s) idx#%i" % (repr([hex(n)[2:] for n in topList]), idx)
                done += 1
            elif bottom == highest+1:
                add += "00 "
                desc = "add next incrementally, "
                highest += 1
                if top == 0xc000 or top == 0x0000:
                    add += "0 %i" % (top // 0xc000)
                elif top == 0x8000 or top == 0x4000:
                    add += "1 0 %i" % ((top // 0x4000) - 1)
                else:
                    add += "1 1 %s" % bin(top, 16)[:6]
                done += 1
            else:
                add += "1"
                desc = "custom idx"
                if topList:
                    add += "1"
                if leftList:
                    add += "1"
                size = int(math.log(highest, 2))+1
                add += " " + bin(bottom, size) + " "
                if top == 0xc000 or top == 0x0000:
                    add += "0 %i" % (top // 0xc000)
                elif top == 0x8000 or top == 0x4000:
                    add += "1 0 %i" % ((top // 0x4000) - 1)
                else:
                    add += "1 1 %s" % bin(top, 16)[:6]
                done += 1

            bits += add.replace(" ","")
            if len(bits) > lastWord*16+15:
                lastWord = len(bits) // 16
                # отладочный вывод пропущен

            if not didCopy:
                blk = next
                if done > 1:
                    last = self.layoutData[done-2] & 0x3ff
                else:
                    last = 0
                if last not in lminis:
                    lminis[last] = []
                if len(lminis[last]) == 0 or lminis[last][0] != blk:
                    lminis[last].insert(0, blk)
                    if lminis[last].count(blk) > 1:
                        lminis[last].pop(lminis[last].index(blk, 1))
                    lminis[last] = lminis[last][:4]

                if done > 64:
                    last = self.layoutData[done-65] & 0x3ff
                else:
                    last = 0
                if last not in uminis:
                    uminis[last] = []
                if len(uminis[last]) == 0 or uminis[last][0] != blk:
                    uminis[last].insert(0, blk)
                    if uminis[last].count(blk) > 1:
                        uminis[last].pop(uminis[last].index(blk, 1))
                    uminis[last] = uminis[last][:4]

        if len(bits) % 16:
            bits += "0" * (16 - (len(bits) % 16))
        layoutStr = "".join([hex(int(bits[i:i+4], 2))[2:] for i in range(0, len(bits), 4)])

        # --------
        beforestr = "%02x" % self.paletteIdx
        beforestr += "".join(["%02x" % i for i in self.tilesetIdxes])

        areaBytes = "".join([d.hexlify() for d in self.areas]) + "ffff"
        copyFlagBytes = "".join([d.hexlify() for d in self.copies if d.copyType == 0]) + "ffff"
        copyPermBytes = "".join([d.hexlify() for d in self.copies if d.copyType == 1]) + "ffff"
        copyTempBytes = "".join([d.hexlify() for d in self.copies if d.copyType == 2]) + "ffff"
        warpBytes = "".join([d.hexlify() for d in self.warps]) + "ffff"
        chestBytes = "".join([d.hexlify() for d in self.items if d.isChest]) + "ffff"
        nonChestBytes = "".join([d.hexlify() for d in self.items if not d.isChest]) + "ffff"
        animBytes = "".join([d.hexlify() for d in self.anims]) + "ffff"
        if self.animTSIdx is not None:
            animBytes = "%04x" % self.animTSIdx + "%04x" % self.animCopyLen + animBytes

        # change ptrs
        table = self.sectionAddrs[:]
        datalist = [blockStr, layoutStr, areaBytes, copyFlagBytes, copyPermBytes, copyTempBytes, warpBytes, chestBytes, nonChestBytes, animBytes]

        for i in range(9, -1, -1):
            if self.sectionAddrs[i] is None:
                table.pop(i)
                datalist.pop(i)

        inttable, table, datalist = kwargs["rom"].reformDataSection(table, suppl=datalist)

        for i in range(10):
            if self.sectionAddrs[i] is None:
                table.insert(i, "ffffffff")
                datalist.insert(i, "")

        return beforestr + "".join(table) + "".join(datalist)

    animCopyLen = property(lambda self: max(a.end for a in self.anims))


class Sprite(DataObject):
    namePattern = "Sprite %i"
    entriesPerGroup = 3
    decompress = compress.basicDecompression
    direction = "v"

    def init(self, width, height, pixels=None, pixels2=None):
        if pixels is None: pixels = []
        if pixels2 is None: pixels2 = []
        self.width = width
        self.height = height
        self.pixels = pixels
        self.pixels2 = pixels2
        self.raw_pixels = pixels
        self.raw_pixels2 = pixels2
        self.commands = {}
        self.compressed = True

    def rearrangePixels(self, pixels, twoFrames=True):
        tileWidth = self.width // 8
        tileHeight = self.height // 8
        numTiles = tileWidth * tileHeight
        if not twoFrames and len(pixels) % (self.width * 8):
            pixels += "0" * ((self.width * 8) - (len(pixels) % (self.width * 8)))

        if twoFrames:
            self.raw_pixels = pixels[:len(pixels)//2]
            self.raw_pixels2 = pixels[len(pixels)//2:]
        else:
            self.raw_pixels = pixels[:]
            self.raw_pixels2 = ""

        if self.direction == "v":
            row = range(0, tileWidth)
            col = range(0, numTiles, tileWidth)
        else:
            row = range(0, numTiles, tileWidth)
            col = range(0, tileWidth)

        pixels1 = ["".join([pixels[(i+j)*64 : (i+j+1)*64] for j in row]) for i in col]
        if twoFrames:
            pixels = pixels[len(pixels)//2:]
            pixels2 = ["".join([pixels[(i+j)*64 : (i+j+1)*64] for j in row]) for i in col]
        self.pixels = ["".join([tile[i:i+8] for tile in pixels1]) for i in range(0, 64 * tileHeight, 8)]
        if twoFrames:
            self.pixels2 = ["".join([tile[i:i+8] for tile in pixels2]) for i in range(0, 64 * tileHeight, 8)]

    def convertFromPixelRows(self, rows):
        rowlen = len(rows[0])
        pixels = []
        if self.direction == "h":
            for i in range(0, len(rows), 8):
                tilerow = "".join(["".join([rows[j][pos:pos+8] for j in range(i, i+8)]) for pos in range(0, rowlen, 8)])
                pixels.append(tilerow)
        else:
            for i in range(0, len(rows[0]), 8):
                tilerow = "".join([rows[j][i:i+8] for j in range(len(rows))])
                pixels.append(tilerow)
        return pixels

    def hexlify(self, debug=False, **kwargs):
        # ФИКС ДЛЯ ВТОРОГО КАДРА
        if not hasattr(self, 'raw_pixels') or self.raw_pixels is None:
            self.raw_pixels = ""
        if not hasattr(self, 'raw_pixels2') or self.raw_pixels2 is None:
            self.raw_pixels2 = ""

        # Правильно соединяем оба кадра
        frame1 = "".join(self.raw_pixels) if isinstance(self.raw_pixels, list) else self.raw_pixels
        frame2 = "".join(self.raw_pixels2) if isinstance(self.raw_pixels2, list) else self.raw_pixels2

        pixels = frame1 + frame2

        pixels = " ".join([pixels[i:i+4] for i in range(0, len(pixels), 4)]) + " xxxx "
        if pixels == " xxxx ":
            return "ffffffff"

        code = ""
        barrel = ""
        short_pat = ""
        long_pat = ""
        last_short = ""
        last_long = ""
        sub = 0
        ins = 0
        lastpos = 0
        skip = False

        for pos in range(0, len(pixels), 5):
            lastcode = code[:]
            token = pixels[pos:pos+5]
            long_pat += token
            if not short_pat:
                short_pat += token
            temp_pat = (((len(long_pat) - len(short_pat)) // len(short_pat)) + 2) * short_pat
            if temp_pat.find(long_pat) == -1:
                short_pat = long_pat
            found_short = pixels[:sub].rfind(short_pat)
            found_long = pixels[:sub].rfind(long_pat)
            dist_short = (sub - found_short)
            dist_long = (sub - found_long)
            does_repeat = (short_pat * ((sub - found_short) // len(short_pat) + 1)).find(pixels[found_short:sub]) == 0
            possible_short = (found_short != -1) and (dist_short <= len(short_pat) or does_repeat)
            possible_long = (found_long != -1)

            if (not possible_short and not possible_long) or len(long_pat) > 33*5:
                if len(long_pat) == 5:
                    short_pat = ""
                    long_pat = ""
                    code += token
                    barrel += "0"
                    sub = pos+5
                elif len(long_pat) == 10:
                    code += long_pat[:5]
                    barrel += "0"
                    short_pat = token
                    long_pat = token
                    sub = pos
                else:
                    reverted = False
                    if (not possible_short and not possible_long) or len(long_pat) > 33*5:
                        reverted = True
                        short_pat = last_short
                        long_pat = last_long
                        found_short = pixels[:sub].rfind(short_pat)
                        found_long = pixels[:sub].rfind(long_pat)
                        dist_short = (sub - found_short)
                        dist_long = (sub - found_long)
                        possible_short = (found_short != -1) and dist_short <= len(short_pat)
                        possible_long = (found_long != -1)
                    repeat = (len(long_pat) // 10) * 2
                    repeat -= ((len(long_pat) // 5) + 1) % 2
                    if possible_short:
                        offset = (dist_short // 5 * 2) * 16
                    elif possible_long:
                        offset = (dist_long // 5 * 2) * 16
                    else:
                        pass
                    repeat = 32 - repeat
                    cmd = hex(offset + repeat)[2:].zfill(4)
                    code += cmd + " "
                    barrel += "1"
                    short_pat = token * reverted
                    long_pat = token * reverted
                    sub = pos
            else:
                pass

            if len(barrel) >= 16:
                extra = barrel[16:]
                barrel = "".join([hex(int(barrel[s:s+4], 2))[2:] for s in range(0,16,4)])
                code = code[:ins] + barrel + ": " + code[ins:]
                barrel = extra
                ins += 86
                code = code[:ins] + "\n" + code[ins:]
                ins += 1

            last_short = short_pat
            last_long = long_pat
            if lastcode != code:
                lastpos = pos
            QApplication.processEvents()

        barrel += "1"
        while len(barrel) < 16:
            barrel += "0"
        code += "0000"
        code = code[:ins] + barrel + ": " + code[ins:]
        barrel = extra if 'extra' in locals() else ""
        ins += 86
        code = code[:ins] + "\n" + code[ins:]
        ins += 1
        if len(barrel):
            while len(barrel) < 16:
                barrel += "0"
            barrel = "".join([hex(int(barrel[s:s+4], 2))[2:] for s in range(0,16,4)])
            code = code[:ins] + barrel + " " + code[ins:]

        return code

class MenuIcon(Sprite):
    namePattern = "Menu Icon %i"
    entriesPerGroup = 1

class OtherIcon(Sprite):
    namePattern = "Item/Spell Icon %i"
    entriesPerGroup = 1


class Tileset(DataObject):
    namePattern = "Tileset %i"
    decompress = compress.stackDecompression
    # pixels property остаётся прежним
    pixels = property(lambda self: "".join([t.hexlify() for t in self.tiles]))

    def init(self, tiles=None):
        if tiles is None: tiles = []
        self.tiles = tiles[:]

    def setPixels(self, pixels):
        self.tiles = []
        for p in range(len(pixels)//64):
            idx = p*64
            tile = Tile("Tile %i" % p)
            pix = [pixels[idx+i:idx+i+8] for i in range(0, 64, 8)]
            tile.init(pix)
            tile.raw_pixels = pixels[idx:idx+64]
            self.tiles.append(tile)

    def convertFromPixelRows(self, rows):
        rowlen = len(rows[0])
        self.tiles = []
        for i in range(0, len(rows), 8):
            tilerow = [[rows[j][pos:pos+8] for j in range(i, i+8)] for pos in range(0, rowlen, 8)]
            tiles = [Tile("Tile %i" % (j+len(self.tiles))) for j in range(rowlen//8)]
            [tiles[j].init(tilerow[j]) for j in range(len(tilerow))]
            self.tiles += tiles

    def getPixelRows(self, tw, th):
        pixels = []
        order = self.getTileOrder(tw, th)
        tiles = [self.tiles[t] for t in order]
        for tRow in range(12):
            for pRow in range(8):
                row = "".join([tiles[tRow*tw+to].pixels[pRow] for to in range(tw)])
                pixels.append(row)
        return pixels

    def getTileOrder(self, tw, th):
        return range(tw * th)

        # продолжение класса Tileset
    def hexlify(self, debug=False, **kwargs):
        pixels = " ".join([self.pixels[i:i+4] for i in range(0, len(self.pixels), 4)]) + " xxxx "
        code = ""
        barrel = ""
        short_pat = ""
        long_pat = ""
        sub = 0
        ins = 0
        pixels_to_encode = ""
        commands = []
        pixel_stack = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f"]
        max_offset = 2048 * 5 // 2

        for pos in range(0, len(pixels)+2, 5):
            token = pixels[pos:pos+5]
            if token != "":
                long_pat += token
                if not short_pat:
                    short_pat += token
                temp_pat = (((len(long_pat) - len(short_pat)) // len(short_pat)) + 2) * short_pat
                if temp_pat.find(long_pat) == -1:
                    short_pat = long_pat
                found_short = pixels[:sub].rfind(short_pat)
                found_long = pixels[:sub].rfind(long_pat)
                dist_short = (sub - found_short)
                dist_long = (sub - found_long)
                possible_short = (found_short != -1) and dist_short <= len(short_pat)
                possible_long = (found_long != -1)

                if (not possible_short and not possible_long) or pos+5 >= len(pixels) or (dist_short > max_offset or dist_long > max_offset):
                    if len(long_pat) == 5:
                        short_pat = ""
                        long_pat = ""
                        barrel += "0"
                        sub = pos+5
                        pixels_to_encode += token
                    elif len(long_pat) == 10:
                        barrel += "0"
                        pixels_to_encode += long_pat[:5]
                        short_pat = token
                        long_pat = token
                        sub = pos
                    else:
                        # revert to last good pattern
                        short_pat = last_short
                        long_pat = last_long
                        found_short = pixels[:sub].rfind(short_pat)
                        found_long = pixels[:sub].rfind(long_pat)
                        dist_short = (sub - found_short)
                        dist_long = (sub - found_long)
                        possible_short = (found_short != -1) and dist_short <= len(short_pat)
                        possible_long = (found_long != -1)
                        repeat = (len(long_pat) // 10) * 2 + 1
                        repeat -= ((len(long_pat) // 5) + 1) % 2
                        if possible_short:
                            offset = (dist_short // 5 * 2)
                        elif possible_long:
                            offset = (dist_long // 5 * 2)
                        else:
                            # impossible, should not happen
                            pass
                        barrel += "1"
                        commands.append((offset, repeat, long_pat, sub))
                        short_pat = token
                        long_pat = token
                        sub = pos
            else:
                # end of pixels
                barrel += "1"
                while len(barrel) < 16:
                    barrel += "0"
                commands.append((0,0,0,0))

            if len(barrel) >= 16 or token == "":
                extra = barrel[16:]
                barrelbits = barrel
                barrel = "".join([hex(int(barrel[s:s+4], 2))[2:] for s in range(0,16,4)])
                # encode main barrel
                for d in barrel:
                    if d == "8":
                        cmd = "1110"
                    elif d == "4":
                        cmd = "110"
                    elif d == "2":
                        cmd = "101"
                    elif d == "1":
                        cmd = "100"
                    elif d == "0":
                        cmd = "0"
                    else:
                        cmd = "1111" + bin(int(d, 16), 4)
                    code += cmd

                # process barrel bits
                barrelbits = barrelbits.replace(" ","")
                for b in barrelbits:
                    if b == "0":
                        # raw pixels
                        pix = pixels_to_encode[:4]
                        for p in pix:
                            idx = pixel_stack.index(p)
                            if idx == 0: cmd = "00"
                            elif idx == 1: cmd = "01"
                            elif idx == 2: cmd = "100"
                            elif idx == 3: cmd = "101"
                            elif idx == 4: cmd = "110"
                            elif idx == 5: cmd = "11100"
                            elif idx == 6: cmd = "11101"
                            elif idx == 7: cmd = "11110"
                            elif idx == 8: cmd = "1111100"
                            elif idx == 9: cmd = "1111101"
                            elif idx == 10: cmd = "1111110"
                            elif idx == 11: cmd = "111111100"
                            elif idx == 12: cmd = "111111101"
                            elif idx == 13: cmd = "111111110"
                            elif idx == 14: cmd = "1111111110"
                            elif idx == 15: cmd = "1111111111"
                            else:
                                # error
                                return ""
                            pixel_stack.insert(0, pixel_stack.pop(idx))
                            code += cmd
                        pixels_to_encode = pixels_to_encode[5:]
                    else:
                        (offset, repeat, pat, curpos) = commands.pop(0)
                        offset //= 2
                        offset_code = bin(offset, 11).zfill(11)
                        repeat_code = (repeat-2) * "0" + "1"
                        code += offset_code
                        code += repeat_code
                barrel = extra
                # optional debug output removed

            last_short = short_pat
            last_long = long_pat
            QApplication.processEvents()

        # final hexcode
        hexcode = " ".join(["".join([hex(int(code[s:s+4].zfill(4), 2))[2:] for s in range(i,i+16,4)]) for i in range(0, len(code), 16)])
        return hexcode


class Tile(DataObject):
    def init(self, pixels=None):
        if pixels is None: pixels = []
        self.pixels = pixels

    def hexlify(self, *args, **kwargs):
        return "".join([p for p in self.pixels])

    def setPixel(self, x, y, color, frame=0):
        self.pixels[y] = self.pixels[y][:x] + color + self.pixels[y][x+1:]


class TextBank(DataObject):
    namePattern = "Text Bank %i"
    entriesPerEntry = 4

    def init(self, lines=None):
        if lines is None: lines = []
        self.lines = lines[:]

    def hexlify(self, *args, **kwargs):
        pass


class TextLine(DataObject):
    def init(self, text):
        self.text = text
        self.broken = False

    def hexlify(self, rom, check=False):
        def asc2sf2(val):
            global symTable
            n = ""
            args = val[1:-1].split(";")
            if val in "0123456789":
                n = hex(ord(val)-46)[2:].zfill(2)
            elif val in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                n = hex(ord(val)-53)[2:].zfill(2)
            elif val in "abcdefghijklmnopqrstuvwxyz":
                n = hex(ord(val)-59)[2:].zfill(2)
            elif val in symTable:
                n = symTable[val]
            elif len(args) == 2 and args[1].isdigit():
                if args[0] == "NAME":
                    n = "fc" + hex(int(args[1]))[2:].zfill(2)
                elif args[0] == "COLOR":
                    n = "fd" + hex(int(args[1]))[2:].zfill(2)
                else:
                    self.broken = True
            else:
                self.broken = True
            return n

        getBytes = rom.getBytes
        db = False
        self.broken = False
        f = rom.file

        addr_reader = 0
        last_symbol = "fe"
        addr_tree_ptrs_ptr = h2i("2E196")
        string = self.text
        substr = ""
        symbols = ""

        for i, c in enumerate(string):
            if c == "}":
                substr += c
                symbols += asc2sf2(substr)
                substr = ""
            elif c == "{" or substr != "":
                substr += c
                if i == len(string)-1:
                    self.broken = True
            else:
                symbols += asc2sf2(c)

        symbols += "fe"

        barrel_string = ""
        tree_string = ""
        cur_tree_string = ""

        for i in range(len(symbols)//2):
            tree_ptr = h2i("2E394") + h2i(getBytes(addr_tree_ptrs_ptr + h2i(last_symbol) * 2, 2))
            current_symbol = symbols[i*2:i*2+2]
            tree_reader = tree_ptr
            symbol_reader = tree_ptr
            symbol_offset = 0
            cur_tree_string = ""
            tree_desc = 0

            while symbol_offset == 0:
                symbol_reader -= 1
                b = getBytes(symbol_reader, 1)
                if b == current_symbol:
                    symbol_offset = tree_ptr - symbol_reader

            index = 0
            tree_div = 0
            path = []
            passed = 0
            cur_str = ""
            just_popped = 0
            tree_num_possible = 1

            while passed < symbol_offset:
                if tree_div == 0:
                    tree_desc = h2i(getBytes(tree_reader, 1).zfill(2))
                    tree_reader += 1
                    tree_div = 128

                direct = (tree_desc // tree_div) % 2
                cur_str += repr(direct)

                if direct == 0:
                    path.append(0)
                    tree_num_possible += 1
                else:
                    passed += 1
                    if passed == symbol_offset:
                        break
                    elif check and passed >= tree_num_possible:
                        self.broken = True
                        return "IMPOSSIBLE STRING -- Works up to at least:\n" + string[:i]
                    if path and path[-1] == 1:
                        while path and path[-1] == 1:
                            path.pop()
                        if path:
                            path[-1] = 1
                    if path:
                        path[-1] = 1
                    else:
                        path.append(1)
                tree_div //= 2

            tree_string += ''.join([repr(c) for c in path])

            while len(tree_string) >= 8:
                barrel_string += hex(int(tree_string[:8], 2))[2:].zfill(2) + " "
                tree_string = tree_string[8:]

            last_symbol = current_symbol

        if tree_string:
            while len(tree_string) < 8:
                tree_string += "0"
            barrel_string += hex(int(tree_string[:8], 2))[2:].zfill(2) + " "

        return hex(len(barrel_string)//3+1)[2:].zfill(2) + ": " + barrel_string


class Font(DataObject):
    def init(self, glyphs=None):
        if glyphs is None: glyphs = {}
        self.glyphs = glyphs

    def hexlify(self, *args, **kwargs):
        pass


class Block(DataObject):
    def init(self, tileIdxes=None, tiles=None):
        if tileIdxes is None: tileIdxes = []
        if tiles is None: tiles = []
        self.tileIdxes = tileIdxes
        self.tiles = tiles
        self.pixels = []

    def createPixelArray(self):
        self.pixels = []
        if len(self.tiles) == 9:
            for row in range(24):
                startTile = row // 8 * 3
                pr = ""
                for tile in range(startTile, startTile+3):
                    idx = row % 8
                    if self.tileIdxes[tile] & 0x1000:
                        idx = 7 - idx
                    if self.tileIdxes[tile] & 0x0800:
                        pr += "".join([a for a in reversed(self.tiles[tile].pixels[idx])])
                    else:
                        pr += self.tiles[tile].pixels[idx]
                    if self.tileIdxes[tile] & 0x8000:
                        for p in range((tile%3) * 8, (tile%3) * 8 + 8):
                            if not (p + row*2) % 4:
                                pr = pr[:p] + "0" + pr[p+1:]
                self.pixels.append(pr)

    def hexlify(self, *args, **kwargs):
        pass

    tilesetIdxes = property(lambda self: [v // 0x80 - 2 for v in self.tileIdxes])
    uniqueTilesetIdxes = property(lambda self: sorted([v for (i,v) in enumerate(self.tilesetIdxes) if i - self.tilesetIdxes.index(v) == 0]))


class FontGlyph(DataObject):
    def init(self, width, pixels):
        self.width = width
        self.height = 15
        self.pixels = pixels

    def setPixel(self, x, y, color, frame=0):
        self.pixels[y] = self.pixels[y][:x] + color + self.pixels[y][x+1:]

    def recalculateWidth(self):
        self.width = max(0, *[p.rfind("1") for p in self.pixels])

    def hexlify(self, *args, **kwargs):
        s = "000%s " % hex(self.width)[2:] + " ".join(["".join([hex(int(r[i:i+4], 2))[2:] for i in range(0,16,4)]) for r in self.pixels])
        return s


class Background(DataObject):
    namePattern = "Background %i"

    def init(self):
        self.frame = BackgroundFrame()
        self.palette = Palette()

    def hexlify(self, *args, **kwargs):
        f1 = BackgroundFrame()
        f2 = BackgroundFrame()
        f1.init()
        f2.init()
        f1.tiles = self.frame.tiles[:192]
        f2.tiles = self.frame.tiles[192:]

        f1b = f1.raw_hexlify(kwargs["rom"])
        f2b = f2.raw_hexlify(kwargs["rom"])

        raw_bytes = ""
        raw_bytes += "0026"
        raw_bytes += "%04x" % (len(f1b) // 2 + 0x24)
        raw_bytes += "%04x" % self.myst
        raw_bytes += self.palette.raw_hexlify()
        raw_bytes += f1b
        raw_bytes += f2b
        return raw_bytes


class BackgroundFrame(Tileset):
    namePattern = "Background Frame %i"
    entriesPerGroup = 1
    decompress = compress.stackDecompression
    direction = "h"

    def getTileOrder(self, tw, th):
        return [a*16 + b + c*th*4 + d*4 for a in range(th//4) for b in range(4) for c in range(tw//4) for d in range(4)]


class BattleFloor(DataObject):
    namePattern = "Battle Floor %i"

    def init(self):
        self.frame = BattleFloorFrame()
        self.palette = Palette()

    def hexlify(self, *args, **kwargs):
        c1 = self.palette.colors[3]
        c2 = self.palette.colors[4]
        c3 = self.palette.colors[8]
        raw_bytes = ""
        raw_bytes += "0" + c1[5] + c1[3] + c1[1]
        raw_bytes += "0" + c2[5] + c2[3] + c2[1]
        raw_bytes += "0" + c3[5] + c3[3] + c3[1]
        raw_bytes += "0000"
        raw_bytes += self.frame.raw_hexlify(kwargs["rom"])
        return raw_bytes


class BattleFloorFrame(Tileset):
    namePattern = "Battle Floor Frame %i"
    entriesPerGroup = 1
    decompress = compress.stackDecompression
    direction = "h"

    def getTileOrder(self, tw, th):
        return [a + b*th for a in range(th) for b in range(tw)]

    def rearrangePixels(self, pixels):
        new_pixels = [""]*32
        for n in range(0, len(pixels), 8):
            row3 = (n//8) % 32
            new_pixels[row3] += pixels[n:n+8]
        self.pixels = new_pixels


class Portrait(DataObject):
    namePattern = "Portrait %i"

    def init(self):
        self.frame = PortraitFrame()
        self.palette = Palette()

    def hexlify(self, *args, **kwargs):
        raw_bytes = ""
        raw_bytes += self.eyeBytes
        raw_bytes += self.mouthBytes
        raw_bytes += self.palette.raw_hexlify()
        raw_bytes += self.frame.raw_hexlify(kwargs["rom"])
        return raw_bytes


class PortraitFrame(Tileset):
    namePattern = "Portrait Frame %i"
    entriesPerGroup = 1
    decompress = compress.stackDecompression
    direction = "h"


class BattleSprite(DataObject):
    namePattern = "Battle Sprite %i"

    def init(self, animSpd, myst, numFrames, numPalettes):
        self.animSpeed = animSpd
        self.myst = myst
        self.frames = []
        for n in range(numFrames):
            self.frames.append(BattleSpriteFrame())
        self.palettes = []
        for n in range(numPalettes):
            self.palettes.append(Palette())

    def hexlify(self, *args, **kwargs):
        len_palettes = len(self.palettes)
        len_frame_ptrs = len(self.frames) * 2
        raw_bytes = ""
        raw_bytes += "%04x" % self.animSpeed
        raw_bytes += self.myst
        raw_bytes += "%04x" % (len_frame_ptrs + 2)

        palette_data = "".join([p.raw_hexlify() for p in self.palettes])
        frame_data = ""
        for i, f in enumerate(self.frames):
            raw_bytes += "%04x" % (len_frame_ptrs - i*2 + len(frame_data)//2 + len(palette_data)//2)
            frame_data += f.raw_hexlify(kwargs["rom"])

        raw_bytes += palette_data + frame_data
        return raw_bytes


class BattleSpriteFrame(Tileset):
    namePattern = "Battle Sprite Frame %i"
    entriesPerGroup = 1
    decompress = compress.stackDecompression
    direction = "h"

    def getTileOrder(self, tw, th):
        return [a*16 + b + c*th*4 + d*4 for a in range(th//4) for b in range(4) for c in range(tw//4) for d in range(4)]


class WeaponSprite(DataObject):
    namePattern = "Weapon Sprite %i"

    def init(self):
        self.frames = []
        self.palettes = []

    def hexlify(self, *args, **kwargs):
        raw_bytes = ""
        for f in self.frames:
            raw_bytes += Tileset.hexlify(f)
        return raw_bytes


class WeaponSpriteFrame(Tileset):
    namePattern = "Weapon Sprite Frame %i"
    entriesPerGroup = 1
    decompress = compress.stackDecompression
    direction = "h"

    def getTileOrder(self, tw, th):
        return [a*16 + b + c*th*4 + d*4 for a in range(th//4) for b in range(4) for c in range(tw//4) for d in range(4)]

    def rearrangePixels(self, pixels):
        new_pixels = [""]*64
        for n in range(0, len(pixels), 8):
            row3 = (n//8) % 8
            row2 = (n//64) % 4
            row1 = (n//256//4) % 2
            new_pixels[row1*32 + row2*8 + row3] += pixels[n:n+8]
        self.pixels = new_pixels


class SpellAnimation(DataObject):
    namePattern = "Spell Animation %i"

    def init(self):
        self.frame = SpellAnimationFrame()
        self.palette = Palette()

    def hexlify(self, *args, **kwargs):
        raw_bytes = ""
        for f in self.frames:
            raw_bytes += Tileset.hexlify(f)
        return raw_bytes


class SpellAnimationFrame(Tileset):
    namePattern = "Spell Animation Frame %i"
    entriesPerGroup = 1
    decompress = compress.stackDecompression
    direction = "h"

    def getTileOrder(self, tw, th):
        return range(len(self.tiles))

    def rearrangePixels(self, pixels):
        Sprite.rearrangePixels(self, pixels, False)


class Item(DataObject):
    namePattern = "Item %i"


class Music(DataObject):
    namePattern = "Music %i"


class MapSetup(DataObject):
    namePattern = "Map Setup %i"

    def init(self, flag, sectionIdxes=None):
        if sectionIdxes is None: sectionIdxes = []
        self.flag = flag
        self.sectionIdxes = sectionIdxes[:]


class MapArea(DataObject):
    namePattern = "Area %i"

    def init(self, l1x1, l1y1, l1x2, l1y2, l2x, l2y, l1xp, l1yp, l2xp, l2yp, l1xs, l1ys, l2xs, l2ys, layerType, music):
        self.l1x1 = l1x1
        self.l1y1 = l1y1
        self.l1x2 = l1x2
        self.l1y2 = l1y2
        self.l2x = l2x
        self.l2y = l2y
        self.l2xp = l2xp
        self.l2yp = l2yp
        self.l1xp = l1xp
        self.l1yp = l1yp
        self.l2xs = l2xs
        self.l2ys = l2ys
        self.l1xs = l1xs
        self.l1ys = l1ys
        self.layerType = layerType
        self.music = music
        self.hasLayer2 = not (self.l2x == 0 and self.l2y == 0)

    def hexlify(self, *args, **kwargs):
        st = ""
        st += "%04x" % self.l1x1
        st += "%04x" % self.l1y1
        st += "%04x" % self.l1x2
        st += "%04x" % self.l1y2

        l2x = [0, self.l2x][self.hasLayer2]
        l2y = [0, self.l2y][self.hasLayer2]

        if self.layerType == 0:
            st += "%04x" % l2x
            st += "%04x" % l2y
            st += "00000000"
            st += "%04x" % self.l2xp
            st += "%04x" % self.l2yp
            st += "%04x" % self.l1xp
            st += "%04x" % self.l1yp
            st += "%02x" % (self.l2xs % 256)
            st += "%02x" % (self.l2ys % 256)
            st += "%02x" % (self.l1xs % 256)
            st += "%02x" % (self.l1ys % 256)
        else:
            st += "00000000"
            st += "%04x" % l2x
            st += "%04x" % l2y
            st += "%04x" % self.l1xp
            st += "%04x" % self.l1yp
            st += "%04x" % self.l2xp
            st += "%04x" % self.l2yp
            st += "%02x" % (self.l1xs % 256)
            st += "%02x" % (self.l1ys % 256)
            st += "%02x" % (self.l2xs % 256)
            st += "%02x" % (self.l2ys % 256)

        st += "%02x" % self.layerType
        st += "%02x" % self.music
        return st


class MapBlockCopy(DataObject):
    namePattern = "Block Copy %i"

    def init(self, stepx, stepy, srcx, srcy, width, height, destx, desty, copyType):
        self.x = stepx
        self.y = stepy
        self.flag = 0
        self.srcx = srcx
        self.srcy = srcy
        self.width = width
        self.height = height
        self.destx = destx
        self.desty = desty
        self.copyBlank = (self.srcx > 64) or (self.srcy > 64)
        self.copyType = copyType

    def hexlify(self, *args, **kwargs):
        st = ""
        if self.copyType == 0:
            st += "%04x" % self.flag
        else:
            st += "%02x" % self.x
            st += "%02x" % self.y
        if self.copyBlank:
            st += "ffff"
        else:
            st += "%02x" % self.srcx
            st += "%02x" % self.srcy
        st += "%02x" % self.width
        st += "%02x" % self.height
        st += "%02x" % self.destx
        st += "%02x" % self.desty
        return st


class MapWarp(DataObject):
    namePattern = "Warp %i"

    def init(self, x, y, destmap, destx, desty, destfacing, mystery):
        self.x = x % 64
        self.y = y % 64
        self.destmap = destmap
        self.destx = destx % 64
        self.desty = desty % 64
        self.destfacing = destfacing
        self.mystery = mystery
        self.sameX = x == 255
        self.sameY = y == 255
        self.sameDestX = destx == 255
        self.sameDestY = desty == 255
        self.sameMap = destmap == 255

    def hexlify(self, *args, **kwargs):
        st = ""
        st += "%02x" % [self.x, 255][self.sameX]
        st += "%02x" % [self.y, 255][self.sameY]
        st += "%04x" % [self.destmap, 255][self.sameMap]
        st += "%02x" % [self.destx, 255][self.sameDestX]
        st += "%02x" % [self.desty, 255][self.sameDestY]
        st += "%02x" % self.destfacing
        st += "%02x" % self.mystery
        return st


class MapItem(DataObject):
    namePattern = "Map Item %i"

    def init(self, x, y, flag, itemIdx, isChest):
        self.x = x
        self.y = y
        self.flag = flag
        self.itemIdx = itemIdx
        self.isChest = isChest

    def hexlify(self, *args, **kwargs):
        st = ""
        st += "%02x" % self.x
        st += "%02x" % self.y
        st += "%02x" % self.flag
        st += "%02x" % self.itemIdx
        return st


class MapAnim(DataObject):
    namePattern = "Animation %i"

    def init(self, start, end, dest, delay):
        self.start = start
        self.end = end
        self.dest = dest
        self.delay = delay

    def hexlify(self, *args, **kwargs):
        st = ""
        st += "%04x" % self.start
        st += "%04x" % (self.end - self.start)
        st += "%04x" % self.dest
        st += "%04x" % self.delay
        return st