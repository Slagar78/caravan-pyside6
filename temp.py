import pickle
import layout

def doTempStuff():
    dumpPickledProj("sf2.caravan-game")

def dumpPickledProj(fn):
    proj = layout.Project("Shining Force 2")
    with open(fn, "wb") as f:
        pickle.dump(proj, f, -1)