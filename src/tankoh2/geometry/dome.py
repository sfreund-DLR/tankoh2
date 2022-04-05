"""This module creates dome contours"""
from abc import ABCMeta, abstractmethod

import numpy as np
from scipy import special
from scipy import optimize

from tankoh2.service.exception import Tankoh2Error
from tankoh2 import log
from tankoh2.service.plot.generic import plotContour


def getDome(cylinderRadius, polarOpening, domeType=None, lDomeHalfAxis = None):
    """creates a dome analog to tankoh2.desig.winding.contour.getDome()

    :param cylinderRadius: radius of the cylinder
    :param polarOpening: polar opening radius
    :param domeType: pychain.winding.DOME_TYPES.ISOTENSOID or pychain.winding.DOME_TYPES.CIRCLE
    :param lDomeHalfAxis: ellipse half axis describing the dome length for elliptical domes
    """
    validDomeTypes = ['isotensoid', 'circle',
                      'ellipse', # allowed by own implementation in tankoh2.geometry.contour
                      1, 2,  # types from µWind
                      ]

    if domeType is None:
        domeType = 'isotensoid'
    elif isinstance(domeType, str):
        domeType = domeType.lower()
    elif isinstance(domeType, int) and domeType in validDomeTypes:
        domeType = {1:'isotensoid', 2:'circle'}[domeType]
    else:
        raise Tankoh2Error(f'wrong dome type "{domeType}". Valid dome types: {validDomeTypes}')
    # build  dome
    if domeType == 'ellipse':
        dome = DomeEllipsoid(cylinderRadius, lDomeHalfAxis, polarOpening)
    elif domeType == 'circle':
        dome = DomeSphere(cylinderRadius, polarOpening)
    elif domeType == 'isotensoid':
        from tankoh2.design.winding.contour import getDome as getDomeMuWind
        domeMuWind = getDomeMuWind(cylinderRadius, polarOpening, domeType)
        x, r = domeMuWind.getXCoords(), domeMuWind.getRCoords()
        dome = DomeGeneric(x,r)

    return dome

class AbstractDome(metaclass=ABCMeta):
    """Abstract class defining domes"""

    def __init__(self):
        self._contourCache = {} # nodeNumber --> result points

    @property
    def rCyl(self):
        """Return largest radius of dome"""
        return self.getContour()[1][0]

    @property
    def volume(self):
        """calc dome volume numerically by slices of circular conical frustums"""
        return self.getVolume(self.getContour())

    @staticmethod
    def getVolume(contour):
        """calc dome volume numerically by slices of circular conical frustums
        :param contour: iterable with x and radius coordinates as resulted from self.getContour()"""
        x, radii = contour
        R, r = radii[:-1], radii[1:]
        return np.sum(np.pi * (x[1:] - x[:-1]) / 3 * (R**2 + R*r + r**2))

    @abstractmethod
    def getDomeResizedByThickness(self, thickness):
        """return a dome that has a resized geometry by given thickness"""

    def getWallVolume(self, wallThickness):
        """Calculate the volume of the material used

        :param wallThickness: thickness of the dome material
        """
        otherDome = self.getDomeResizedByThickness(wallThickness)
        return otherDome.volume - self.volume

    @property
    def domeLength(self):
        """Returns the length of the dome, also considering the polar opening"""
        x, _ = self.getContour()
        return abs(x[0]-x[-1])


    @property
    def area(self):
        """calc dome area numerically by slices of circular conical frustums"""
        return self.getArea(self.getContour())

    @staticmethod
    def getArea(contour):
        """calc dome area numerically by slices of circular conical frustums
        :param contour: iterable with x and radius coordinates as resulted from self.getContour()"""
        x, r = contour
        return np.sum(np.pi * (r[:-1] + r[1:]) * np.sqrt((r[:-1] - r[1:]) ** 2 + (x[:-1] - x[1:]) ** 2))

    @abstractmethod
    def getContour(self, nodeNumber=250):
        """Return the countour of the dome

        :param nodeNumber: number of nodes used
        :return: vectors x,r: r starts at cylinder radius decreasing, x is increasing
        """


class DomeGeneric(AbstractDome):

    def __init__(self, x, r):
        """
        :param x: vector x is increasing
        :param r: vector r starts at cylinder radius decreasing
        """
        AbstractDome.__init__(self)
        self._x = x
        self._r = r



    @property
    def rPolarOpening(self):
        return self._r[-1]

    @property
    def rCyl(self):
        return self._r[0]

    def getDomeResizedByThickness(self, thickness):
        """return a dome that has a resized geometry by given thickness"""
        diff = np.array([self._x[:-1]-self._x[1:], self._r[:-1]-self._r[1:]])
        normals = diff
        normals[0] *= -1
        normals = normals[::-1,:]
        normals = np.append([[0],[1]], normals,axis=1) # add normal vector for conjunction to cylindrical part
        fac = np.linalg.norm(normals, axis=0)
        normals = normals / fac * thickness
        x, r = normals + [self._x, self._r]

        return DomeGeneric(x, r)

    def getContour(self, nodeNumber=250):
        """Return the countour of the dome

        :param nodeNumber: unused
        :return: vectors x,r: r starts at cylinder radius decreasing, x is increasing
        """
        return np.array([self._x, self._r])

class DomeEllipsoid(AbstractDome):
    """Calculcate ellipsoid contour

    :param rCyl: radius of cylindrical section
    :param lDomeHalfAxis: axial length of the ellipse (half axis)
    :param rPolarOpening: polar opening radius. The polar opening is only accounted for in getContour

    ::

        |              rPolarOpening
        |                 ←→
        |
        |             ..--    --..          ↑
        |         .-~              ~-.      |    lDomeHalfAxis
        |        /                    \     |
        |       |                     |     ↓
        |
        |       ←----------→
        |           rCyl
    """

    def __init__(self, rCyl, lDomeHalfAxis, rPolarOpening):
        AbstractDome.__init__(self)
        if rPolarOpening >= rCyl:
            raise Tankoh2Error('Polar opening should not be greater or equal to the cylindrical radius')
        self._rPolarOpening = rPolarOpening
        self._rCyl = rCyl
        self._lDomeHalfAxis = lDomeHalfAxis
        self.halfAxes = (self.lDomeHalfAxis, self.rCyl) if self.lDomeHalfAxis > self.rCyl else (self.rCyl, self.lDomeHalfAxis)

    @property
    def eccentricitySq(self):
        """return eccentricity squared"""
        a, b = self.halfAxes
        return 1.0 - b ** 2 / a ** 2

    @property
    def rPolarOpening(self):
        return self._rPolarOpening

    @property
    def rCyl(self):
        return self._rCyl

    @property
    def lDomeHalfAxis(self):
        return self._lDomeHalfAxis

    @property
    def aIsDomeLength(self):
        """Returns true if the dome length represents the major half axis of the ellipse"""
        return self.lDomeHalfAxis > self.rCyl

    def getDomeResizedByThickness(self, thickness):
        """return a dome that has a resized geometry by given thickness"""
        return DomeEllipsoid(self.rCyl + thickness, self.lDomeHalfAxis + thickness, self.rPolarOpening)


    def _getPolarOpeningArcLenEllipse(self):
        a, b = self.halfAxes
        if self.aIsDomeLength:
            phiPo = np.pi / 2 - np.arcsin(self.rPolarOpening / b)
        else:
            phiPo = np.pi / 2 - np.arccos(self.rPolarOpening / a)
        arcLen = self.getArcLength(phiPo)
        return arcLen

    @property
    def contourLength(self):
        """Calculates the circumference of the second elliptic integral of second kind
        :return: circumference
        """
        arcLen = self._getPolarOpeningArcLenEllipse()
        if self.aIsDomeLength:
            return arcLen
        quaterEllipseLength = self.getArcLength(np.pi/2)
        return quaterEllipseLength - arcLen


    def getPoints(self, phis):
        """Calculates a point on the ellipse

        ::

            |   b,y ↑
            |       |    /
            |       |phi/
            |       |  /
            |       | /
            |       |------------------→ a,x

        :param phis: angles of the ellipse in rad. For phi=0 → x=0, y=b. For phi=pi/2 → x=a, y=0
        :return: tuple x,y
        """
        a, b = self.halfAxes

        ys = a*b/np.sqrt(a**2+b**2*(np.tan(phis)**2))
        xs = a/b*np.sqrt(b**2-ys**2)
        return np.array([xs,ys])


    def getArcLength(self, phi):
        """Calculates the arc length"""
        a = self.halfAxes[0]
        return a * special.ellipeinc(phi, self.eccentricitySq)


    def getContour(self, nodeNumber=250):
        """Return the countour of the dome

        :param nodeNumber: number of nodes used
        :return: vectors x,r: x is increasing, r starts at cylinder radius decreasing

        The angles here are defined as follows::

            |   b,y ↑
            |       |    /
            |       |phi/
            |       |  /
            |       | /
            |       |------------------→ a,x


        """
        if nodeNumber in self._contourCache:
            return self._contourCache[nodeNumber]
        initAngles = np.pi /2 * np.arange(nodeNumber) / nodeNumber
        a, b = self.halfAxes
        arcPo = self._getPolarOpeningArcLenEllipse()
        if self.aIsDomeLength:
            arcStart = 0.
            arcEnd = arcPo
        else:
            arcStart = self.getArcLength(np.pi/2)
            arcEnd = arcPo
        arcLengths = np.linspace(arcStart, arcEnd, nodeNumber)
        res = optimize.root(
            lambda angles: (a * special.ellipeinc(angles, self.eccentricitySq) - arcLengths),
            initAngles)
        phis = res.x
        points = np.array([a * np.sin(phis), b * np.cos(phis)])
        if not self.aIsDomeLength:
            points = points[::-1,:]

        points[:, 0] = [0, self.rCyl] # due to numerical inaccuracy
        points[1, -1] = self.rPolarOpening # due to numerical inaccuracy
        self._contourCache[nodeNumber] = points
        return points

    def plotContour(self):
        """creates a plot of the outer liner contour"""
        points = self.getContour(20)
        plotContour(True, '', points[0,:], points[1,:])


class DomeSphere(DomeEllipsoid):
    """Defines a spherical dome"""

    def __init__(self, r, rPolarOpening):
        """
        :param r: radius
        :param rPolarOpening: polar opening radius
        """
        DomeEllipsoid.__init__(self, r, r, rPolarOpening)

    @property
    def radius(self):
        """Returns the radius of the sphere"""
        return self.rCyl

    @property
    def contourLength(self):
        """Calculates the circumference of the second elliptic integral of second kind
        :return: circumference
        """
        return np.pi * self.radius


def getCountourConical(rPolarOpening, rSmall, rLarge, lConical, domeType='circular'):
    """Calculates the countour of a dome and a attached conical structure

    ATTENTION:

    - This method is not yet finished!
    - It continas some hardcoded values like xOffset, rOffset
    - dydxConical must be iteratively identified which changes xOffset, rOffset.
      Or a fully analytical solution must be found
    - Only tested for dydxConical=1
    - extend for other dome types

    ::

        |                      rPolarOpening
        |                         ←-→
        |
        |                     ..--     --..
        |    circle 1     .-~               ~-.          rSmall
        |                /                     \     ↑
        |               /                       \    |   lConical
        |              /                         \   ↓
        |    circle 2 |                           |      rLarge
        |             |                           |
        |             |                           |


    :return: vectors x,r: r starts at cylinder radius decreasing, x is increasing
    """
    allowedDomeTypes = ['circular']
    if domeType not in allowedDomeTypes:
        raise Tankoh2Error(f'Wrong input for domeType "{domeType}". Valid types: {allowedDomeTypes}')
    if not all([val > 0 for val in [rSmall, rLarge, lConical]]):
        raise Tankoh2Error('All input values must be larger than zero')
    if rSmall >= rLarge:
        raise Tankoh2Error('rSmall >= rLarge')

    numPoints = 40
    # 1: circle at polar opening
    # find location where dr/dx of circular section is same dr/dx of conical section
    dydxConical = (rLarge - rSmall) / lConical
    # drdx=-x/np.sqrt(rSmall**2-x**2)
    x1SameDydx = dydxConical * rSmall
    rCirc1 = np.sqrt(x1SameDydx ** 2 + rSmall ** 2)
    alphaSmallR = np.arccos(x1SameDydx / rCirc1)
    alphaPolarOpening = np.arcsin(rPolarOpening / rCirc1)
    angles = np.linspace(alphaPolarOpening, alphaSmallR, numPoints)
    x1 = np.cos(angles) * rCirc1
    x1 = 2 * x1[-1] - x1  # x must be increasing
    r1 = np.sin(angles) * rCirc1

    # 2: conical section
    xOffset, rOffset = 100, 100
    x2, r2 = np.linspace([x1[-1], r1[-1]], [x1[-1] + xOffset, r1[-1] + rOffset], numPoints, False).T[:, 1:]

    # 3: circle at cylinder
    angles = np.linspace(alphaSmallR, np.pi / 2, numPoints)
    x3 = np.cos(angles) * rCirc1
    x3 = 2 * x3[0] - x3
    r3 = np.sin(angles) * rCirc1

    # put it together
    x = np.concatenate([x1, x2, x3])
    r = np.concatenate([r1, r2, r3])
    print(indent(np.array([x, r]).T, delim='  '))

    r = r[::-1]
    x = x[::-1]
    x = x[0] - x

    if 0:
        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)
        ax.plot(x, r)
        plt.show()

    log.error('This method is not fully implemented and uses hardcoded values')
    return x, r


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    from tankoh2.service.utilities import indent

    de = DomeEllipsoid(2,1,1)
    #de = DomeEllipsoid(1,2,0.5)
    de.plotContour()


    # getCountourConical(20 ,60 ,100 ,40)
    pass
