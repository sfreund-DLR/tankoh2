"""Mechanical calculations of metal tank"""
import numpy as np
from scipy.optimize import minimize_scalar

from tankoh2 import log
from tankoh2.service.exception import Tankoh2Error
from tankoh2.service.utilities import indent
from tankoh2.design.metal.fatigue import getFatigueLifeAircraftTanks


def getMaxWallThickness(*args, **kwargs):
    return getMaxWallThickness2(*args, **kwargs)[0]

def getMaxWallThickness2(pDesign, material, diameter, safetyFactor, pMinOperation = 0.1,
                         cycles = 50000, heatUpCycles=500, scatter = 5, Kt = 5):

    cycles, heatUpCycles = cycles*scatter, heatUpCycles*scatter

    def fatigueLifeFun(thickness):
        stressMax = getStress(pDesign, diameter, thickness)
        stressMin = getStress(pMinOperation, diameter, thickness)
        fl = getFatigueLifeAircraftTanks(material, stressMax, stressMin, cycles, heatUpCycles, Kt)
        return fl

    def fatigueLifeOptFun(thickness):
        return abs(fatigueLifeFun(thickness) - 1)

    f_ty = material['sigma_t_yield']
    f_tu = material['sigma_t']

    pressuresAllowables=[
        (safetyFactor * pDesign, f_tu, 'ultimate'), # ultimate load case
        (1.33 * pDesign, f_ty, 'proof'), # proof pressure, no detrimental damage
        #(2.0 * designPressure, f_tu), # burst load case
    ]


    infoStr = []
    thkStaticStrengths = []
    for pressure, strength, name in pressuresAllowables:
        thk = getWallThickness(material, pressure, diameter, strength)
        thkStaticStrengths.append(thk)
        infoStr.append([f'Thicknesses according to {name} pressure [mm]', thk])
    thkStaticStrength = np.max(thkStaticStrengths)

    fatigueLife = fatigueLifeFun(thkStaticStrength)
    infoStr.append([f'Initial fatigue life [lifes]', fatigueLife])
    thkFatigue = thkStaticStrength
    fatigueFac = 1.
    if fatigueLife > 1:
        # structure is prone to fatigue failure, update thickness
        res = minimize_scalar(fatigueLifeOptFun, bounds=[thkFatigue, thkFatigue*10],
                              method='bounded', options={'xatol':1e-3})
        thkFatigue = res.x
        if not res.success:
            raise Tankoh2Error('Thickness optimization for fatigue did not succeeded successfully')
        fatigueLife = fatigueLifeFun(thkFatigue)
        fatigueFac = thkFatigue / thkStaticStrength
        infoStr.append([f'Final fatigue life [lifes]', fatigueLife])
        infoStr.append(['Final thickness updated due to fatigue [mm]', thkFatigue])
        infoStr.append(['Fatigue Factor [-]', fatigueFac])

    log.info('\n'+indent(infoStr))
    return thkFatigue, fatigueFac


def getStress(pressure, diameter, wallThickness):
    """Calculate tangential stress according to eq. 2.7 in

        Schwaigerer, Siegfried. Festigkeitsberechnung: im Dampfkessel-, Behälter-und Rohrleitungsbau, 2013

    :param pressure: burst pressure of the tank [MPa]
    :param diameter: diameter of the tank [m]
    :param wallThickness: thickness of the tank wall [m]
    :return: tangential stress [MPa]
    """
    daByDi = (diameter+wallThickness) / diameter
    sigUMax = pressure * (daByDi ** 2 + 1) / (daByDi ** 2 - 1)
    sigUMin = pressure * (1 + 1) / (daByDi ** 2 - 1)
    sigLMax = pressure / (daByDi ** 2 - 1)
    sigRMax = -pressure * (daByDi ** 2 - 1) / (daByDi ** 2 - 1)
    sigRMin = -pressure * (1 - 1) / (daByDi ** 2 - 1)
    sigEq1 = 1/np.sqrt(2) * np.sqrt((sigUMax-sigLMax)**2+(sigLMax-sigRMin)**2+(sigRMin-sigUMax)**2)
    sigEq2 = pressure * np.sqrt(3) * daByDi ** 2 / (daByDi ** 2 - 1)
    sig = pressure * (diameter + wallThickness) / 2 / wallThickness
    return sig



def getWallThickness(material, pressure, diameter, strength = None):
    """Calculate wall thickness of a metal tank
    According to

        Dampfkesselausschuss, D. Technische Regeln für Dampfkessel; Verband der TÜV e.V.: Berlin, Germany, 2010

    :param material: dict describing material properties like those in tankoh2.design.metal.material
    :param pressure: pressure of the tank [MPa]
    :param diameter: diameter of the tank [m]
    :return: tank metal wall thickness [m]
    """

    sigma_t = material['sigma_t'] if strength is None else strength
    we = material['weldEfficiency']
    c1 = material['c1']
    c2 = material['c2']

    thk = pressure * diameter / (we * (2 * sigma_t - pressure)) + c1 + c2

    return thk

