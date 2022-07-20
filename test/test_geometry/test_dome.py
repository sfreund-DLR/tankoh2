import numpy as np

from tankoh2.geometry.dome import DomeEllipsoid, DomeSphere, DomeGeneric, DomeIsotensoid


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
    vFullEllipsoid = 2 * np.pi / 3 * de.rCyl ** 2 * de.lDomeHalfAxis
    assert de.volume < vFullEllipsoid

def test_domeEllipsoidVolume2():
    de = DomeEllipsoid(1000, 2000, 0)
    vFullEllipsoid = 2 * np.pi / 3 * de.rCyl ** 2 * de.lDomeHalfAxis
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
    x, r = de.getContour(100)
    assert all((x[1:] - x[:-1]) > 0)
    assert all((r[1:] - r[:-1]) < 0)
    assert np.allclose(x[0], 0)
    assert x[-1] < de.lDomeHalfAxis
    assert np.allclose(r[0], de.rCyl)
    assert np.allclose(r[-1], de.rPolarOpening)
    dx, dr = abs(x[:-1]-x[1:]), abs(r[:-1]-r[1:])
    norm = np.linalg.norm([dx, dr], axis=0)
    assert np.all(np.abs(norm/norm[0]-1) < 1e-4)

def test_ellipseContour2():
    rCyl, lDome = 10, 20
    de = DomeEllipsoid(rCyl, lDome, 1)
    x, r = de.getContour(100)
    assert all((x[1:] - x[:-1]) > 0)
    assert all((r[1:] - r[:-1]) < 0)
    assert np.allclose(x[0], 0)
    assert x[-1] < de.lDomeHalfAxis
    assert np.allclose(r[0], de.rCyl)
    assert np.allclose(r[-1], de.rPolarOpening)
    dx, dr = abs(x[:-1]-x[1:]), abs(r[:-1]-r[1:])
    norm = np.linalg.norm([dx, dr], axis=0)
    assert np.all(np.abs(norm/norm[0]-1) < 1e-4)


def test_ellipseContour3():
    radius, count = 10, 5
    de = DomeEllipsoid(radius, radius, 0)
    x, r = de.getContour(count)
    angles = np.linspace(0, np.pi/2, count)
    ref = [radius * np.sin(angles), radius * np.cos(angles)]
    assert np.allclose([x,r], ref)

def test_ellipseContour4():
    rCyl, lDome = 10, 0.0001
    de = DomeEllipsoid(rCyl, lDome, 1)
    x, r = de.getContour(100)
    rRef = np.linspace(rCyl,1,100)
    assert np.allclose(r,rRef)

def test_ellipseContourCheckEqualDist1():
    rCyl, lDome = 1, 0.99
    de = DomeEllipsoid(rCyl, lDome, rCyl/2)
    points = de.getContour(5)
    dp = abs(points[:,:-1]-points[:,1:])
    norm = np.linalg.norm(dp, axis=0)
    assert np.alltrue(np.abs(norm/norm[0]-1) < 2e-4)

def test_ellipseContourCheckEqualDist2():
    rCyl, lDome = 0.99, 1.
    de = DomeEllipsoid(rCyl, lDome, rCyl/2)
    x, r = de.getContour(5)
    dx, dr = abs(x[:-1]-x[1:]), abs(r[:-1]-r[1:])
    norm = np.linalg.norm([dx, dr], axis=0)
    assert np.alltrue(np.abs(norm/norm[0]-1) < 2e-4)

def test_ellipseContourCheckSimilarPoints():
    rCyl, lDome = 1, 0.9999
    de = DomeEllipsoid(rCyl, lDome, rCyl/2)
    p1 = de.getContour(5)

    rCyl, lDome = 0.9999, 1.
    de = DomeEllipsoid(rCyl, lDome, rCyl/2)
    p2 = de.getContour(5)
    assert np.allclose(p1,p2, rtol=1e-4)

def test_ellipseWallVolume():
    r = 1000
    de = DomeEllipsoid(r, r, 0)
    vRefSphere = 4/3*np.pi*((r+1)**3-r**3)
    assert abs(2*de.getWallVolume(1) / vRefSphere -1) < 1e-5

def test_domeVolumes():
    r = 1
    thk = 0.01
    po = r/10
    dc = DomeSphere(r, po)
    de = DomeEllipsoid(r,r,po)
    dg = DomeGeneric(*dc.getContour())
    assert np.allclose(dc.volume, de.volume)
    assert np.allclose(dc.volume, dg.volume)
    assert np.allclose(dc.getWallVolume(thk), de.getWallVolume(thk))
    assert np.allclose(dc.getWallVolume(thk), dg.getWallVolume(thk), rtol=1e-4)

def test_domeIsotensoid():
    di = DomeIsotensoid(400/3, 20)
    points = di.getContour(250)
    assert np.any(np.isnan(points))

