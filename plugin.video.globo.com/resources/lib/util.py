import htmlentitydefs
import unicodedata
import re

try:
    from StorageServer import StorageServer
except:
    from test.storageserverdummy import StorageServer


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

    def __len__(self):
        return len(self.__dict__)

    def get(self, key):
        return self.__dict__.get(key)


class Cache(StorageServer):
    '''
        StorageServer class specialization that always sets values as python
        objects repr and upong get eval the string back to python objects.
    '''
    def set(self, key, value):
        StorageServer.set(self, key, repr(value))

    def get(self, key):
        data = StorageServer.get(self, key)
        if data:
            try:
                data = eval(data)
            except:
                pass
        return data



def find(exp, text):
    '''
        Helper class for regexp matching.
        @param exp The regular expression.
        @param text The text to be matched against.
        @return A tuple containing the matches
    '''
    return re.findall(exp, text, re.S|re.U)


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


# metaclass definition to turn all methods in classmethods
def m(name, bases, dct):
    for k, v in dct.items():
        if type(v) is type(m):
            dct[k] = classmethod(v)
    return type(name, bases, dct)
