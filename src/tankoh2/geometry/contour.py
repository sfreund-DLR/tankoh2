"""This module creates dome contours"""
from abc import ABCMeta, abstractmethod, abstractproperty

import numpy as np
from matplotlib import pyplot as plt
from scipy import special
from scipy.optimize import minimize_scalar

from tankoh2.service.exception import Tankoh2Error
from tankoh2.service.utilities import indent
from tankoh2 import log


class AbstractDome(metaclass=ABCMeta):
    """Abstract class defining domes"""

    def __init__(self):
        self._contourCache = {} # nodeNumber --> result points

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
    def getWallVolume(self, wallThickness):
        """Calculate the volume of the material used

        :param wallThickness: thickness of the dome material
        :return: scalar, wall volume
        """

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


class DomeEllipsoid(AbstractDome):

    def __init__(self, rCyl, lDome, rPolarOpening):
        """Calculcate ellipsoid contour
        :param rCyl: radius of cylindrical section
        :param lDome: axial length of dome
        :param rPolarOpening: polar opening radius. The polar opening is only accounted for in getContour

                          rPolarOpening
                             ←→

                         ..--    --..          ↑
                     .-~              ~-.      |    lDome
                    /                    \     |
                   |                     |     ↓

                   ←----------→
                       rCyl
        """
        if rPolarOpening >= rCyl:
            raise Tankoh2Error('Polar opening should not be greater or equal to the cylindrical radius')
        self.rPolarOpening = rPolarOpening
        self._rCyl = rCyl
        self._lDome = lDome
        self.halfAxes = (self.lDome, self.rCyl) if self.lDome > self.rCyl else (self.rCyl, self.lDome)
        a, b = self.halfAxes
        self.eccentricitySq = 1.0 - b ** 2 / a ** 2  # eccentricity squared

    @property
    def rCyl(self):
        return self._rCyl

    @property
    def lDome(self):
        return self._lDome

    @property
    def aIsDomeLength(self):
        """Returns true if the dome length represents the major half axis of the ellipse"""
        return self.lDome > self.rCyl

    def getWallVolume(self, wallThickness):
        """Calculate the volume of the material used

        :param wallThickness: thickness of the dome material
        """
        otherDome = DomeEllipsoid(self.rCyl + wallThickness, self.lDome + wallThickness, self.rPolarOpening)
        return otherDome.volume - self.volume

    def _getPolarOpeningArcLenEllipse(self):
        a, b = self.halfAxes
        if self.aIsDomeLength:
            yPo = self.rPolarOpening
            xPo = a/b*np.sqrt((b**2-yPo**2))
        else:
            xPo = self.rPolarOpening
            yPo = b / a * np.sqrt((a ** 2 - xPo ** 2))
        phiPo = np.arctan2(xPo, yPo)
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



        a, b = self.halfAxes
        e_sq = 1.0 - b ** 2 / a ** 2  # eccentricity squared
        return 2 * a * special.ellipe(e_sq)  # circumference formula

    def getPoints(self, phis):
        """Calculates a point on the ellipse

            b,y ↑
                |    /
                |phi/
                |  /
                | /
                |------------------→ a,x

        :param phis: angles of the ellipse in rad. For phi=0 → x=0, y=b. For phi=pi/2 → x=a, y=0
        :return: tuple x,y
        """
        a, b = self.halfAxes

        ys = a*b/np.sqrt(a**2+b**2*(np.tan(phis)**2))
        xs = a/b*np.sqrt(b**2-ys**2)
        return np.array([xs,ys])

    def getPhiByArcLength(self, arcLength):
        """Calculate angle phi starting from phiStart and a given arc length
            b,y ↑
                |    /
                |phi/
                |  /
                | /
                |------------------→ a,x
        :param arcLength: length of the arc
        :return: angle in rad
        """
        a = self.halfAxes[0]

        def optFun(phi):
            return abs(arcLength - (a * special.ellipeinc(phi, self.eccentricitySq)))

        result = minimize_scalar(optFun, bounds=(0, np.pi), method='bounded')
        phi = result.x

        return phi

    def getArcLength(self, phi):
        """Calculates the arc length"""
        a = self.halfAxes[0]
        return a * special.ellipeinc(phi, self.eccentricitySq)



    def getContour(self, nodeNumber=250):
        """Return the countour of the dome

        :param nodeNumber: number of nodes used
        :return: vectors x,r: x is increasing, r starts at cylinder radius decreasing
        """
        arcLen = self._getPolarOpeningArcLenEllipse()
        if self.aIsDomeLength:
            arcLengths = np.linspace(0, arcLen, nodeNumber)
        else:
            endLen = self.getArcLength(np.pi/2)
            arcLengths = np.linspace(arcLen, endLen, int(nodeNumber))
        phis = [self.getPhiByArcLength(length) for length in arcLengths]
        points = self.getPoints(phis)
        if not self.aIsDomeLength:
            points = points[::-1,::-1]
        points[:, 0] = [0, self.rCyl] # due to nummerical inaccuracy
        points[1, -1] = self.rPolarOpening # due to nummerical inaccuracy
        return points


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
        return self.lDome

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


                      rPolarOpening
                         ←-→

                     ..--     --..
    circle 1     .-~               ~-.          rSmall
                /                     \     ↑
               /                       \    |   lConical
              /                         \   ↓
    circle 2 |                           |      rLarge
             |                           |
             |                           |


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

    f = plt.figure()
    de = DomeEllipsoid(20, 10, 1)
    phis = np.linspace(0, np.pi, 5)
    #coords = de.getPoints(phis)
    #print(indent(coords))

    print(de.contourLength)
    print(de.getPhiByArcLength(48.4422411), np.pi)
    print(indent(de.getContour(5)))

    # getCountourConical(20 ,60 ,100 ,40)
    pass
