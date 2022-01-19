import numpy as np

from tankoh2.exception import Tankoh2Error
from tankoh2.service.pyhsicalprops import rhoLh2, g


def getHydrostaticPressure(tankLocation, length, diameter, baffleDist = None):
    """Calculate hydrostatic pressure according to CS 25.963 (d)
    :param tankLocation: location of tank ['wing_no_engine', 'wing_at_engine', 'fuselage']
    :param length: inner length of tank [mm]
    :param diameter: inner diameter of tank [mm]
    :param baffleDist: distance of horizontal baffles dividing the tank in length direction [mm]
    :return: hydrostatic pressure [MPa]
    """
    validLocations = ['wing_no_engine', 'wing_at_engine', 'fuselage']
    if tankLocation not in validLocations:
        raise Tankoh2Error(f'Only {validLocations} allowed for '
                           f'parameter wingOrFuselage. Got "{tankLocation}"')

    if baffleDist is not None:
        length = baffleDist
    length, diameter = length / 1000, diameter / 1000  # convert to [m]
    rho = rhoLh2(21)
    # 25.963 (d)(1)
    # loadFac: forward, inboard/outboard, downward
    loadFac = np.array([9., 3., 6] if tankLocation == 'fuselage' else [4.5, 1.5, 6])
    lengths = np.array([length, diameter, diameter])
    hPressured1 = loadFac * lengths * rho * g

    # 25.963 (d)(2)(ii)(A)
    # not applied, in this calculation it is always equal or  greater than 25.963 (d)(2)(ii)(B)
    # might be different if dynamic sloshing is considered

    # 25.963 (d)(2)(ii)(B)
    loadFac = np.array([9., 1.5, 6] if tankLocation == 'wing_at_engine' else [0, 0, 0])
    lengths = np.array([length, diameter, diameter * 0.85])
    hPressured2iiB = loadFac * lengths * rho * g

    hPressure = np.max(np.max([hPressured1, hPressured2iiB])) / 1e6
    return hPressure