"""Utility functions for design"""

import numpy as np
from scipy import optimize

from tankoh2.service.physicalprops import rhoLh2ByP, rhoGh2NonCryo
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
    :return: radius, length
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


def getRequiredVolume(lh2Mass, operationalPressure, maxFill = 0.9, roh=None, lh2OrGh2='lh2'):
    """Calculate volume according to mass and operational pressure according to Brewer ch. 4.4.1
    :param lh2Mass: mass of lh2 [kg]
    :param operationalPressure: operational pressure [MPa]
    :param maxFill: max fill level. Brewer uses 1/(1+0.0072 [volumetric allowance]) for this
    :param roh: density of lh2/gh2 [kg/m^3]
    :param lh2OrGh2: switch which storage system shall be used [lh2, gh2]
    :return: volume [m**3]
    """
    if roh is None and lh2OrGh2:
        if lh2OrGh2 == 'lh2':
            roh = rhoLh2ByP(operationalPressure)  # roh at 22K
        else:
            roh = rhoGh2NonCryo(operationalPressure, 273 + 20)[0]
    v = lh2Mass / roh
    v *= 1 / maxFill
    return v

def getMassByVolume(lh2Volume, operationalPressure, maxFill = 0.9, roh=None, lh2OrGh2='lh2'):
    """Calculate mass according to volume and operational pressure
    :param lh2Volume: volume of the tank [m**3]
    :param operationalPressure: operational pressure [MPa]
    :param maxFill: max fill level. Brewer uses 1/(1+0.0072 [volumetric allowance]) for this
    :param roh: density of lh2/gh2 [kg/m^3]
    :param lh2OrGh2: switch which storage system shall be used [lh2, gh2]
    :return: volume [m**3]
    """
    if roh is None and lh2OrGh2:
        if lh2OrGh2 == 'lh2':
            roh = rhoLh2ByP(operationalPressure)  # roh at 22K
        else:
            roh = rhoGh2NonCryo(operationalPressure, 273 + 20)[0]
    m = lh2Volume * roh * maxFill
    return m



if __name__ == '__main__':
    #print(getLengthRadiusFromVolume(0.11893647322374*1e9, polarOpeningRadius=15.))
    #print(getLengthRadiusFromVolume(0.2079145*1e9, polarOpeningRadius=20))
    print(getMassByVolume(1301.602703/1000, 70, lh2OrGh2='gh2'))
