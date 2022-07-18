import numpy as np


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
