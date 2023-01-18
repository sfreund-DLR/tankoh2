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


def getFatigueLifeMetalTankLevel(material, sigMaxOperation, sigMinOperation,
                                 flightCycles, heatUpCycles, Kt=None):
    """Calculate fatigue life for aircraft applications using LH2 tanks

    :param material: material dict as defined in tankoh2.design.metal.material
    :param sigMaxOperation: max stress at max operating pressure [MPa]
    :param sigMinOperation: max stress at min operating pressure [MPa]
    :param flightCycles: number of flight cycles
    :param heatUpCycles: number of cycles where a cryo tank is heated up.
        This leads to the pressure cycle [0, pMaxOperation]
    :param Kt: stress concentration factor
    :return: fatigue life factor. If it is larger than 1, the fatigue life is exceeded
    """
    sigMax = [sigMaxOperation] * 2
    sigMin = [sigMinOperation, 0.]
    occurences = [flightCycles, heatUpCycles]

    return getFatigueLifeMetal(material, sigMax, sigMin, occurences, Kt)


def getFatigueLifeMetal(material, sigMax, sigMin, occurences, Kt=None):
    """Assess fatigue life calculating the damage for each amplitude, use miner rule for damage accumulation

    A1 and A4 are corrected according to the given Kt value.
    The new A1 and A4 is obtained by considering that the new Smax is (Kt/Kt_curve) x Smax in the S-N equation

    .. math::
        A_{1 Kt} = A_1 + A_2 \\cdot log_{10} \\frac{K_t}{K_t^{Curve}}

    .. math::
        A_{4 Kt} = A_1 + A_2 \\cdot log_{10} K_t

    :math:`K_t^{Curve}` ist the :math:`K_t` where the SN_parameters (defined in material) are measured

    :param material: material dict as defined in tankoh2.design.metal.material
    :param sigMax: list of maximal stresses
    :param sigMin: list of minimal stresses
    :param occurences: list of occurences
    :param Kt: stress intensity factor
        Pilkey, Walter D.; Pilkey, Deborah F.; Peterson, Rudolph E.: Peterson's stress concentration factors
    :return: accumulated damage factor. If this value is above 1, the structure is seen to be failed
    """
    A1, A2, A3, A4 = material['SN_parameters']
    Kt_curve = material['Kt_curve']  # Kt where the parameters where taken
    if Kt is not None:
        if Kt < Kt_curve:
            log.warning(f'Scaling the measured SN curves from higher Kt {Kt_curve} to lower Kt {Kt} is not '
                        f'conservative. Please check if you can use SN-curves with a Kt smaller or equal'
                        f'than the requested Kt')
        A1, A4 = correctSnParameters(A1, A2, A4, Kt_curve, Kt)

    critCycles = getCyclesToFailure(sigMax, sigMin, A1, A2, A3, A4)
    return stressLifeMinerRule(occurences, critCycles)


def correctSnParameters(A1, A2, A4, Kt_curve, Kt):
    A1 = A1 + A2 * np.log10(Kt / Kt_curve)
    A4 = Kt_curve * A4 / Kt
    return A1, A4


def stressLifeMinerRule(occurences, critCycles):
    """Calculate the damage factor for each load cycles and the total damage factor according to miner rule

    .. math::
        c = \\sum\\frac{n_i}{n_{ic}}

    :param occurences: list of occurences of the related serr
    :param critCycles: list with number of cycles to failue. Same length as occurences
    :return: accumulated damage factor. If this value is above 1, the structure is seen to be failed
    """
    occurences = np.array(occurences)
    critCycles = np.array(critCycles)

    damageFac = occurences / critCycles
    log.debug(f'Damage of each amplitude+occurence {damageFac}')

    return np.sum(damageFac, axis=len(damageFac.shape) - 1)


def getCyclesToFailure(sigMax, sigMin, A1, A2, A3, A4):
    """Evaluates S-N equation with p1-p4 for Kt==1. The function is modified accordingly to the given Kt

    Calculates number of cycles to failure according to

        MMPDS (2012): MMPDS Metallic Materials Properties Development and Standardization.
        Chapter 9.6.1.4

    .. math::
        log N_f = A_1+A_2\\cdot log_{10}(\\sigma_{max}\\cdot (1-R)^{A_3}-A_4)

    with

    .. math::
        R = \\frac{\\sigma_{min}}{\\sigma_{max}}

    .. note::

        The calculation of the cycles to failure is highly dependend on

        - Valid test data basis which created A1-A4.
          Caution should be taken, when interpolating and especially extrapolating these values
        - A coorect load assumption, since this is not linear.
          Little increases in load can have a significant effect on the cycles to failure

        PLease refer to the literature above for more details.

    :param sigMax: max stress [MPa]
    :param sigMin: min stress [MPa]
    :param A1: see equation
    :param A2: see equation
    :param A3: see equation
    :param A4: see equation
    :return: number of cycles to failure
    """
    sigMin, sigMax = np.array(sigMin), np.array(sigMax)
    if np.any(sigMax < 1e-20):
        raise Tankoh2Error(f'sigMax must be positive but got: {sigMax}')

    R = sigMin / sigMax

    if np.any(R > 1):
        raise Tankoh2Error(f'sigMin and sigMax do not match. sigMin {sigMin}, sigMax {sigMax}')

    return np.power(10, A1 + A2 * np.log10((sigMax * MPaToPsiFac * (1 - R) ** A3) - A4))
