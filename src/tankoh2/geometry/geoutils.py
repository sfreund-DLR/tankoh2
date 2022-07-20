import numpy as np
import pandas as pd
from scipy.interpolate import interp1d


def getReducedDomePoints(contourFilename, spacing=1, contourOutFilename=None):
    """

    :param contourFilename: path to file. The file has 2 rows with x and r coordinates
    :param spacing:
    :param contourOutFilename:
    :return: [x,r]
    """
    # load contour from file
    contourPoints = np.abs(np.loadtxt(contourFilename))
    contourPoints[:, 0] -= contourPoints[0, 0]
    # reduce points
    redContourPoints = contourPoints[::spacing, :]
    if not np.allclose(redContourPoints[-1, :], contourPoints[-1, :]):
        redContourPoints = np.append(redContourPoints, [contourPoints[-1, :]], axis=0)
    if contourOutFilename:
        np.savetxt(contourOutFilename, redContourPoints, delimiter=',')
    Xvec, rVec = redContourPoints[:, 0], redContourPoints[:, 1]

    return np.array([Xvec, rVec])


def contourLength(x, r):
    """Returns the contour length of a dome"""
    contourCoords = np.array([x, r]).T
    contourDiffs = contourCoords[1:,:] - contourCoords[:-1]
    contourLength = np.sum(np.linalg.norm(contourDiffs, axis=1))
    return contourLength


def getRadiusByShiftOnContour(radii, lengths, startRadius, shift):
    """Calculates a shift along the mandrel surface in the dome section

    :param radii: vector of radii
    :param lengths: vector of lengths with same length as radii
    :param startRadius: radius on mandrel where the shift should be applied
    :param shift: (Scalar or Vector) Shift along the surface. Positive values shift in fitting direction
    :return: radius
    """
    # x-coordinate, radius, length on mandrel
    coords = pd.DataFrame(np.array([radii, lengths]).T, columns=['r', 'l'])

    # cut section of above 0.9*maxRadius
    maxR = coords['r'].max()
    coords = coords[coords['r'] < 0.9 * maxR]

    # invert index order
    coordsRev = coords.iloc[::-1]

    # get initial length and perform shift
    lengthInterp = interp1d(coordsRev['r'], coordsRev['l'], fill_value='extrapolate', assume_sorted=True)
    startLength = lengthInterp(startRadius)
    targetLength = startLength + shift

    # get target radius
    radiusInterpolation = interp1d(coords['l'], coords['r'], fill_value='extrapolate', assume_sorted=True)
    targetRadius = radiusInterpolation(targetLength)
    return targetRadius


def getCoordsShiftFromLength(x, r, l, startLength, shift):
    """Calculates a shift along the mandrel surface in the dome section

    :param x: vector with x-coords
    :param r: vector with radius-coords
    :param l: vector with contour length-coords
    :param startLength: length on mandrel where the shift should be applied
    :param shift: (Scalar or Vector) Shift along the surface. Positive values shift in fitting direction
    :return: 4-tuple with scalar or vector entires depending on parameter "shift"
        x-coordinate, radius, length, nearestElementIndices

    """
    targetLength = startLength + shift

    targetRadius = np.interp(targetLength, l, r)
    targetX = np.interp(targetLength, l, x)
    elementLengths = (l[:-1]+l[1:]) / 2
    elementLengths = np.array([elementLengths] * len(targetLength))
    indicies = np.argmin(np.abs(elementLengths.T - targetLength), axis=0)
    return targetX, targetRadius, targetLength, indicies