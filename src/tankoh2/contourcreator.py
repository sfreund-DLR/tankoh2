"""This module creates dome contours"""

import numpy as np
from matplotlib import pyplot as plt


from tankoh2.exception import Tankoh2Error
from tankoh2.service import indent
from tankoh2.service import log




def getCountourConical(rPolarOpening, rSmall, rLarge, lConical, domeType ='circular'):
    """Calculates the countour of a dome and a attached conical structure

    ATTENTION:
    - This method is not yet finished!
    - It continas some hardcoded values like xOffset, rOffset
    - dydxConical must be iteratively identified which changes xOffset, rOffset.
      Or a fully analytical solution must be found
    - Only tested for dydxConical=1
    - extend for other dome types


                      rPolarOpening
                         ←-→

                     ..--     --..
    circle 1     .-~               ~-.          rSmall
                /                     \     ↑
               /                       \    |   lConical
              /                         \   ↓
    circle 2 |                           |      rLarge
             |                           |
             |                           |


    :return: vectors x,r: r starts at zylinder radius decreasing, x is increasing
    """
    allowedDomeTypes = ['circular']
    if domeType not in allowedDomeTypes:
        raise Tankoh2Error(f'Wrong input for domeType "{domeType}". Valid types: {allowedDomeTypes}')
    if not all([val >0 for val in [rSmall, rLarge, lConical]]):
        raise Tankoh2Error('All input values must be larger than zero')
    if rSmall >= rLarge:
        raise Tankoh2Error('rSmall >= rLarge')

    numPoints = 40
    # 1: circle at polar opening
    # find location where dr/dx of circular section is same dr/dx of conical section
    dydxConical = (rLarge - rSmall) / lConical
    # drdx=-x/np.sqrt(rSmall**2-x**2)
    x1SameDydx = dydxConical * rSmall
    rCirc1 = np.sqrt(x1SameDydx**2 + rSmall**2)
    alphaSmallR = np.arccos(x1SameDydx /rCirc1)
    alphaPolarOpening = np.arcsin(rPolarOpening /rCirc1)
    angles = np.linspace(alphaPolarOpening, alphaSmallR, numPoints)
    x1 = np.cos(angles) * rCirc1
    x1 = 2 * x1[-1] - x1  # x must be increasing
    r1 = np.sin(angles) * rCirc1

    # 2: conical section
    xOffset, rOffset  = 100,100
    x2, r2 = np.linspace([x1[-1], r1[-1]], [x1[-1]+xOffset, r1[-1]+rOffset], numPoints, False).T[:,1:]

    # 3: circle at zylinder
    angles = np.linspace(alphaSmallR, np.pi/2, numPoints)
    x3 = np.cos(angles) * rCirc1
    x3 = 2 * x3[0] - x3
    r3 = np.sin(angles) * rCirc1

    # put it together
    x = np.concatenate([x1, x2, x3])
    r = np.concatenate([r1, r2, r3])
    print(indent(np.array([x,r]).T, delim='  '))

    r = r[::-1]
    x = x[::-1]
    x = x[0] - x

    if 0:
        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)
        ax.plot(x, r)
        plt.show()

    log.error('This method is not fully implemented and uses hardcoded values')
    return x, r









if __name__ == '__main__':
    getCountourConical(20 ,60 ,100 ,40)
