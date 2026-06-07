import pickle

def init(filename):
    try:
        with open(filename, "rb") as f:
            cfg = pickle.load(f)
    except IOError as e:
        cfg = CaravanSettings(filename)
        cfg.save()
    return cfg


class CaravanSettings(object):
    def __init__(self, filename):
        self.filename = filename
        self.options = {}
        self.platforms = {}
        self.games = {}
        self.history = {}
        self.history["ROMs"] = []

    def save(self):
        with open(self.filename, "wb") as f:
            pickle.dump(self, f, -1)