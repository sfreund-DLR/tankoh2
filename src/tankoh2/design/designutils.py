"""Utility functions for design"""

import numpy as np
from scipy import optimize

from tankoh2.service.pyhsicalprops import rhoLh2ByP, rhoGh2NonCryo
from tankoh2.design.existingdesigns import allArgs
from tankoh2.geometry.dome import getDome
from tankoh2.geometry.liner import Liner


def getLengthRadiusFromVolume(
        volume,
        lcylByR = float(allArgs[allArgs['name']=='lcylByR']['default']),
        domeLengthByR = float(allArgs[allArgs['name']=='domeLengthByR']['default']),
        polarOpeningRadius = float(allArgs[allArgs['name']=='polarOpeningRadius']['default']),
        mode = 'accurate',
        domeType = allArgs[allArgs['name']=='domeType']['default'].to_list()[0],
):
    """Calculate cylindrical length and radius from volume
    :param volume: volume [mm**3]
    :param lcylByR: cylindrical length by cylindrical radius
    :param domeLengthByR: dome length by cylindrical radius
    :param polarOpeningRadius: polar opening radius [mm]
    :param mode: [quick, accurate] Quick does not consider the polar opening reducing the effective dome vol
    :param domeType: type of dome
    :return:
    """
    def getVol(rCyl):
        if polarOpeningRadius > rCyl:
            return volume
        rCyl = rCyl[0]
        dome = getDome(rCyl, polarOpeningRadius, domeType,  rCyl * domeLengthByR)
        liner = Liner(dome, rCyl * lcylByR)
        return abs(liner.volume - volume)

    if mode == 'quick':
        radius = np.cbrt(volume / (np.pi*(4/3*domeLengthByR+lcylByR)))
    else:
        res = optimize.minimize(getVol, np.cbrt(volume*3/4/np.pi), bounds=((polarOpeningRadius*1.5, np.inf),))
        radius = res.x[0]
    length = radius*lcylByR
    return radius, length


def getRequiredVolume(lh2Mass, operationalPressure, maxFill = 0.9, roh=None, lh2OrCh2='lh2'):
    """Calculate volume according to mass and operational pressure according to Brewer ch. 4.4.1
    :param lh2Mass: mass of lh2 [kg]
    :param operationalPressure: operational pressure [MPa]
    :param maxFill: max fill level. Brewer uses 1/(1+0.0072 [volumetric allowance]) for this
    :param roh: density of lh2/gh2 [kg/m^3]
    :param lh2OrCh2: switch which storage system shall be used [lh2, gh2]
    :return: volume [m**3]
    """
    if roh is None and lh2OrCh2:
        if lh2OrCh2 == 'lh2':
            roh = rhoLh2ByP(operationalPressure)  # roh at 22K
        else:
            roh = rhoGh2NonCryo(operationalPressure, 273 + 20)[0]
    v = lh2Mass / roh
    v *= 1 / maxFill
    return v



if __name__ == '__main__':
    print(getLengthRadiusFromVolume(0.11893647322374*1e9, polarOpeningRadius=15.))
    print(getLengthRadiusFromVolume(0.2079145*1e9, polarOpeningRadius=20))
