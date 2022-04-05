"""Fatigue analysis

The fatigue analysis is based on a stress-life approach.
It uses the given load cycles and fits of SN-curves to calculate the
number of cycles to failure for each type of load cycle.
This number is accumulated to a structural damage factor using the palmgren-miner rule.
"""


import numpy as np

from tankoh2 import log
from tankoh2.service.exception import Tankoh2Error
from tankoh2.service.physicalprops import MPaToPsiFac



def getFatigueLifeAircraftTanks(material, sigMaxOperation, sigMinOperation,
                                flightCycles, heatUpCycles, Kt = None):
    """Calculate fatigue life for aircraft applications using LH2 tanks

    :param material: material dict as defined in tankoh2.design.metal.material
    :param sigMaxOperation: max stress at max operating pressure [MPa]
    :param sigMinOperation: max stress at min operating pressure [MPa]
    :param flightCycles: number of flight cycles
    :param heatUpCycles: number of cycles where a cryo tank is heated up.
        This leads to the pressure cycle [0, pMaxOperation]
    :param Kt:
    :return: fatigue life factor. If it is larger than 1, the fatigue life is exceeded
    """
    sigMax = [sigMaxOperation] * 2
    sigMin = [sigMinOperation, 0.]
    occurences = [flightCycles, heatUpCycles]

    return getFatigueLife(material, sigMax, sigMin, occurences, Kt)



def getFatigueLife(material, sigMax, sigMin, occurences, Kt = None):
    """Assess fatigue life"""
    p1, p2, p3, p4 = material['SN_parameters']
    Kt_used = material['Kt_used'] # Kt where the parameters where taken
    if Kt is None:
        KtCorrection = None
    else:
        if np.allclose(Kt_used, 1):
            KtCorrection = Kt
        else:
            KtCorrection = None

    critCycles = getCyclesToFailure(sigMax, sigMin, p1, p2, p3, p4, KtCorrection=KtCorrection)
    return stressLifeMinerRule(occurences, critCycles)


def stressLifeMinerRule(occurences, critCycles):
    """Calculate the damage factor for each load cycles and the total damage factor according to miner rule

    .. math::
        c = \\sum\\frac{n_i}{n_{ic}}

    :param occurences: list of occurences of the related serr
    :param critCycles: list with number of cycles to failue. Same length as occurences

    """
    occurences = np.array(occurences)
    critCycles = np.array(critCycles)

    damageFac = occurences / critCycles
    log.debug(f'Damage of each amplitude+occurence {damageFac}')

    return np.sum(damageFac, axis=len(damageFac.shape) - 1)


def getCyclesToFailure(sigMax, sigMin, p1, p2, p3, p4, KtCorrection=None):
    """Evaluates S-N equation with p1-p4 for Kt==1. The function is modified accordingly to the given Kt

    Calculates number of cycles to failure

    .. math::
        N_f = 10 ^ {(p_{1 Kt}+p_2\\cdot log_{10}((\\sigma_{max}\\cdot (1-R)^{p_3})-p_4)}

    with

    .. math::
        p_{1 Kt} = p1 + p2 \\cdot log_{10} K_t

    .. math::
        R = \\frac{\\sigma_{min}}{\\sigma_{max}}

    :param sigMax: max stress [MPa]
    :param sigMin: min stress [MPa]
    :param p1: first parameter. At Kt==1. If given p1 is for Kt!=1, then use p1 and Kt=1 as input
    :param p2: see equation
    :param p3: see equation
    :param p4: see equation
    :param KtCorrection: stress intensity factor correction from Kt==1 to KtCorrection
        Pilkey, Walter D.; Pilkey, Deborah F.; Peterson, Rudolph E.: Peterson's stress concentration factors
    :return: number of cycles to failure
    """
    sigMin, sigMax = np.array(sigMin), np.array(sigMax)
    if np.any(sigMax<1e-20):
        raise Tankoh2Error(f'sigMax must be positive but got: {sigMax}')

    R = sigMin / sigMax

    if np.any(R > 1):
        raise Tankoh2Error(f'sigMin and sigMax do not match. sigMin {sigMin}, sigMax {sigMax}')

    if KtCorrection is not None:
        p1 = p1 + p2 * np.log10(KtCorrection)
    return np.power(10, p1 + p2 * np.log10((sigMax * MPaToPsiFac * (1 - R) ** p3) - p4))






