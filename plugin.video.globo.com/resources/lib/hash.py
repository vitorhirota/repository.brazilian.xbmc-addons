# -*- coding: UTF-8 -*-
'''
hash module for plugin.video.globo.com

Original procedure at http://s.videos.globo.com/p2/j/api.min.js
version > 2.5.4

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
import base64
import hashlib
import random
import time

def get_signed_hashes(a):
    a = type(a) == list and a or [a]
    return map(P, a)

G = 3600
H = "=0xAC10FD"

def J(a):
    # def I has been replaced with hashlib.md5.digest
    # def rstr2b64 has been replaced with b64encode
    digest = hashlib.md5(a + H[1:]).digest()
    return base64.b64encode(digest).replace('=', '')

def K(a):
    # def I has been replaced with hashlib.md5.digest
    # def rstr2hex has been replaced with b16encode
    # note that def rstr2hex outputs in lower
    digest = hashlib.md5(a + H[1:]).digest()
    return base64.b16encode(digest).replace('=', '')

def L():
    return '%010d' % random.randint(1, 1e10)

def M(a):
    b, c, d, e = (a[0:2], a[2:12], a[12:22], a[22:44])
    f, g = (int(c) + G, L())
    h = J(e + str(f) + g)
    return ''.join(map(str, ['05', b, c, d, f, g, h]))

def N():
    return int(time.time() / 1e3)

def O(a):
    b, c, d, e, f, g, h = (
            a[0:2], a[2:3], a[3:13], a[13:23], a[24:46],
            N() + G, L())
    i = J(f+g+h)
    return b + c + d + e + g + h + i

def P(a):
    b, c, d, e, f = ('04', '03', '02', '', a[0:2])
    return (f == b and O(a) or
            (f == c or f == d) and M(a) or e)
