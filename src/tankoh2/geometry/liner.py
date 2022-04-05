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

    def getLinerResizedByThickness(self, thickness):
        """return a liner that has a resized geometry by given thickness"""
        dome = self.dome.getDomeResizedByThickness(thickness)
        dome2 = None if self.dome2 is None else self.dome2.getDomeResizedByThickness(thickness)
        return Liner(dome, self.lcyl, dome2)

    def getWallVolume(self, wallThickness):
        """Calculate the volume of the material used

        :param wallThickness: thickness of the dome material
        :return: scalar, wall volume
        """
        otherLiner = self.getLinerResizedByThickness(wallThickness)
        return otherLiner.volume - self.volume

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

    def getContour(self):
        """Return the countour of the liner

        :return: vectors x,r: starting at symmetry plane: r decreasing, x is increasing
        """
        pointsDome = self.dome.getContour(20)
        stepping = scipy.linalg.norm(pointsDome[:,0] - pointsDome[:,1], axis=0)
        linerPointCount = int(self.lcyl / 2 // stepping)
        pointsDome[0,:] += (pointsDome[0,0] + self.lcyl/2)  # move dome start to half liner length
        pointsLiner = [np.linspace(0., self.lcyl/2, linerPointCount, False), [self.rCyl]*linerPointCount]
        points = np.append(pointsLiner, pointsDome, axis=1)
        return points

    def plotContour(self):
        """creates a plot of the outer liner contour"""
        points = self.getContour()
        plotContour(True, '', points[0,:], points[1,:])


