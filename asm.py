import re
import xml.dom.minidom as minidom
import util

getBankAddr = lambda a: "%02x:%04x" % (a // 0x10000, a % 0x10000)

# --------------
# language definition

class InstructionSet(object):

    def __init__(self, lang):
        self.order = []
        self.instDict = {}
        self.last = (None, None)

        # parse the document
        doc = minidom.parse("%s.xml" % lang)
        set = doc.childNodes[0]

        for n in set.childNodes:
            if n.nodeType == n.ELEMENT_NODE:
                opcode = n.getAttribute("opcode")
                inst = InstructionType(self, n)
                inst.opcode = opcode
                self.order.append(opcode)
                self.instDict[opcode] = inst

        self.splitPoint = [i for i in range(len(self.order)) if self.order[i].startswith("1")][0]
        self.fail = InstructionType(self, None)
        self.maxInstLen = 0

    def readInstruction(self, rom, addr):
        chunk = ""
        inst = None
        getAddr = addr

        while (inst is None or not inst.isValid) and len(chunk) <= self.maxInstLen:
            chunk += rom.getBytes(getAddr, 2)
            inst = self.getInstFromStr(chunk, addr)
            getAddr += 2

        return inst, getAddr

    def getInstruction(self, bstr, loc):
        inst = None

        if self.last[1] is not None and bstr.startswith(self.last[0]):
            op = self.last[1]
            inst = Instruction(self.instDict[self.last[1]], bstr, loc)
        else:
            order = self.order
            if bstr[0] == "1":
                order = self.order[self.splitPoint:]

            for op in order:
                short = bstr[:len(op)]
                m = re.match(op, bstr)
                if m:
                    inst = Instruction(self.instDict[op], bstr, loc)
                    break

        if not inst:
            op = None
            inst = None  # Instruction(self.fail, "")

        self.last = (bstr, op)
        return inst

    getInstFromStr = lambda self, arg, loc: self.getInstruction(util.bin(int(arg, 16), len(arg)*4), loc)

    maxLength = 10
    byteSize = 8


class InstructionType(object):

    def __init__(self, set, node):
        self.set = set

        if node:
            self.xmlNode = node
            elements = [n for n in node.childNodes if n.nodeType == n.ELEMENT_NODE]
            keys = [n.nodeName for n in elements]

            self.xmlElements = {}
            for k, v in zip(keys, elements):
                self.xmlElements[str(k)] = str(v.firstChild.nodeValue)

            self.formats = self.xmlElements["format"].split(",")
            self.vars = self.xmlElements["vars"].split(",")

    isValid = property(lambda self: hasattr(self, "xmlNode"))


# --------------
# specific uses

class Instruction(object):

    def __init__(self, itype, bstr, loc):
        self.bstr = bstr
        self.opcode = itype.opcode
        self.loc = loc
        self.params = {}

        if self.type.isValid:
            for v, f in zip(itype.vars, itype.formats):
                ptype = paramMap.get(f, InstructionParameter)
                p = ptype(self, v, f)
                p.bstr = bstr[:p.length]
                bstr = bstr[p.length:]
                self.params[v] = p

            for p in ["src", "dest"]:
                if p in self.params and self.params[p].numParams:
                    self.params[p].pbstr = bstr[:self.params[p].paramLength()]
                    bstr = bstr[self.params[p].paramLength():]

    def __repr__(self):
        s = ""
        s += getBankAddr(self.loc)
        s += "\t"
        s += self.type.xmlElements["repr"].replace("s", repr(self.params.get("size", "")))
        s += "\t"

        if "src" in self.params:
            s += str(self.params["src"]) + ","
        if "dest" in self.params:
            s += str(self.params["dest"])

        return s

    def __len__(self):
        return self.length

    def baseRepr(self, processed=True):
        if processed:
            return repr(self).split(".")[0]
        return self.type.xmlElements["repr"].split(".")[0]

    def getPointedAddr(self):
        addr = []
        if "src" in self.params and self.params["src"].isAddr:
            addr.append(self.loc + self.params["src"].val() + 2)
        if "dest" in self.params and self.params["dest"].isAddr:
            addr.append(self.loc + self.params["dest"].val() + 2)
        return addr

    type = property(lambda self: main.instDict[self.opcode])
    set = property(lambda self: main)

    length = property(lambda self: (sum([p.length + p.paramLength() for p in self.params.values()])) // self.set.byteSize)
    isValid = property(lambda self: self.type.isValid and self.length == len(self.bstr) // self.set.byteSize)


# --------------
# specific instruction parameter types

class InstructionParameter(object):

    def __init__(self, inst, name, ptype):
        self.inst = inst
        self.name = name
        self.type = ptype

    def __getLength(self):
        if self.type.isdigit():
            return int(self.type)
        else:
            return paramSizes[self.type]

    def val(self):
        return int(self.bstr, 2)

    def getNumParams(self):
        return 0

    def paramLength(self):
        return 0

    def __repr__(self):
        return "#$%x" % self.val()

    length = property(__getLength)
    numParams = property(lambda self: self.getNumParams())
    isAddr = False


paramSizes = {
    "ea":       6,
    "bea":      6,
    "bsize":    1,
    "size":     2,
    "xsize":    3,
    "reg":      3,
    "areg":     3,
    "bool":     1,
    "nibble":   4,
    "cond":     4,
    "byte":     8,
    "word":     16,
    "long":     32,
    "data":     0,
    "var":      0,
    "bvar":     8,
    "ofs":      16,
    "movesize": 2,
    "addrsize": 3,
    "trap":     4,
}


class ParamWord(InstructionParameter):

    def val(self):
        return util.sign(int(self.bstr, 2), 2)

    def isAbsolute(self):
        return False

    isAddr = False


class ParamSize(InstructionParameter):

    def __repr__(self):
        return ["B", "W", "L", "?"][self.val()]

    def val(self):
        return int(self.bstr, 2) % 4

    def getNumParams(self):
        if "data" in self.inst.type.formats:
            return 1
        return 0

    def paramLength(self):
        if self.numParams:
            return max((2 ** self.val()) * 8, 16)
        else:
            return 0


class ParamBSize(ParamSize):

    def __repr__(self):
        return ["W", "L"][self.val()]


class ParamMoveSize(ParamSize):

    def val(self):
        return [3, 0, 2, 1][int(self.bstr, 2) % 4]


class ParamAddrSize(ParamSize):

    def val(self):
        return [1, 2][int(self.bstr[0], 2)]


class ParamReg(InstructionParameter):

    def __repr__(self):
        return "D%i" % (self.val())


class ParamAReg(InstructionParameter):

    def __repr__(self):
        return "A%i" % (self.val())


class ParamEA(InstructionParameter):

    def val(self):
        if self.mode == "101":
            return int(self.pbstr, 2)
        elif self.mode == "110":
            return (int(self.pbstr[:4], 2), int(self.pbstr[8:], 2))
        elif self.mode == "111":
            if self.reg != "011":
                return int(self.pbstr, 2)
            else:
                return (int(self.pbstr[:4], 2), int(self.pbstr[8:], 2))
        return 0

    def getNumParams(self):
        if self.mode in ["101", "110"]:
            return 1
        elif self.mode == "110":
            return 2
        elif self.mode == "111":
            if self.reg == "011":
                return 2
            else:
                return 1
        else:
            return 0

    def paramLength(self):
        if self.numParams:
            if self.mode in ["101", "110"] or self.reg in ["000", "010", "011"]:
                return 16
            elif self.mode in ["111"] and self.reg in ["100"]:
                return max((2 ** self.inst.params["size"].val()) * 8, 16)
            else:
                return 32
        else:
            return 0

    def isAbsolute(self):
        if self.mode in ["101", "110"]:
            return False
        elif self.mode == "111":
            if self.reg in ["010", "011"]:
                return False
        return True

    def __repr__(self):
        if self.mode == "000":
            return "D%i" % int(self.reg, 2)
        elif self.mode == "001":
            return "A%i" % int(self.reg, 2)
        elif self.mode == "010":
            return "(A%i)" % int(self.reg, 2)
        elif self.mode == "011":
            return "(A%i)+" % int(self.reg, 2)
        elif self.mode == "100":
            return "-(A%i)" % int(self.reg, 2)
        elif self.mode == "101":
            ofs = ""
            if self.val() != 0:
                ofs = hex(self.val())[2:].zfill(4)
            return "$%s(A%i)" % (ofs, int(self.reg, 2))
        elif self.mode == "110":
            ofs = ""
            if self.val()[1] != 0:
                ofs = "$%s" % hex(self.val()[1])[2:].zfill(2)
            rtype = ["D", "A"][int(self.pbstr[0])]
            return "%s(A%i,%s%i)" % (ofs, int(self.reg, 2), rtype, self.val()[0])
        elif self.mode == "111" and self.reg in ["000", "001"]:
            return "($%s)" % hex(self.val())[2:].zfill(self.paramLength() // 4)
        elif self.mode == "111" and self.reg == "010":
            return "$%s(PC)" % hex(self.val())[2:].zfill(4)
        elif self.mode == "111" and self.reg == "011":
            ofs = ""
            if self.val()[1] != 0:
                ofs = "$%s" % hex(self.val()[1])[2:].zfill(2)
            rtype = ["D", "A"][int(self.pbstr[0])]
            return "%s(PC,%s%i)" % (ofs, rtype, self.val()[0])
        elif self.mode == "111" and self.reg == "100":
            return "#$%s" % hex(self.val())[2:].zfill(2 ** self.inst.params["size"].val() * 2)

        return "mode%sreg%s-%s" % (self.mode, self.reg, hex(self.val())[2:].zfill(4))

    mode = property(lambda self: self.bstr[:3])
    reg = property(lambda self: self.bstr[3:])


class ParamBEA(ParamEA):

    reg = property(lambda self: self.bstr[:3])
    mode = property(lambda self: self.bstr[3:])


class ParamOfs(InstructionParameter):

    def val(self):
        return util.sign(int(self.bstr, 2), 1)

    def __repr__(self):
        addr = self.inst.loc + self.val() + 2
        val = hex(int(self.bstr, 2))[2:].zfill(self.getNumParams() * 2 + 2)
        return "#$%s [%s]" % (val, getBankAddr(addr))

    isAddr = True


class ParamBVar(InstructionParameter):

    def val(self):
        if self.bstr.startswith("00000000"):
            return util.sign(int(self.pbstr, 2), 2)
        return util.sign(int(self.bstr, 2), 1)

    def getNumParams(self):
        return [0, 1][self.bstr.startswith("00000000")]

    def paramLength(self):
        return [0, 16][self.bstr.startswith("00000000")]

    def isAbsolute(self):
        return False

    def __repr__(self):
        addr = self.inst.loc + self.val() + 2
        val = hex(int(self.bstr, 2))[2:].zfill(self.getNumParams() * 2 + 2)
        return "#$%s [%s]" % (val, getBankAddr(addr))

    isAddr = True


class ParamTrap(InstructionParameter):

    def val(self):
        return int(self.bstr, 2)

    def getNumParams(self):
        v = self.val()
        if v in [6]:
            return 0
        elif v in [9]:
            return 3
        else:
            return 1

    def paramLength(self):
        return self.getNumParams() * 16


paramMap = {
    "word": ParamWord,
    "bsize": ParamBSize,
    "size": ParamSize,
    "xsize": ParamSize,
    "movesize": ParamMoveSize,
    "addrsize": ParamAddrSize,
    "ofs": ParamOfs,
    "reg": ParamReg,
    "areg": ParamAReg,
    "ea": ParamEA,
    "bea": ParamBEA,
    "bvar": ParamBVar,
    "trap": ParamTrap,
}

# --------------

main = InstructionSet("68k")
main.maxInstLen = 20