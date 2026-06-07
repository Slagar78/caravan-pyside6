import asm
import util
import time
import pickle


def loadProject(filename):
    try:
        with open(filename, "rb") as f:
            proj = pickle.load(f)
    except EOFError:
        proj = None
    return proj


class Project(object):
    def __init__(self, name):
        self.name = name
        self.layout = ROMLayout()
        self.layout.init()
        self.cache = True
        self.version = 1


class ROMLayout(object):
    def __init__(self):
        self.maxInstLen = 20

    def init(self):
        self.initSections()

    def initSections(self):
        self.sections = []
        self.offsets = {}
        self.counters = {
            "Data": 1,
            "Code": 1,
            "Jump Table": 1,
            "Padding": 1,
            "Inaccessible": 1,
        }
        self.addNewSection("Header", "Data", 0, 0x200)
        self.addNewSection(None, "Data", 0x200, 0x200000)

    def updatePickledObj(self, rom):
        for s in self.sections:
            s.updatePickledObj(rom)
        self.createLinks(rom)

    def createLinks(self, rom):
        for s in self.sections:
            if s.type == "Code":
                s.updateContent(rom)
                for c in s.content:
                    locals = self.getInstLocalAddr(c)
                    for l in locals:
                        l[0].ilinks.append((c, l[1]))
                        s.olinks.append((l[0], l[1]))

    def getInstLocalAddr(self, inst):
        addrs = inst.getPointedAddr()
        locals = []
        for a in addrs:
            s = self.getContainingSection(a)
            locals.append((s, a - s.start))
        return locals

    def clearContent(self):
        for s in self.sections:
            s.content = []
            s.ilinks = []
            s.olinks = []

    def parseROM(self, rom, entry):
        self.initSections()

        def getSegment(a, inc=False):
            c = None
            cnt = 0
            last = 0
            for s, e in zip(codeStarts, codeEnds):
                if inc:
                    e += 2
                if s <= a and a < e:
                    return cnt, False
                elif last < a and a <= s:
                    return cnt - 1, True
                if inc:
                    e -= 2
                last = e
                cnt += 1
            return cnt, True

        done = False
        finishedSections = []
        parseStack = [entry]
        srStack = [entry]
        codeStarts = []
        codeEnds = []
        jumpTables = []
        getAddr = entry
        instAddr = entry
        chunk = ""

        thresh = 0  # change this to make it stop after a certain number of instructions
        numCmds = 0
        totalCmds = 0
        printThresh = 1000
        maxChunkLen = 20
        incTime = 0
        totalIncTime = 0
        startTime = time.time()

        while parseStack:
            numCmds += 1
            totalCmds += 1
            stepped = False

            t2 = time.time()
            inst, getAddr = asm.main.readInstruction(rom, getAddr)
            t1 = time.time()
            incTime += t1 - t2

            if inst.isValid:
                parseStack[-1] = getAddr
                after = False
                seg, after = getSegment(instAddr, True)

                if seg is not None:
                    if after:
                        codeStarts.insert(seg + 1, instAddr)
                        codeEnds.insert(seg + 1, getAddr)
                    elif codeEnds and instAddr == codeEnds[seg]:
                        codeEnds[seg] = getAddr
                    elif len(codeEnds) > seg + 1 and getAddr == codeStarts[seg + 1]:
                        codeStarts[seg + 1] = instAddr

                pops = []
                for i in range(len(codeStarts) - 1):
                    if codeEnds[i] >= codeStarts[i + 1]:
                        codeEnds[i] = codeEnds[i + 1]
                        pops.append(i + 1)
                    if codeStarts[i] >= codeEnds[i]:
                        numCmds = thresh

                if numCmds != thresh:
                    o = 0
                    for p in pops:
                        codeStarts.pop(p - o)
                        codeEnds.pop(p - o)
                        o += 1

                cmd = inst.baseRepr(False)
                dest = None
                already = False

                variableJump = cmd in ["JSR", "JMP"] and (
                    inst.params["dest"].mode in ["010", "101", "110"]
                    or inst.params["dest"].mode + inst.params["dest"].reg == "111011"
                )
                variablePCJump = (
                    cmd in ["JSR", "JMP"]
                    and inst.params["dest"].mode + inst.params["dest"].reg == "111011"
                )

                if cmd in ["BSR", "BRA", "Bc", "DBc", "JSR", "JMP"]:
                    if not inst.params["dest"].isAbsolute():
                        dest = instAddr + 2 + util.sign(inst.params["dest"].val(), 2)
                    else:
                        dest = inst.params["dest"].val()

                if dest is not None and not variableJump:
                    already, after = getSegment(dest)
                    if after:
                        if cmd not in ["BRA", "JMP"]:
                            parseStack.append(dest)
                            if cmd in ["BSR", "JSR"]:
                                srStack.append(dest)
                            else:
                                srStack.append(None)
                        else:
                            parseStack[-1] = dest
                        stepped = True
                    elif cmd in ["BRA", "JMP"]:
                        dest = None

                if (dest is None and cmd in ["RTS", "RTE", "RTR", "BRA", "JMP"]) or variableJump:
                    parseStack.pop()
                    sr = srStack.pop()
                    if variablePCJump and dest:
                        jumpTables.append(dest)
                        print(
                            "%s%s ---- %s -> %s ---- %s"
                            % (
                                "  " * len(parseStack),
                                asm.getBankAddr(instAddr),
                                repr(inst),
                                hex(dest),
                                repr(chunk),
                            )
                        )
                    if sr is not None:
                        bStart = asm.getBankAddr(sr)
                        bEnd = asm.getBankAddr(getAddr)
                    if not parseStack:
                        print("Done, at %i cmds." % totalCmds)
                    stepped = True

                if parseStack:
                    instAddr = parseStack[-1]
                    getAddr = instAddr
                chunk = ""

            if not totalCmds % printThresh:
                print("%i -- %f" % (totalCmds, incTime))
                totalIncTime += incTime
                incTime = 0

            if (thresh and numCmds > thresh) or len(chunk) > maxChunkLen or not parseStack:
                if numCmds > thresh:
                    print("Reached threshold.")
                if chunk:
                    print("Current Chunk: %s" % chunk)
                if inst:
                    print("I think it's: %s, %i" % (inst.baseRepr(), inst.length))

                print("")
                print("=== Stack: %s" % repr([asm.getBankAddr(a) for a in parseStack]))
                print(
                    "=== Segments: %s"
                    % repr(
                        [
                            (asm.getBankAddr(s), asm.getBankAddr(e))
                            for s, e in zip(codeStarts, codeEnds)
                        ]
                    )
                )
                print("=== Time: %f -- %f" % (totalIncTime, time.time() - startTime))
                print("")

                numCmds = 0
                codeCounter = 1
                dataCounter = 1
                jumpCounter = 1

                jumpTables = sorted(jumpTables)
                jumpTables = [j for i, j in enumerate(jumpTables) if jumpTables.index(j) == i]

                print([hex(j) for j in jumpTables])

                self.addNewSection(None, "Code", codeStarts[0], codeEnds[0])
                codeCounter += 1

                codeStarts.append(0x200000)
                codeEnds.append(0x200000)

                for i in range(1, len(codeStarts)):
                    spl = codeEnds[i - 1]
                    while jumpTables and jumpTables[0] >= codeEnds[i - 1] and jumpTables[0] <= codeStarts[i]:
                        if jumpTables[0] != codeEnds[i - 1]:
                            self.addNewSection(None, "Unprocessed", spl, jumpTables[0])
                        s = self.addNewSection(None, "Jump Table", jumpTables[0], jumpTables[0])
                        s.isPermanent = True
                        spl = jumpTables[0]
                        jumpTables.pop(0)

                    if spl != codeStarts[i]:
                        self.addNewSection(None, "Unprocessed", spl, codeStarts[i])

                    if i != len(codeStarts) - 1:
                        self.addNewSection(None, "Code", codeStarts[i], codeEnds[i])

                print([hex(j) for j in jumpTables])
                yield True

    def addNewSection(self, name, typ, start=None, end=None, **kwargs):
        if start is None or end is None:
            start = self.sections[-1].end
            end = start + 2
        if not typ:
            typ = "Unprocessed"
        if not name:
            if typ in self.counters:
                name = "%s %i" % (typ, self.counters[typ])
                self.counters[typ] += 1
            else:
                name = "New Section"
        return self.addSection(ROMSection(name, typ, start, end, **kwargs))

    def addSection(self, added):
        self.sections.append(added)
        self.resize(added, added.start, added.end)
        return added

    def resize(self, sect, start, end):
        inter = self.getIntersectingSections(start, end)
        sect.start = start
        sect.end = end
        for s in inter:
            leftEnc = start <= s.start
            rightEnc = end >= s.end
            if leftEnc and rightEnc:
                if not s.isPermanent:
                    self.sections.remove(s)
            elif leftEnc:
                s.end = start
            elif rightEnc:
                s.start = end
            else:
                self.sections.append(ROMSection(s.name, s.type, s.end, end))
                s.end = start
            if s.start == s.end and not s.isPermanent:
                self.sections.remove(s)
            if s not in self.sections:
                del s

    def getContainingSection(self, addr):
        for s in self.sections:
            if addr >= s.start and addr < s.end:
                return s

    def sortSections(self):
        next = None
        new = []
        for i in range(len(self.sections)):
            low = max([s.start for s in self.sections])
            for s in self.sections:
                if s.start < low or (
                    s.start == low and s.end - s.start < next.end - next.start
                ):
                    low = s.start
                    next = s
            new.append(next)
            self.sections.remove(next)
        self.sections = new

    def getIntersectingSections(self, start, end):
        inter = []
        for s in self.sections:
            if (start > s.start and start < s.end) or (
                end > s.start and end < s.end
            ):
                inter.append(s)
        return inter

    def copyLayout(self, layout):
        self.sections = layout.sections[:]


class ROMSection(object):
    set = object.__setattr__

    def __init__(self, name, type, start, end):
        self.name = name
        self.type = type
        self.start = start
        self.end = end
        self.romPos = start
        self.outOfDate = True
        self.content = []
        self.ilinks = []
        self.olinks = []
        self.params = {}
        self.isPermanent = False

    def updatePickledObj(self, rom):
        if not hasattr(self, "romPos"):
            self.romPos = self.start
        if not hasattr(self, "ilinks"):
            self.ilinks = []
        if not hasattr(self, "olinks"):
            self.olinks = []

    def setParam(self, attr, val):
        self.set("outOfDate", True)
        self.params[attr] = val

    def getContent(self, rom):
        self.updateContent(rom)
        return self.content

    def getContentRepr(self, rom):
        self.updateContent(rom)
        return self.contentRepr

    def updateContent(self, rom):
        self.contentClass.updateContent(self, rom)

    def __getContentClass(self):
        if self.type in contentClasses:
            return contentClasses[self.type]
        return defaultContentClass

    contentClass = property(__getContentClass)
    size = property(lambda self: self.end - self.start)


class DefaultContent(object):
    def updateContent(self, sect, rom):
        if sect.outOfDate:
            sect.content = self.parseContent(sect, rom)
            sect.contentRepr = [repr(c) for c in sect.content]
            sect.outOfDate = False

    def parseContent(self, sect, rom):
        return ["(unprocessed data chunk)"]


class CodeContent(DefaultContent):
    def parseContent(self, sect, rom):
        content = []
        addr = sect.start
        while addr < sect.end:
            inst, addr = asm.main.readInstruction(rom, addr)
            if inst.isValid:
                content.append(inst)
        return content


class ListContent(DefaultContent):
    def parseContent(self, sect, rom):
        content = []
        addr = sect.start
        size = sect.params.get("size", 1)
        lineNum = 0
        while addr < sect.end:
            data = rom.getBytes(addr, min(sect.end - addr, size))
            line = "%i: %s" % (lineNum, data)
            lineNum += 1
            addr += size
            content.append(line)
        return content


contentClasses = {
    "Code": CodeContent(),
    "List": ListContent(),
}
defaultContentClass = DefaultContent()