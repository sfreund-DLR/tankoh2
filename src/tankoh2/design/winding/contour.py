"""methods for liners and domes"""

import numpy as np


from tankoh2 import pychain
from tankoh2 import log
from tankoh2.geometry.geoutils import contourLength
from tankoh2.service.exception import Tankoh2Error
from tankoh2.design.winding.windingutils import copyAsJson, updateName
from tankoh2.geometry.dome import validDomeTypes



def domeContourLength(dome):
    """Returns the contour length of a dome"""
    return contourLength(dome.getXCoords(), dome.getRCoords())


def getDome(cylinderRadius, polarOpening, domeType = None, x=None, r=None):
    """creates a µWind dome

    :param cylinderRadius: radius of the cylinder
    :param polarOpening: polar opening radius
    :param domeType: pychain.winding.DOME_TYPES.ISOTENSOID or pychain.winding.DOME_TYPES.CIRCLE
    :param x: x-coordinates of a custom dome contour
    :param r: radius-coordinates of a custom dome contour. r[0] starts at cylinderRadius
    """
    if domeType is None:
        domeType = pychain.winding.DOME_TYPES.ISOTENSOID
    elif isinstance(domeType, str):
        #domeType = domeType.lower()
        if domeType == 'isotensoid_MuWind':
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
            raise Tankoh2Error(f'polarOpening {polarOpening} and smallest given radius {r[-1]} do not fit')
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
    
    polarOpeningRadius = dome.polarOpening
    scaleFittingRadii = 1.
    for fitting in [liner.getFitting(True), liner.getFitting(False)]:
        fitting.r0 = polarOpeningRadius / 2 * scaleFittingRadii
        fitting.r1 = polarOpeningRadius * scaleFittingRadii
        fitting.rD = polarOpeningRadius + polarOpeningRadius * scaleFittingRadii
        fitting.rebuildFitting()

    if linerFilename and linerName:
        liner.saveToFile(linerFilename)
        updateName(linerFilename, linerName, ['liner'])
        copyAsJson(linerFilename, 'liner')      
        liner.loadFromFile(linerFilename)
        
    return liner