'''
     StorageServer override.
     Version: 1.0
'''


class StorageServer:
    def __init__(self, *args, **kwargs):
        self.dict = {}
        return None

    def cacheFunction(self, funct=False, *args):
        key = '%s|%s' % (funct.func_name, args)
        if key not in self.dict:
            self.dict[key] = funct(*args)
        return self.dict[key]

    def set(self, name, data):
        self.dict[name] = data
        return data

    def get(self, name):
        return self.dict.get(name)

    def setMulti(self, name, data):
        return ""

    def getMulti(self, name, items):
        return ""

    def lock(self, name):
        return False

    def unlock(self, name):
        return False
