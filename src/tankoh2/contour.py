"""methods for liners and domes"""

import numpy as np

from tankoh2 import pychain
from tankoh2.exception import Tankoh2Error
from tankoh2.utilities import updateName, copyAsJson


# #########################################################################################
# Create Liner
# #########################################################################################

def getReducedDomePoints(contourFilename, spacing, contourOutFilename=None):
    # load contour from file
    Data = np.loadtxt(contourFilename)
    if 1:
        contourPoints = np.abs(Data)
        contourPoints[:, 0] -= contourPoints[0, 0]
        # reduce points
        redContourPoints = contourPoints[::spacing, :]
        if not np.allclose(redContourPoints[-1, :], contourPoints[-1, :]):
            redContourPoints = np.append(redContourPoints, [contourPoints[-1, :]], axis=0)
        if contourOutFilename:
            np.savetxt(contourOutFilename, redContourPoints, delimiter=',')
        Xvec, rVec = redContourPoints[:, 0], redContourPoints[:, 1]

    else:
        Xvec = abs(Data[:, 0])
        Xvec = Xvec - Xvec[0]
        rVec = abs(Data[:, 1])

        # reduce data points
        log.info(len(Xvec) - 1)
        index = np.linspace(0, dpoints * int((len(Xvec) / dpoints)), int((len(Xvec) / dpoints)) + 1, dtype=np.int16)

        arr = [len(Xvec) - 1]
        index = np.append(index, arr)

        Xvec = Xvec[index]
        rVec = rVec[index]

        # save liner contour for loading in mikroWind
        with open(fileNameReducedDomeContour, "w") as contour:
            for i in range(len(Xvec)):
                contour.write(str(Xvec[i]) + ',' + str(rVec[i]) + '\n')
    return Xvec, rVec

def getDome(cylinderRadius, polarOpening, domeType=pychain.winding.DOME_TYPES.ISOTENSOID,
            x=None, r=None):
    """

    :param cylinderRadius: radius of the cylinder
    :param polarOpening: polar opening
    :param domeType: pychain.winding.DOME_TYPES.ISOTENSOID or pychain.winding.DOME_TYPES.CIRCLE
    :param x: x-coordinates of a custom dome contour
    :param r: radius-coordinates of a custom dome contour. r[0] starts at cylinderRadius
    """
    # build  dome
    dome = pychain.winding.Dome()
    dome.buildDome(cylinderRadius, polarOpening, domeType)
    if x is not None and r is not None:
        if not np.allclose(r[0], cylinderRadius):
            raise Tankoh2Error('cylinderRadius and r-vector do not fit')
        dome.setPoints(x, r)
    return dome

def getLiner(dome, length, linerFilename=None, linerName=None):
    """Creates a liner
    :param dome: dome instance
    :param length: zylindrical length of liner
    :param linerFilename: if given, the liner is saved to this file for visualization in µChainWind
    :param linerName: name of the liner written to the file
    :return:
    """
    # create a symmetric liner with dome information and cylinder length
    liner = pychain.winding.Liner()
    # spline for winding calculation is left on default of 1.0
    liner.buildFromDome(dome, length, 1.0)

    if linerFilename:
        liner.saveToFile(linerFilename)
        updateName(linerFilename, linerName, ['liner'])
        copyAsJson(linerFilename, 'liner')
        liner = pychain.winding.Liner()
        liner.loadFromFile(linerFilename)
    return liner

