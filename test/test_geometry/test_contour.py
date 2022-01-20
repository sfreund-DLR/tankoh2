import numpy as np

from tankoh2.geometry.contour import DomeEllipsoid, DomeSphere


def test_domeEllipsoidSphere():
    de = DomeEllipsoid(1, 1, 0.1)
    ve = de.volume
    ds = DomeSphere(1, 0.1)
    vs = ds.volume

    assert np.allclose(ve, vs)

def test_domeEllipsoid():
    de = DomeEllipsoid(1, 2, 0.1)
    a = de.area
    wallThk = 0.001
    vShell1 = de.getWallVolume(wallThk)
    vShell2 = a * wallThk
    assert abs(vShell1 / vShell2) - 1 < 0.025

