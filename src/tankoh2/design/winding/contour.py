"""methods for liners and domes"""

import numpy as np


from tankoh2 import pychain
from tankoh2 import log
from tankoh2.service.exception import Tankoh2Error
from tankoh2.design.winding.windingutils import copyAsJson, updateName


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

def domeContourLength(dome):
    """Returns the contour length of a dome"""
    contourCoords = np.array([dome.getXCoords(), dome.getRCoords()]).T
    contourDiffs = contourCoords[1:,:] - contourCoords[:-1]
    contourLength = np.sum(np.linalg.norm(contourDiffs, axis=1))
    return contourLength

def getDome(cylinderRadius, polarOpening, domeType = None, x=None, r=None, lDomeHalfAxis = None,
            rSmall = None, lCone = None, lRad = None, xApex = None, yApex = None):
    """creates a µWind dome

    :param cylinderRadius: radius of the cylinder
    :param polarOpening: polar opening radius
    :param domeType: pychain.winding.DOME_TYPES.ISOTENSOID or pychain.winding.DOME_TYPES.CIRCLE
    :param x: x-coordinates of a custom dome contour
    :param r: radius-coordinates of a custom dome contour. r[0] starts at cylinderRadius
    """
    validDomeTypes = ['isotensoid', 'circle',
                      'ellipse', # allowed by own implementation in tankoh2.geometry.contour
                      'conical',
                      ]
    if domeType is None:
        domeType = pychain.winding.DOME_TYPES.ISOTENSOID
    elif isinstance(domeType, str):
        domeType = domeType.lower()
        if domeType == 'isotensoid':
            domeType = pychain.winding.DOME_TYPES.ISOTENSOID
        elif domeType == 'circle':
            domeType = pychain.winding.DOME_TYPES.CIRCLE
        elif domeType in validDomeTypes:
            if x is None or r is None:
                raise Tankoh2Error(f'For dome type "{domeType}", the contour coordinates x, r must be given.')
            domeType = pychain.winding.DOME_TYPES.CIRCLE
        else:
            raise Tankoh2Error(f'wrong dome type "{domeType}". Valid dome types: {validDomeTypes}')
    # build  dome
    dome = pychain.winding.Dome()
    try:
        dome.buildDome(cylinderRadius, polarOpening, domeType)
    except IndexError as e:
        log.error(f'Got an error creating the dome with these parameters: '
                  f'{(cylinderRadius, polarOpening, domeType)}')
        raise

    if x is not None and r is not None:
        if not np.allclose(r[0], cylinderRadius):
            raise Tankoh2Error('cylinderRadius and r-vector do not fit')
        if not np.allclose(r[-1], polarOpening):
            print(r[-1], polarOpening)
            raise Tankoh2Error('polarOpening and r-vector do not fit')
        if len(r) != len(x):
            raise Tankoh2Error(f'x and r-vector do not have the same size. len(r): len(x): {len(r), len(x)}')
        dome.setPoints(x, r)
    return dome

def getLiner(dome, length, linerFilename=None, linerName=None, dome2 = None, nodeNumber = 500):
    """Creates a liner
    :param dome: dome instance
    :param length: zylindrical length of liner
    :param linerFilename: if given, the liner is saved to this file for visualization in µChainWind
    :param linerName: name of the liner written to the file
    :param dome2: dome of type pychain.winding.Dome
    :param nodeNumber: number of nodes of full contour. Might not exactly be matched due to approximations
    :return: liner of type pychain.winding.Liner
    """
        
    # create a symmetric liner with dome information and cylinder length
    liner = pychain.winding.Liner()

    # spline for winding calculation is left on default of 1.0
    if dome2:
        contourLength = length + domeContourLength(dome) + domeContourLength(dome2)
    else:
        contourLength = length / 2 + domeContourLength(dome)  # use half model (one dome, half cylinder)
        nodeNumber //= 2
    deltaLengthSpline = contourLength / nodeNumber  # just use half side

    if dome2 is not None:
        log.info("Create unsymmetric vessel")
        liner.buildFromDomes(dome, dome2, length, deltaLengthSpline)
    else:
        log.info("Create symmetric vessel")
        liner.buildFromDome(dome, length, deltaLengthSpline)
    
    if linerFilename:
        liner.saveToFile(linerFilename)
        updateName(linerFilename, linerName, ['liner'])
        copyAsJson(linerFilename, 'liner')      
        liner.loadFromFile(linerFilename)
        
    return liner

    
    