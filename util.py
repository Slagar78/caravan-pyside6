carry = 0

h2i = lambda i: int(i, 16)

# why do I always forget this...
# i = int of number
# l = places
def bin(i, l):
    global carry
    bs = ""
    for c in range(l):
        i = add(i, i, pow(2, l)-1)
        bs += repr(carry)
    return bs

def add(v1, v2, thresh):
    global carry
    v = v1 + v2
    carry = 0
    if v > thresh:
        carry = 1
    return v % (thresh+1)

def sign(i, l):
    r = 256 ** l
    return ((i + (r//2)) % r) - (r//2)

def tabs2spaces(text, tabsize):
    i = text.find("\t")
    while i != -1:
        text = text[:i] + " "*(-(i%tabsize) + tabsize) + text[i+1:]
        i = text.find("\t")
    return text