import numpy as np

from tankoh2.geometry.contour import DomeEllipsoid, DomeSphere


def test_domeEllipsoidSphere():
    de = DomeEllipsoid(1000, 1000, 100)
    ve = de.volume
    ds = DomeSphere(1000, 100)
    vs = ds.volume
    assert np.allclose(ve, vs)

def test_domeEllipsoidShell():
    de = DomeEllipsoid(1000, 2000, 100)
    a = de.area
    wallThk = 1
    vShell1 = de.getWallVolume(wallThk)
    vShell2 = a * wallThk
    assert abs(vShell1 / vShell2 - 1) < 0.022

def test_domeEllipsoidVolume1():
    de = DomeEllipsoid(1000, 2000, 100)
    vFullEllipsoid = 2 * np.pi / 3 * de.rCyl ** 2 * de.lDome
    assert de.volume < vFullEllipsoid

def test_domeEllipsoidVolume2():
    de = DomeEllipsoid(1000, 2000, 0)
    vFullEllipsoid = 2 * np.pi / 3 * de.rCyl ** 2 * de.lDome
    assert de.volume < vFullEllipsoid
    assert abs(1-de.volume / vFullEllipsoid) < 2e-5

def test_ellipseCircumference():
    r = 4
    de = DomeEllipsoid(r, r, 0)
    c = de.contourLength
    assert np.allclose(c, 1/2*np.pi*r)

def test_ellipseContour1():
    rCyl, lDome = 20, 10
    de = DomeEllipsoid(rCyl, lDome, 1)
    x, r = de.getContour(5)
    assert all((x[1:] - x[:-1]) > 0)
    assert all((r[1:] - r[:-1]) < 0)
    assert np.allclose(x[0], 0)
    assert x[-1] < de.lDome
    assert np.allclose(r[0], de.rCyl)
    assert np.allclose(r[-1], de.rPolarOpening)

def test_ellipseContour2():
    rCyl, lDome = 10, 20
    de = DomeEllipsoid(rCyl, lDome, 1)
    x, r = de.getContour(5)
    assert all((x[1:] - x[:-1]) > 0)
    assert all((r[1:] - r[:-1]) < 0)
    assert np.allclose(x[0], 0)
    assert x[-1] < de.lDome
    assert np.allclose(r[0], de.rCyl)
    assert np.allclose(r[-1], de.rPolarOpening)


def test_ellipseContour3():
    radius, count = 10, 5
    de = DomeEllipsoid(radius, radius, 0)
    x, r = de.getContour(count)
    angles = np.linspace(0, np.pi/2, count)
    xref = radius * np.sin(angles)
    rref = radius * np.cos(angles)
    assert np.allclose(x, xref)
    assert np.allclose(r, rref)

