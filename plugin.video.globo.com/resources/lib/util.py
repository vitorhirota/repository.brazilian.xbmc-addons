import base64
import hashlib
import htmlentitydefs
import json
import unicodedata
import random
import re
import string
import time

try:
    import cPickle as pickle
except:
    import pickle


class struct(object):
    '''
        Simple attributes helper class that behaves like dict.get for unset
        attrs.
    '''
    def __init__(self, kdict=None):
        kdict = kdict or {}
        self.__dict__.update(kdict)

    def __repr__(self):
        return repr(self.__dict__)

    def __getattr__(self, name):
        return None

    def __len__(self):
        return len(self.__dict__)

    def get(self, key):
        return self.__dict__.get(key)


def slugify(string):
    '''
        Helper function that slugifies a given string.
    '''
    slug = unicodedata.normalize('NFKD', string)
    slug = slug.encode('ascii', 'ignore').lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug).strip('-')
    return re.sub(r'[-]+', '-', slug)


def unescape(text):
    '''
        Removes HTML or XML character references and entities from a text string.
        @param text The HTML (or XML) source text.
        @return The plain text, as a Unicode string, if necessary.
    '''
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


def time_format(time_str=None, input_format=None):
    '''
        Helper function to reformat time according to xbmc expecctation DD.MM.YYYY
    '''
    if time_str:
        time_obj = time.strptime(time_str, input_format)
        return time.strftime('%d.%m.%Y', time_obj)
    else:
        return time.strftime('%d.%m.%Y')


# methods below are part of globo hashing scheme
# original procedure at http://s.videos.globo.com/p2/j/api.min.js
# version > 2.5.4
def get_signed_hashes(a):
    a = type(a) == list and a or [a]
    return map(P, a)

G = 3600
H = "=0xAC10FD"
table1 = string.maketrans('/+', '_-')

def J(a):
    # def I has been replaced with hashlib.md5.digest
    # def rstr2b64 has been replaced with b64encode
    digest = hashlib.md5(a + H[1:]).digest()
    return base64.b64encode(digest).translate(table1, '=')

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
    h = J('%s'*3 % (e, f, g))
    return '%s'*7 % ('05', b, c, d, f, g, h)

def N():
    return int(time.time())

def O(a):
    b, c, d, e, f, g, h = (
            a[0:2], a[2:3], a[3:13], a[13:23], a[24:46],
            N() + G, L())
    i = J('%s'*3 % (f, g, h))
    return '%s'*7 % (b, c, d, e, g, h, i)

def P(a):
    b, c, d, e, f = ('04', '03', '02', '', a[0:2])
    return (f == b and O(a) or
            (f == c or f == d) and M(a) or e)
