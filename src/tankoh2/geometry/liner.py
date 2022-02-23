"""Defines liner based on a cylindrical section and domes"""

import numpy as np
import scipy

from tankoh2.service.plot.generic import plotContour


class Liner():
    """Defines liner based on a cylindrical section and domes"""

    def __init__(self, dome, lcyl, dome2 = None):
        self.dome = dome
        self.lcyl = lcyl
        if dome2:
            # turn dome 2 to fit geometry
            pass
        self.dome2 = dome2

    @property
    def rCyl(self):
        return self.dome.rCyl

    @property
    def _cylVolume(self):
        """calc volume of cylindrical part"""
        return np.pi * self.rCyl ** 2 * self.lcyl

    @property
    def volume(self):
        """calc volume of the liner"""
        domeVolume = (self.dome.volume + self.dome2.volume) if self.dome2 else 2 * self.dome.volume
        return self._cylVolume + domeVolume

    def getWallVolume(self, wallThickness):
        """Calculate the volume of the material used

        :param wallThickness: thickness of the dome material
        :return: scalar, wall volume
        """
        if self.dome2:
            domeWallVol = (self.dome.getWallVolume(wallThickness) + self.dome2.getWallVolume(wallThickness))
        else:
            domeWallVol = 2 * self.dome.getWallVolume(wallThickness)
        biggerCylVol = np.pi * (self.rCyl+wallThickness) ** 2 * self.lcyl
        return biggerCylVol-self._cylVolume + domeWallVol

    @property
    def length(self):
        """Returns the length of the dome, also considering the polar opening"""
        domeLength = (self.dome.domeLength + self.dome2.domeLength) if self.dome2 else 2 * self.dome.domeLength
        return self.lcyl + domeLength

    @property
    def area(self):
        """calc dome area numerically by slices of circular conical frustums"""
        domeArea = (self.dome.area + self.dome2.area) if self.dome2 else 2 * self.dome.area
        return 2 *np.pi*self.rCyl*self.lcyl + domeArea

    def plotContour(self):
        """creates a plot of the outer liner contour"""
        pointsDome = self.dome.getContour(20)
        stepping = scipy.linalg.norm(pointsDome[:,0] - pointsDome[:,1], axis=0)
        linerPointCount = int(self.lcyl / 2 // stepping)
        pointsDome[0,:] += (pointsDome[0,0] + self.lcyl/2)  # move dome start to half liner length
        pointsLiner = [np.linspace(0., self.lcyl/2, linerPointCount, False), [self.rCyl]*linerPointCount]
        points = np.append(pointsLiner, pointsDome, axis=1)
        plotContour(True, '', points[0,:], points[1,:])


