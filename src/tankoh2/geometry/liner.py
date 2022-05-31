"""Defines liner based on a cylindrical section and domes"""

import numpy as np
import scipy

from tankoh2.service.plot.generic import plotContour


class Liner():
    """Defines liner based on a cylindrical section and domes"""

    def __init__(self, dome, lcyl, dome2 = None):
        self.dome = dome
        self.lcyl = lcyl
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
        domeVolume = self.dome.volume + (self.dome2.volume if self.dome2 else self.dome.volume)
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
        domeLength = self.dome.domeLength + (self.dome2.domeLength if self.dome2 else self.dome.domeLength)
        return self.lcyl + domeLength

    @property
    def area(self):
        """calc dome area numerically by slices of circular conical frustums"""
        domeArea = self.dome.area + (self.dome2.area if self.dome2 else self.dome.area)
        return 2 *np.pi*self.rCyl*self.lcyl + domeArea

    def getContour(self, nodeNumber = 250):
        """Return the countour of the liner

        :param nodeNumber: number of nodes per section (dome, cylindrical part, dome2)
        :return: vectors x,r: starting at symmetry plane: r decreasing, x is increasing
        """
        symmetricLiner = self.dome2 is None
        linerLenFac = 2 if symmetricLiner else 1 # only use half cylindrical length if liner is symmetric
        pointsDome = self.dome.getContour(nodeNumber)

        # switch dome points for left side visualization
        pointsDome[:,:] = pointsDome[:, ::-1] # r
        pointsDome[0, :] = self.dome.domeLength - pointsDome[0, :] # x
        pointsLiner = np.array([np.linspace(0., self.lcyl/linerLenFac, nodeNumber, False) + self.dome.domeLength,
                                [self.rCyl]*nodeNumber])[:,1:]
        points = np.append(pointsDome, pointsLiner, axis=1)
        if not symmetricLiner:
            pointsDome2 = self.dome2.getContour(nodeNumber)
            # move dome2 start to dome+liner length
            pointsDome2[0,:] += (pointsDome2[0,0] + self.lcyl + self.dome.domeLength)
            points = np.append(points, pointsDome2, axis=1)
        return points

    def plotContour(self, nodeNumber):
        """creates a plot of the outer liner contour"""
        points = self.getContour(nodeNumber)
        plotContour(True, '', points[0,:], points[1,:])


if __name__ == '__main__':
    from tankoh2.geometry.dome import DomeEllipsoid
    dome = DomeEllipsoid(100, 50, 10)
    dome2 = DomeEllipsoid(100, 100, 10)



    liner = Liner(dome, 20, dome2)
    liner.plotContour(100)



