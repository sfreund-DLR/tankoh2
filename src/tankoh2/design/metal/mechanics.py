"""Mechanical calculations of metal tank"""

import tankoh2.design.designmetal.material as materials
from tankoh2.service.exception import Tankoh2Error

def getWallThickness(materialName, burstPressure, diameter):
    """Calculate wall thickness of a metal tank
    According to

        Dampfkesselausschuss, D. Technische Regeln für Dampfkessel; Verband der TÜV e.V.: Berlin, Germany, 2010

    :param materialName: name of the material used - must be a dict located in tankoh2.design.metal.material
    :param burstPressure: burst pressure of the tank [MPa]
    :param diameter: diameter of the tank [m]
    :return: tank metal wall thickness [m]
    """
    try:
        material = getattr(materials, materialName)
    except AttributeError:
        raise Tankoh2Error(f'The given material "{materialName}" is not defined in '
                           f'tankoh2.design.metal.material')

    sigma_t = material['sigma_t']
    we = material['weldEfficiency']
    c1 = material['c1']
    c2 = material['c2']

    thk = burstPressure * diameter /(we * (2 * sigma_t - burstPressure)) + c1 + c2

    return thk


