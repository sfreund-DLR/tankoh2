"""This module creates dome contours"""
from abc import ABCMeta, abstractmethod

import numpy as np
from scipy import special
from scipy import optimize
import mpl_toolkits.mplot3d.axes3d as axes3d
from scipy.integrate import quad
import statistics

from tankoh2.service.utilities import importFreeCad

importFreeCad()

import FreeCAD
import Part
from Part import LineSegment, Point
import Sketcher

from tankoh2.service.exception import Tankoh2Error
from tankoh2 import log
from tankoh2.service.plot.generic import plotContour

validDomeTypes = ['isotensoid', 'circle',  # also CAPITAL letters are allowed
                  'ellipse', 'conical', # allowed by own implementation in tankoh2.geometry.contour
                  1, 2,  # types from µWind
                  ]

def getDomeType(domeType):
    """returns the usable dome tpye

    :param domeType: dome type - one of validDomeTypes
    :return:
    """
    if domeType is None:
        domeType = 'isotensoid'
    elif isinstance(domeType, str):
        domeType = domeType.lower()
    elif isinstance(domeType, int) and domeType in validDomeTypes:
        domeType = {1:'isotensoid', 2:'circle'}[domeType]
    else:
        raise Tankoh2Error(f'wrong dome type "{domeType}". Valid dome types: {validDomeTypes}')
    return domeType


def getDome(cylinderRadius, polarOpening, domeType = None, lDomeHalfAxis = None, delta1 = None, rSmall = None, lCone = None, lRad = None, xApex = None, yApex = None, lCyl = None, lDome2 = None):
    """creates a dome analog to tankoh2.design.winding.contour.getDome()

    :param cylinderRadius: radius of the cylinder
    :param polarOpening: polar opening radius
    :param domeType: pychain.winding.DOME_TYPES.ISOTENSOID or pychain.winding.DOME_TYPES.CIRCLE
    :param lDomeHalfAxis: ellipse half axis describing the dome length for elliptical domes
    :param rConeSmall: small radius of conical tank section
    :param rConeLarge: large radius of conical tank section
    :param lCone: length of conical tank section
    :param lRadius: length of radius between conical and cylindrical section
    :param xApex: difference of the radius from conical to convex shape
    """
    domeType = getDomeType(domeType)
    # build  dome
    if domeType == 'ellipse':
        dome = DomeEllipsoid(cylinderRadius, lDomeHalfAxis, polarOpening)
    if domeType == 'conical':

        rCyl = designArgs['dcyl'] / 2
        rSmall = rCyl - designArgs['alpha'] * rCyl
        lDome1 = designArgs['delta1'] * rSmall
        lDome2 = designArgs['delta2'] * rCyl
        lRad = designArgs['beta'] * designArgs['gamma'] * designArgs['dcyl']
        lCone = designArgs['beta'] * designArgs['dcyl'] - lRad

        dome = DomeConical(cylinderRadius, polarOpening, delta1, rSmall, lCone, lRad, xApex, yApex, lCyl, lDome2, '')
    elif domeType == 'circle':
        dome = DomeSphere(cylinderRadius, polarOpening)
    elif domeType == 'isotensoid':
        from tankoh2.design.winding.contour import getDome as getDomeMuWind
        domeMuWind = getDomeMuWind(cylinderRadius, polarOpening, domeType)
        x, r = domeMuWind.getXCoords(), domeMuWind.getRCoords()
        dome = DomeGeneric(x,r)

    return dome

def flipContour(x,r):
    """moves the given contour from left to right side and vice versa"""
    return np.array([np.min(x) + np.max(x) - x[::-1], r[::-1]])

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

    def plotContour(self, nodeNumber = 100, ax = None, **mplKwargs):
        """creates a plot of the outer liner contour. For more details see tankoh2..service.plot.generic"""
        points = self.getContour(nodeNumber)
        if ax:
            plotContour(False, '', points[0,:], points[1,:], ax=ax, plotContourCoordinates=False, **mplKwargs)
        else:
            plotContour(True, '', points[0,:], points[1,:], **mplKwargs)

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

class DomeConical(AbstractDome):
    """Calculcate ellipsoid contour with conical tank

    :param rSmall: small radius of conical tank section
    :param rCyl: large radius of conical tank section
    :param lCone: length of conical tank section
    :param rPolarOpening: polar opening radius. The polar opening is only accounted for in getContour
    :param lRadius: length of radius between conical and cylindrical section
    :param xApex: x-position of the apex
    :param yApex: y-position of the apex

    ::

        |              rPolarOpening
        |                 ←--→
        |             ..--    --..              ↑
        |         .-~              ~-.          |   lDomeHalfAxis
        |        /                    \         ↓
        |       /←---------→           \        ↑
        |      /   rSmall               \       |
        |     /                          \      |   lCone
        |    /                            \     |
        |   /                              \    ↓
        |  :                                :   ↑   lRadius
        | |←---------------→                |   ↓
        |       rLarge
    """

    def __init__(self, volume, dCyl, rPolarOpening, alpha, beta, gamma, delta1, delta2, xApex, yApex, title):

        AbstractDome.__init__(self)
        self._rSmall = dCyl / 2 - alpha * dCyl / 2
        self._rCyl = dCyl / 2
        self._delta1 = delta1
        self._lDome2 = delta2 * self._rCyl
        self._rPolarOpening = rPolarOpening
        self._lRad = beta * gamma * dCyl
        self._lCone = beta * dCyl - self._lRad
        self._volume = volume
        self._xApex = xApex
        self._yApex = yApex
        self.title = title

        #self.halfAxes = (self._lDomeHalfAxis, self._rCyl) if self._lDomeHalfAxis > self._rSmall else (self._rSmall, self._lDomeHalfAxis)

    # def __init__(self, rCyl, rPolarOpening, delta1, rSmall, lCone, lRad, xApex, yApex, volume, lDome2, title):
    #     AbstractDome.__init__(self)
    #     # if rPolarOpening >= rSmall:
    #     #     raise Tankoh2Error('Polar opening should not be greater or equal to the dome radius')
    #     # if rSmall > rCyl:
    #     #     raise Tankoh2Error('Small radius should not be larger than cylindrical radius')
    #     # if xApex > lCone:
    #     #     raise Tankoh2Error('The position of the apex must be within the conical part')
    #     self._rSmall = rSmall
    #     self._rCyl = rCyl
    #     self._lCone = lCone
    #     self._rPolarOpening = rPolarOpening
    #     self._delta1 = delta1
    #     self._lRad = lRad
    #     self._xApex = xApex
    #     self._yApex = yApex
    #     self._volume = volume
    #     self._lDome2 = lDome2
    #     self.title = title

        # self.halfAxes = (self.lDomeHalfAxis, self._rCyl) if self.lDomeHalfAxis > self._rSmall else (self._rSmall, self.lDomeHalfAxis)

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
    def rSmall(self):
        return self._rSmall

    @property
    def lDomeHalfAxis(self):
        return self._lDomeHalfAxis

    @property
    def volume(self):
        """calc dome volume numerically by slices of circular conical frustums"""
        return self.getVolume(self.getContour())

    def getDomeResizedByThickness(self, thickness):
        """return a dome that has a resized geometry by given thickness"""
        return DomeConical(self._rCyl + thickness, self.rSmall + thickness, self.rPolarOpening)

    def getGeometry(self):

        FreeCAD.newDocument(self.title)
        tank = FreeCAD.activeDocument()
        tank.addObject('Sketcher::SketchObject', 'Sketch')
        sketch = FreeCAD.getDocument(self.title).getObject('Sketch')

        if self._delta1 == 1:

            sketch.addGeometry(Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(0, self._rCyl / 3, 0), FreeCAD.Vector(0, 0, 1), self._rCyl / 2), 1, 2), False)
            sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(self._lRad, self._rCyl, 0), FreeCAD.Vector(1.5 * (self._lRad + self._lCone), 1.5 * self._rSmall, 0)), False)
            sketch.addGeometry(Part.ArcOfCircle(Part.Circle(App.Vector(self._lRad + self._lCone, 0, 0), App.Vector(0, 0, 1), self._rSmall), 0.1, 1.2), False)

            sketch.addConstraint(Sketcher.Constraint('Tangent', 0, 1, 1, 1))
            sketch.addConstraint(Sketcher.Constraint('Tangent', 1, 2, 2, 2))

            sketch.addConstraint(Sketcher.Constraint('Vertical', 0, 2, 0, 3))

            sketch.addConstraint(Sketcher.Constraint('DistanceX', -1, 1, 0, 2, 0))
            sketch.addConstraint(Sketcher.Constraint('DistanceX', -1, 1, 0, 1, self._lRad))
            sketch.addConstraint(Sketcher.Constraint('DistanceX', -1, 1, 1, 2, self._lRad + self._lCone))

            sketch.addConstraint(Sketcher.Constraint('DistanceY', -1, 1, 2, 3, 0))
            sketch.addConstraint(Sketcher.Constraint('DistanceY', -1, 1, 0, 2, self._rCyl))
            sketch.addConstraint(Sketcher.Constraint('DistanceY', 1, 2, 0, 2, self._rCyl - self._rSmall))
            sketch.addConstraint(Sketcher.Constraint('DistanceY', -1, 1, 2, 1, self._rPolarOpening))

        else:

            sketch.addGeometry(Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(0, self._rCyl / 3, 0), FreeCAD.Vector(0, 0, 1), self._rCyl / 2), 1, 2), False)
            sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(self._lRad, self._rCyl, 0), FreeCAD.Vector(1.5 * (self._lRad + self._lCone), 1.5 * self._rSmall, 0)), False)
            sketch.addGeometry(Part.ArcOfEllipse(Part.Ellipse(FreeCAD.Vector(self._lRad + self._lCone, 1.2 * self._rSmall, 0), FreeCAD.Vector(self._lRad + self._lCone + self._rSmall, 0, 0), FreeCAD.Vector(self._lRad + self._lCone, 0, 0)), 0.5, 1.5), False)
            sketch.exposeInternalGeometry(2)
            sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(self._lRad + self._lCone, self._rSmall, 0), FreeCAD.Vector(self._lRad + self._lCone + self._rSmall, 0, 0)), False)

            sketch.addConstraint(Sketcher.Constraint('Tangent', 0, 1, 1, 1))
            sketch.addConstraint(Sketcher.Constraint('Tangent', 1, 2, 2, 2))

            sketch.addConstraint(Sketcher.Constraint('Coincident', 7, 1, 3, 2))
            sketch.addConstraint(Sketcher.Constraint('Coincident', 7, 2, 4, 1))
            sketch.addConstraint(Sketcher.Constraint('Angle', 3, 2, 7, 1, np.arctan(self._delta1)))

            sketch.addConstraint(Sketcher.Constraint('Vertical', 0, 2, 0, 3))
            sketch.addConstraint(Sketcher.Constraint('Vertical', 3))

            sketch.addConstraint(Sketcher.Constraint('DistanceX', -1, 1, 0, 2, 0))
            sketch.addConstraint(Sketcher.Constraint('DistanceX', -1, 1, 0, 1, self._lRad))
            sketch.addConstraint(Sketcher.Constraint('DistanceX', -1, 1, 1, 2, self._lRad + self._lCone))

            sketch.addConstraint(Sketcher.Constraint('DistanceY', -1, 1, 2, 3, 0))
            sketch.addConstraint(Sketcher.Constraint('DistanceY', -1, 1, 0, 2, self._rCyl))
            sketch.addConstraint(Sketcher.Constraint('DistanceY', 1, 2, 0, 2, self._rCyl - self._rSmall))

            geometry = sketch.getPropertyByName('Geometry')

            sketch.addConstraint(Sketcher.Constraint('DistanceX', 2, 1, 4, 2, geometry[2].MinorRadius - (np.sqrt((1 - (self._rPolarOpening ** 2 / geometry[2].MajorRadius ** 2)) * geometry[2].MinorRadius ** 2))))

        FreeCAD.getDocument(self.title).saveAs(u"D:/bier_ju/06 FreeCAD/tank_shapes/tank")

        geometry = sketch.getPropertyByName('Geometry')

        return geometry

    def getContourLength(self):

        geometry = DomeConical.getGeometry(self)

        radiusArcLength = np.arcsin(geometry[0].StartPoint[0] / geometry[0].Radius) * geometry[0].Radius
        coneArcLength = np.sqrt((geometry[1].EndPoint[0] - geometry[1].StartPoint[0]) ** 2 + (geometry[1].EndPoint[1] - geometry[1].StartPoint[1]) ** 2)

        angle1 = np.arctan(geometry[2].EndPoint[1] / (geometry[2].EndPoint[0] - geometry[2].Center[0]))
        angle2 = np.arctan(geometry[2].StartPoint[1] / (geometry[2].StartPoint[0] - geometry[2].Center[0]))
        t = np.linspace(angle1, angle2, 100)
        def fun(t):
            return np.sqrt(geometry[2].MinorRadius ** 2 * np.cos(t) ** 2 + geometry[2].MajorRadius ** 2 * np.sin(t) ** 2)
        domeArcLength = quad(fun, angle1, angle2)[0]

        totalArcLength = radiusArcLength + coneArcLength + domeArcLength

        return totalArcLength

    def getContour(self, nodeNumber = 1000):

        geometry = DomeConical.getGeometry(self)

        if self._delta1 == 1:

            end = np.sqrt(geometry[2].Radius ** 2 - self._rPolarOpening ** 2) + geometry[2].Center[0]

            xRadius = np.linspace(0, geometry[0].StartPoint[0], round((nodeNumber + 2) * (geometry[0].StartPoint[0] - geometry[0].EndPoint[0]) / end))
            rRadius = np.sqrt(geometry[0].Radius ** 2 - (xRadius - geometry[0].Center[0]) ** 2) + geometry[0].Center[1]

            xCone = np.linspace(geometry[1].StartPoint[0], geometry[1].EndPoint[0], round((nodeNumber + 2) * (geometry[1].EndPoint[0] - geometry[1].StartPoint[0]) / end))
            rCone = ((geometry[1].EndPoint[1] - geometry[1].StartPoint[1]) / (geometry[1].EndPoint[0] - geometry[1].StartPoint[0]) * xCone + (geometry[1].StartPoint[1] - (geometry[1].EndPoint[1] - geometry[1].StartPoint[1]) / (geometry[1].EndPoint[0] - geometry[1].StartPoint[0]) * geometry[1].StartPoint[0]))

            xDome = np.linspace(geometry[2].EndPoint[0], end, (nodeNumber + 2) - round((nodeNumber + 2) * ((geometry[0].StartPoint[0] - geometry[0].EndPoint[0]) / end)) - round(nodeNumber * (geometry[1].EndPoint[0] - geometry[1].StartPoint[0]) / end))
            rDome = np.sqrt(geometry[2].Radius ** 2 - (xDome - geometry[2].Center[0]) ** 2)

        else:

            end = np.sqrt((1 - (self._rPolarOpening ** 2 / geometry[2].MajorRadius ** 2)) * geometry[2].MinorRadius ** 2) + geometry[2].Center[0]

            xRadius = np.linspace(0, geometry[0].StartPoint[0], round((nodeNumber + 2) * (geometry[0].StartPoint[0] - geometry[0].EndPoint[0]) / end))
            rRadius = np.sqrt(geometry[0].Radius ** 2 - (xRadius - geometry[0].Center[0]) ** 2) + geometry[0].Center[1]

            xCone = np.linspace(geometry[1].StartPoint[0], geometry[1].EndPoint[0], round((nodeNumber + 2) * (geometry[1].EndPoint[0] - geometry[1].StartPoint[0]) / end))
            rCone = ((geometry[1].EndPoint[1] - geometry[1].StartPoint[1]) / (geometry[1].EndPoint[0] - geometry[1].StartPoint[0]) * xCone + (geometry[1].StartPoint[1] - (geometry[1].EndPoint[1] - geometry[1].StartPoint[1]) / (geometry[1].EndPoint[0] - geometry[1].StartPoint[0]) * geometry[1].StartPoint[0]))

            xDome = np.linspace(geometry[2].StartPoint[0], end, (nodeNumber + 2) - round((nodeNumber + 2) * ((geometry[0].StartPoint[0] - geometry[0].EndPoint[0]) / end)) - round(nodeNumber * (geometry[1].EndPoint[0] - geometry[1].StartPoint[0]) / end))
            rDome = np.sqrt((1 - ((xDome - geometry[2].Center[0]) ** 2 / geometry[2].MinorRadius ** 2)) * geometry[2].MajorRadius ** 2)

        x = np.concatenate([xRadius, xCone[1:], xDome[1:]])
        r = np.concatenate([rRadius, rCone[1:], rDome[1:]])

        points = np.array([x, r])

        return points

    def getCylLength(self):

        geometry = DomeConical.getGeometry(self)

        def rRadiusFun(xRadius):
            return (np.sqrt(geometry[0].Radius ** 2 - (xRadius - geometry[0].Center[0]) ** 2) + geometry[0].Center[1]) ** 2

        def rConeFun(xCone):
            return (((geometry[1].EndPoint[1] - geometry[1].StartPoint[1]) / (geometry[1].EndPoint[0] - geometry[1].StartPoint[0]) * xCone + (geometry[1].StartPoint[1] - (geometry[1].EndPoint[1] - geometry[1].StartPoint[1]) / (geometry[1].EndPoint[0] - geometry[1].StartPoint[0]) * geometry[1].StartPoint[0]))) ** 2

        xDome2 = np.linspace(0, np.sqrt((1 - self._rPolarOpening ** 2 / self._rCyl ** 2) * self._lDome2 ** 2), 1000)

        def rDome2Fun(xDome2):
            return np.sqrt((1 - ((xDome2 ** 2) / (self._lDome2 ** 2))) * self._rCyl ** 2)

        if self._delta1 == 1:

            def rDome1Fun(xDome):
                return np.sqrt(geometry[2].Radius ** 2 - (xDome - geometry[2].Center[0]) ** 2) ** 2

            volumeConeAndDomes = np.pi * (quad(rRadiusFun, 0, geometry[0].StartPoint[0])[0] + quad(rConeFun, geometry[1].StartPoint[0], geometry[1].EndPoint[0])[0] + quad(rDome1Fun, geometry[2].EndPoint[0], np.sqrt(geometry[2].Radius ** 2 - self._rPolarOpening ** 2) + geometry[2].Center[0])[0] + quad(rDome2Fun, 0, self._lDome2)[0])

        else:

            def rDome1Fun(xDome):
                return (np.sqrt((1 - ((xDome - geometry[2].Center[0]) ** 2 / geometry[2].MinorRadius ** 2)) * geometry[2].MajorRadius ** 2)) ** 2

            volumeConeAndDomes = np.pi * (quad(rRadiusFun, 0, geometry[0].StartPoint[0])[0] + quad(rConeFun, geometry[1].StartPoint[0], geometry[1].EndPoint[0])[0] + quad(rDome1Fun, geometry[2].StartPoint[0], np.sqrt((1 - (self._rPolarOpening ** 2 / geometry[2].MajorRadius ** 2)) * geometry[2].MinorRadius ** 2) + geometry[2].Center[0])[0] + quad(rDome2Fun, 0 , self._lDome2)[0])

        lCyl = (self._volume * 1e9 - volumeConeAndDomes) / (np.pi * self._rCyl ** 2)

        return lCyl

    def getContourTank(self, nodeNumber = 500):

        points = DomeConical.getContour(self)
        lCyl = DomeConical.getCylLength(self)

        x = points[0,:] + lCyl + self._lDome2
        r = points[1,:]

        xCyl = np.linspace(self._lDome2, lCyl + self._lDome2, nodeNumber)
        rCyl = [self._rCyl for i in range(nodeNumber)]

        xDome2 = np.linspace(self._lDome2 - np.sqrt((1 - self._rPolarOpening ** 2 / self._rCyl ** 2) * self._lDome2 ** 2), self._lDome2, nodeNumber)

        rDome2 = np.sqrt((1 - (((xDome2 - self._lDome2) ** 2) / (self._lDome2 ** 2))) * self._rCyl ** 2)

        xTotal = np.concatenate([xDome2, xCyl, x])
        rTotal = np.concatenate([rDome2, rCyl, r])

        points = np.array([xTotal, rTotal])

        return points

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
        if nodeNumber not in self._contourCache:

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
        return self._contourCache[nodeNumber].copy()

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

if __name__ == '__main__':
    import matplotlib.pyplot as plt
    from tankoh2.service.utilities import indent

    if 0:
        dc1 = DomeConical(40, 3000, 40, 0.6, 1.7, 0.2, 1, 0.7, 0, 0, 'tank')
        plottitle = 'Tank'
        parameter = '_test'
        dc1.plotContour()

    elif 0:
        fig, axs = plt.subplots(1, 2, figsize=(17, 5))
        r = 1250
        deltas = np.linspace(0.25, 1, 4, True)
        # https://matplotlib.org/stable/gallery/lines_bars_and_markers/linestyles.html
        linestyles = ["solid", "dashdot", "dashed", "dotted"]
        for delta, linestyle in zip(deltas, linestyles):
            dome = DomeEllipsoid(r, r * delta, r / 10)
            dome.plotContour(ax=axs[0], linestyle=linestyle, color='black', grid=True)

        rFactors = np.linspace(0.8, 1.2, 3, True)
        for rFactor, linestyle in zip(rFactors, linestyles):
            dome = DomeEllipsoid(rFactor * r, r * 0.5, r / 10)
            dome.plotContour(ax=axs[1], linestyle=linestyle, color='black')

    else:
        fig, axs = plt.subplots(1, 2, figsize=(17, 5))
        V = 60 # m^3
        d = 3200 # mm
        rPolar = 50 # mm
        alpha = 0.3
        beta = 1.8
        gamma = 0.3
        delta1 = 0.8
        delta2 = 0.7
        xApex = 0
        yApex = 0

        linestyles = ["solid", "dashdot", "dashed", "dotted"]

        parameters = np.linspace(0.25, 0.75, 3, True)
        titles = ["dome1", "dome2", "dome3"]
        plottitle = 'alpha'
        for parameter, linestyle, title in zip(parameters, linestyles, titles):

            dome = DomeConical(V, d, rPolar, parameter, beta, parameter, delta1, delta2, xApex, yApex, title)
            dome.plotContour(ax=axs[0], linestyle=linestyle, color='black', grid=True)

        parameters = np.linspace(1, 2, 3, True)
        titles = ["dome4", "dome5", "dome6"]
        plottitle = 'beta'
        for parameter, linestyle, title in zip(parameters, linestyles, titles):

            dome = DomeConical(V, d, rPolar, alpha, parameter, gamma, delta1, delta2, xApex, yApex, title)
            dome.plotContour(ax=axs[1], linestyle=linestyle, color='black', grid=True)

    plt.show()