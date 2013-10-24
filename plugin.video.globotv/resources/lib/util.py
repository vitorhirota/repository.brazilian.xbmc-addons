import htmlentitydefs
import itertools
import re
import random
import time

# simple attributes object
# supports dict.get method and return None if attr does not exist
class struct(object):
    def __init__(self, kdict=None):
        kdict = kdict or {}
        self.__dict__.update(kdict)

    def __repr__(self):
        return repr(self.__dict__)

    def __getattr__(self, name):
        return None

    def get(self, key):
        return self.__dict__.get(key)


##
# Removes HTML or XML character references and entities from a text string.
#
# @param text The HTML (or XML) source text.
# @return The plain text, as a Unicode string, if necessary.
def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text  # leave as is
    return re.sub("&#?\w+;", fixup, text)


# metaclass definition to turn all methods in classmethods
def m(name, bases, dct):
    for k, v in dct.items():
        if type(v) is type(m):
            dct[k] = classmethod(v)
    return type(name, bases, dct)


class hashJS():
    '''
        hd content hashing class, version 2.5.4
        http://s.videos.globo.com/p2/j/api.min.js
    '''
    __metaclass__ = m

    class alist(list):
        '''helper class to "mimic" JS Arrays behavior'''
        def __getitem__(self, key):
            try:
                return list.__getitem__(self, key)
            except IndexError:
                return 0

        def __setitem__(self, k, v):
            try:
                return list.__setitem__(self, k, v)
            except IndexError:
                # add the value in the k index, filling with 0s as needed
                l = itertools.chain.from_iterable([[0]*(k - len(self)), [v]])
                self.extend(l)

    def get_signed_hashes(self, a):
        a = type(a) == list and a or [a]
        return map(self.P, a)

    z = "0123456789abcdef"
    A = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    B = ""

    def rstr2b64(self, a):
        b, c = ('', len(a))
        for d in range(0, c, 3):
            t1 = ord(a[d + 1]) << 8 if (d + 1 < c) else 0
            t2 = ord(a[d + 2]) if (d + 2 < c) else 0
            e = ord(a[d]) << 16 | t1 | t2
            for f in range(4):
                if d * 8 + f * 6 > len(a) * 8:
                    b += self.B
                else:
                    b += self.A[e >> 6 * (3 - f) & 63]
        return b

    def rstr2hex(self, a):
        b = ''
        for c in range(len(a)):
            d = ord(a[c])
            b += self.z[d >> 4 & 15] + self.z[d & 15]
        return b

    G = 3600
    H = "=0xAC10FD"
    def I(self, a):
        def _32lshift(data, bits):
            # return (data & 0xFFFFFF) << bits
            # d = -0x100000000 + data if (data & 0x80000000) else data
            # return (d << bits) & 0xFFFFFFFF
            r = 0xffffffff & (data << bits)
            return -(~(r - 1) & 0xffffffff) if r > 0x7fffffff else r
        def _zfrshift(data, bits):
            # rshift
            # sign = (data >> 31) & 1
            # fills = ((sign << bits) - 1) << (32 - bits) if sign else 0
            # return ((data & 0xffffffff) >> bits) | fills
            return (data & 0xffffffff) >> bits
        ####
        # the bitwise methods guarantee the same expected behavior as in JS
        # http://stackoverflow.com/questions/6535373/special-js-operators-in-python
        ####

        def b(a, b):
            c = a + b[1:9]
            return c
        def c(a):
            b = [0] * ((len(a) >> 2) + 1)
            for c in range(0, len(a) * 8, 8):
                b[c >> 5] |= ord(a[(c/8) & 255]) << c % 32
            return b
        def d(a):
            return ''.join([unichr(a[c >> 5] >> c % 32 & 255)
                            for c in range(0, len(a) * 32, 8)])
        def e(a, b):
            c = (a & 65535) + (b & 65535)
            d = (a >> 16) + (b >> 16) + (c >> 16)
            return _32lshift(d, 16) | c & 65535
        def f(a, b):
            return _32lshift(a, b) | _zfrshift(a, 32 - b)
        def g(a, b, c, d, g, h):
            return e(f(e(e(b, a), e(d, h)), g), c)
        def h(a, b, c, d, e, f, h):
            return g(b & c | ~b & d, a, b, e, f, h)
        def i(a, b, c, d, e, f, h):
            return g(b & d | c & ~d, a, b, e, f, h)
        def j(a, b, c, d, e, f, h):
            return g(b ^ c ^ d, a, b, e, f, h)
        def k(a, b, c, d, e, f, h):
            return g(c ^ (b | ~d), a, b, e, f, h)
        def l(a, b):
            a = self.alist(a)
            a[b >> 5] |= 128 << b % 32
            a[(b + 64 >> 9 << 4) + 14] = b
            c, d, f, g = (1732584193, -271733879, -1732584194, 271733878)
            for l in range(0, len(a), 16):
                m, n, o, p = (c, d, f, g)
                c = h(c, d, f, g, a[l + 0], 7, -680876936); g = h(g, c, d, f, a[l + 1], 12, -389564586); f = h(f, g, c, d, a[l + 2], 17, 606105819); d = h(d, f, g, c, a[l + 3], 22, -1044525330)
                c = h(c, d, f, g, a[l + 4], 7, -176418897); g = h(g, c, d, f, a[l + 5], 12, 1200080426); f = h(f, g, c, d, a[l + 6], 17, -1473231341); d = h(d, f, g, c, a[l + 7], 22, -45705983)
                c = h(c, d, f, g, a[l + 8], 7, 1770035416); g = h(g, c, d, f, a[l + 9], 12, -1958414417); f = h(f, g, c, d, a[l + 10], 17, -42063); d = h(d, f, g, c, a[l + 11], 22, -1990404162)
                c = h(c, d, f, g, a[l + 12], 7, 1804603682); g = h(g, c, d, f, a[l + 13], 12, -40341101); f = h(f, g, c, d, a[l + 14], 17, -1502002290); d = h(d, f, g, c, a[l + 15], 22, 1236535329)
                c = i(c, d, f, g, a[l + 1], 5, -165796510); g = i(g, c, d, f, a[l + 6], 9, -1069501632); f = i(f, g, c, d, a[l + 11], 14, 643717713); d = i(d, f, g, c, a[l + 0], 20, -373897302)
                c = i(c, d, f, g, a[l + 5], 5, -701558691); g = i(g, c, d, f, a[l + 10], 9, 38016083); f = i(f, g, c, d, a[l + 15], 14, -660478335); d = i(d, f, g, c, a[l + 4], 20, -405537848)
                c = i(c, d, f, g, a[l + 9], 5, 568446438); g = i(g, c, d, f, a[l + 14], 9, -1019803690); f = i(f, g, c, d, a[l + 3], 14, -187363961); d = i(d, f, g, c, a[l + 8], 20, 1163531501)
                c = i(c, d, f, g, a[l + 13], 5, -1444681467); g = i(g, c, d, f, a[l + 2], 9, -51403784); f = i(f, g, c, d, a[l + 7], 14, 1735328473); d = i(d, f, g, c, a[l + 12], 20, -1926607734)
                c = j(c, d, f, g, a[l + 5], 4, -378558); g = j(g, c, d, f, a[l + 8], 11, -2022574463); f = j(f, g, c, d, a[l + 11], 16, 1839030562); d = j(d, f, g, c, a[l + 14], 23, -35309556)
                c = j(c, d, f, g, a[l + 1], 4, -1530992060); g = j(g, c, d, f, a[l + 4], 11, 1272893353); f = j(f, g, c, d, a[l + 7], 16, -155497632); d = j(d, f, g, c, a[l + 10], 23, -1094730640)
                c = j(c, d, f, g, a[l + 13], 4, 681279174); g = j(g, c, d, f, a[l + 0], 11, -358537222); f = j(f, g, c, d, a[l + 3], 16, -722521979); d = j(d, f, g, c, a[l + 6], 23, 76029189)
                c = j(c, d, f, g, a[l + 9], 4, -640364487); g = j(g, c, d, f, a[l + 12], 11, -421815835); f = j(f, g, c, d, a[l + 15], 16, 530742520); d = j(d, f, g, c, a[l + 2], 23, -995338651)
                c = k(c, d, f, g, a[l + 0], 6, -198630844); g = k(g, c, d, f, a[l + 7], 10, 1126891415); f = k(f, g, c, d, a[l + 14], 15, -1416354905); d = k(d, f, g, c, a[l + 5], 21, -57434055)
                c = k(c, d, f, g, a[l + 12], 6, 1700485571); g = k(g, c, d, f, a[l + 3], 10, -1894986606); f = k(f, g, c, d, a[l + 10], 15, -1051523); d = k(d, f, g, c, a[l + 1], 21, -2054922799)
                c = k(c, d, f, g, a[l + 8], 6, 1873313359); g = k(g, c, d, f, a[l + 15], 10, -30611744); f = k(f, g, c, d, a[l + 6], 15, -1560198380); d = k(d, f, g, c, a[l + 13], 21, 1309151649)
                c = k(c, d, f, g, a[l + 4], 6, -145523070); g = k(g, c, d, f, a[l + 11], 10, -1120210379); f = k(f, g, c, d, a[l + 2], 15, 718787259); d = k(d, f, g, c, a[l + 9], 21, -343485551)
                c = e(c, m); d = e(d, n); f = e(f, o); g = e(g, p)
            return [c, d, f, g]
        def m(a):
            return d(l(c(a), len(a) * 8))
        return m(b(a, self.H))
    def J(self, a):
        return self.rstr2b64(self.I(a))
    def K(self, a):
        return self.rstr2hex(self.I(a))
    def L(self):
        return '%010d' % random.randint(1, 1e10)
    def M(self, a):
        b, c, d, e = (a[0:2], a[2:12], a[12:22], a[22:44])
        f, g = (int(c) + self.G, self.L())
        h = self.J(e + str(f) + g)
        return ''.join(map(str, ['05', b, c, d, f, g, h]))
    def N(self):
        return int(time.time() / 1e3)
    def O(self, a):
        b, c, d, e, f, g, h = (
                a[0:2], a[2:3], a[3:13], a[13:23], a[24:46],
                self.N() + self.G, self.L())
        i = self.J(f+g+h)
        return b + c + d + e + g + h + i
    def P(self, a):
        b, c, d, e, f = ('04', '03', '02', '', a[0:2])
        return (f == b and self.O(a) or
                (f == c or f == d) and self.M(a) or e)
