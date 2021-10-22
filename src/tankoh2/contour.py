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
        if not np.allclose(r[-1], polarOpening):
            raise Tankoh2Error('polarOpening and r-vector do not fit')
        dome.setPoints(x, r)
    return dome

def getLiner(dome, length, linerFilename=None, linerName=None, Symmetric=True, dome2 = None):
    """Creates a liner
    :param dome: dome instance
    :param length: zylindrical length of liner
    :param linerFilename: if given, the liner is saved to this file for visualization in µChainWind
    :param linerName: name of the liner written to the file
    :return:
    """
        
    # create a symmetric liner with dome information and cylinder length
    liner = pychain.winding.Liner()
    print(dir(pychain.winding.Liner))
      
    # spline for winding calculation is left on default of 1.0
    r = dome.cylinderRadius
    lengthEstimate = (np.pi * r + length) # half circle + cylindrical length
    desiredNodeNumber = 500
    deltaLengthSpline = lengthEstimate / desiredNodeNumber / 2 # just use half side
    #deltaLengthSpline = np.min([5.0, deltaLengthSpline]) # min since muwind has maximum of 5        
    
    if Symmetric == False:
        print("Creat unsymmetric vessel")            
        if dome2 != None:
            liner.buildFromDomes(dome, dome2, length, deltaLengthSpline)
        else:
            print("Error: contour of second dome is missing!")
    else:
        print("Creat symmetric vessel")
        liner.buildFromDome(dome, length, deltaLengthSpline)
    

    if linerFilename:        
        liner.saveToFile(linerFilename)
        updateName(linerFilename, linerName, ['liner'])
        copyAsJson(linerFilename, 'liner')      
        liner.loadFromFile(linerFilename)
        
    return liner

# def getLengthContourPath(domeContourFilename, r1, r2, ninc):
#     """get length of a contour path on dome contour between polar opening r1 and r2 
# 
#     :param domeContourFilename: txt file of dome contour with secifications as in getReducedDomePoints
#     :param r1: first polar opening radius
#     :param r2: second polar oping radius
#     :param nink: number of radius increments for calculation countour path length
#     """
# 
#     xvec, rvec = getReducedDomePoints(domeContourFilename,
#                                 1, None)
#     
#     ir1 = rvec.index(r1)
#     ir2 = rvec.index(r2)
#     
#     i1 = np.min(ir1, ir2)
#     i2 = np.max(ir1, ir2)
#     
#     dinc = int(abs(i2-i1))/ninc
#     
#     arc = 0.
#     for i in range(i1, i2+1, dinc):
#         arc = arc + (rvec(i1)-r1)**2. + (xvec(i1)-x1)**2.
#     
#     return arc 
#         
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    