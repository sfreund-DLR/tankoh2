import numpy as np

from tankoh2.geometry.liner import Liner
from tankoh2.geometry.dome import DomeEllipsoid

r = 1
l = 2
dl = 0.5

def getLiner(singleDome = True, polarOpeningR = 0.1):
    de = DomeEllipsoid(r,r,polarOpeningR)
    if singleDome:
        return Liner(de, l)
    else:
        de2 = DomeEllipsoid(r, dl, polarOpeningR)
        return Liner(de, l, de2)

def test_linerR():
    liner = getLiner()
    assert np.allclose(liner.rCyl, r)

def test_linerLength():
    liner = getLiner(polarOpeningR=0)
    assert np.allclose(liner.length, 2*r+l)

def test_linerLength2():
    liner = getLiner(singleDome=False, polarOpeningR=0)
    assert np.allclose(liner.length, dl+r+l)

def test_linerVol():
    liner = getLiner()
    ref = np.pi*l*r**2
    assert np.allclose(liner.volume - 2*liner.dome.volume, ref)

def test_linerVol2():
    liner = getLiner(singleDome=False)
    ref = np.pi*l*r**2
    assert np.allclose(liner.volume - liner.dome.volume - liner.dome2.volume, ref)

def test_linerWallVol():
    liner = getLiner()
    thk = 0.001
    ref = 2*liner.dome.getWallVolume(thk)+np.pi*l*((r+thk)**2-r**2)
    assert np.allclose(liner.getWallVolume(thk), ref)

#def test_linerWallVol():
#    liner = getLiner(singleDome=False)
#    thk = 0.001
#    ref = liner.dome.getWallVolume(thk)+liner.dome2.getWallVolume(thk)+np.pi*l*((r+thk)**2-r**2)
#    assert np.allclose(liner.getWallVolume(thk), ref)





