"""Utility functions for design"""

import numpy as np
from scipy import optimize

from tankoh2.service.physicalprops import rhoLh2ByPSaturation, rhoGh2
from tankoh2.design.existingdesigns import allArgs, defaultDesign
from tankoh2.geometry.dome import getDome
from tankoh2.geometry.liner import Liner


def getLengthRadiusFromVolume(
        volume,
        lcylByR = float(allArgs[allArgs['name']=='lcylByR']['default']),
        domeLengthByR = float(allArgs[allArgs['name']=='domeLengthByR']['default']),
        polarOpeningRadius = float(allArgs[allArgs['name']=='polarOpeningRadius']['default']),
        mode = 'accurate',
        domeType = allArgs[allArgs['name']=='domeType']['default'].to_list()[0],
        linerThickness = allArgs[allArgs['name']=='linerThickness']['default'].to_list()[0],
):
    """Calculate cylindrical length and radius of the liner outer contour from required volume
    :param volume: volume [mm**3]
    :param lcylByR: cylindrical length by cylindrical radius
    :param domeLengthByR: dome length by cylindrical radius
    :param polarOpeningRadius: polar opening radius [mm]
    :param mode: [quick, accurate] Quick does not consider the polar opening reducing the effective dome vol
    :param domeType: type of dome
    :param linerThickness: thickness of the liner
    :return: radius, length
    """
    def getVol(rCyl):
        if polarOpeningRadius > rCyl:
            return volume
        rCyl = rCyl[0]
        dome = getDome(rCyl, polarOpeningRadius, domeType,  rCyl * domeLengthByR)
        liner = Liner(dome, rCyl * lcylByR)
        if linerThickness > 1e-8:
            liner = liner.getLinerResizedByThickness(-1*linerThickness)
        return abs(liner.volume - volume)

    if mode == 'quick':
        radius = np.cbrt(volume / (np.pi*(4/3*domeLengthByR+lcylByR)))
    else:
        res = optimize.minimize(getVol, np.cbrt(volume*3/4/np.pi), bounds=((polarOpeningRadius*1.5, np.inf),))
        radius = res.x[0]
    length = radius*lcylByR
    return radius, length


def getRequiredVolume(lh2Mass, operationalPressure, maxFill=defaultDesign['maxFill'], roh=None, temperature=defaultDesign['temperature']):
    """Calculate volume according to mass and operational pressure according to Brewer ch. 4.4.1
    :param lh2Mass: mass of lh2 [kg]
    :param operationalPressure: operational pressure [MPa]
    :param maxFill: max fill level. Brewer uses 1/(1+0.0072 [volumetric allowance]) for this
    :param roh: density of lh2/gh2 [kg/m^3]
    :param temperature: storage temperature, liquid if under 33K
    :return: volume [m**3]
    """
    if roh is None and temperature:
        if temperature < 33:
            roh = rhoLh2ByPSaturation(operationalPressure)  # roh at 22K
        else:
            maxFill = 1
            roh = rhoGh2(operationalPressure, temperature)#[0]
    v = lh2Mass / roh
    v *= 1 / maxFill
    return v


def getMassByVolume(lh2Volume, operationalPressure, maxFill=defaultDesign['maxFill'], roh=None, temperature=defaultDesign['temperature']):
    """Calculate mass according to volume and operational pressure
    :param lh2Volume: volume of the tank [m**3]
    :param operationalPressure: operational pressure [MPa]
    :param maxFill: max fill level. Brewer uses 1/(1+0.0072 [volumetric allowance]) for this
    :param roh: density of lh2/gh2 [kg/m^3]
    :param temperature: storage temperature, liquid if under 33K
    :return: volume [m**3]
    """
    if roh is None and temperature:
        if temperature < 33:
            roh = rhoLh2ByPSaturation(operationalPressure)  # roh at 22K
        else:
            maxFill = 1
            roh = rhoGh2(operationalPressure, 273 + 20)
    m = lh2Volume * roh * maxFill
    return m



if __name__ == '__main__':
    #print(getLengthRadiusFromVolume(0.11893647322374*1e9, polarOpeningRadius=15.))
    #print(getLengthRadiusFromVolume(0.2079145*1e9, polarOpeningRadius=20))
    print(getMassByVolume(1301.602703/1000, 70, temperature=300))
