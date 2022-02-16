"""Mechanical calculations of metal tank"""


def getWallThickness(material, burstPressure, diameter):
    """Calculate wall thickness of a metal tank
    According to

        Dampfkesselausschuss, D. Technische Regeln für Dampfkessel; Verband der TÜV e.V.: Berlin, Germany, 2010

    :param material: dict describing material properties like those in tankoh2.design.metal.material
    :param burstPressure: burst pressure of the tank [MPa]
    :param diameter: diameter of the tank [m]
    :return: tank metal wall thickness [m]
    """

    sigma_t = material['sigma_t']
    we = material['weldEfficiency']
    c1 = material['c1']
    c2 = material['c2']

    thk = burstPressure * diameter /(we * (2 * sigma_t - burstPressure)) + c1 + c2

    return thk


