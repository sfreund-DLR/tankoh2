"""solver related methods"""

import numpy as np
import pandas as pd

from tankoh2 import pychain, log
from tankoh2.design.winding.winding import windLayer, windHoopLayer


targetFuncNames = ['max puck', 'max puck at last crit location', 'puck sum', 'mass',
                   'strain diff', 'strain diff at last crit location']
resultNames = targetFuncNames + ['maxPuckIndex', 'maxStrainDiffIndex']


def getMaxPuckByAngle(angle, args):
    """Sets the given angle, winding sim, puck analysis

    :return: maximum puck fibre failure"""
    return getMaxPuckLocalPuckMassIndexByAngle(angle, args)[0]


def getWeightedTargetFuncByAngle(angle, args):
    """Sets the given angle, winding sim, puck analysis

    :return: maximum puck fibre failure"""
    return np.sum(getMaxPuckLocalPuckMassIndexByAngle(angle, args)[:-2])


def getMaxPuckLocalPuckMassIndexByAngle(angle, kwArgs):
    """Sets the given angle, winding sim, puck analysis

    :return: maximum puck fibre failure"""
    vessel, layerNumber, puckProperties = kwArgs['vessel'], kwArgs['layerNumber'], kwArgs['puckProperties']
    if hasattr(angle, '__iter__'):
        angle = angle[0]
    if angle is not None:
        log.debug(f'Layer {layerNumber}, wind angle {angle}')
        actualPolarOpening = windLayer(vessel, layerNumber, angle)
        if actualPolarOpening is np.inf:
            return np.inf, 0
    result = getMaxPuckLocalPuckMass(kwArgs)
    log.debug(f'Layer {layerNumber}, angle {angle}, ' +
              str([(name, str(val)) for name, val in zip(resultNames, result)]))
    return result


def getMaxPuckByShift(shift, args):
    """Sets the given hoop shift, winding sim, puck analysis

    :return: maximum puck fibre failure
    """
    return getMaxPuckLocalPuckMassIndexByShift(shift, args)[0]


def getWeightedTargetFuncByShift(angle, args):
    """Sets the given angle, winding sim, puck analysis

    :return: maximum puck fibre failure"""
    return np.sum(getMaxPuckLocalPuckMassIndexByShift(angle, args)[:-2])


def getMaxPuckLocalPuckMassIndexByShift(shifts, kwArgs):
    """Sets the given hoop shift, winding sim, puck analysis

    :param shifts:
    :param args:
    :return: tuple, (maximum puck fibre failure, index of max FF/IFF)
    """
    vessel, layerNumber, puckProperties = kwArgs['vessel'], kwArgs['layerNumber'], kwArgs['puckProperties']
    windHoopLayer(vessel, layerNumber, *shifts)
    actualPolarOpening = windLayer(vessel, layerNumber)
    if actualPolarOpening is np.inf:
        return np.inf, 0
    result = getMaxPuckLocalPuckMass(kwArgs)
    log.debug(f'Layer {layerNumber}, hoop shifts {shifts}, ' +
              str([(name, str(val)) for name, val in zip(resultNames, result)]))
    return result


def getMaxPuckLocalPuckMass(kwArgs, puckAndStrainDiff=None, scaleTf=True):
    """Return maximum fibre failure of the all layers after winding the given angle
    :param kwArgs:
    :param puckAndStrainDiff: tuple (puck values, strain Diff)
    :param scaleTf:
    :return:
    """
    vessel, layerNumber, puckProperties = kwArgs['vessel'], kwArgs['layerNumber'], kwArgs['puckProperties']
    burstPressure, useIndices = kwArgs['burstPressure'], kwArgs['useIndices']
    useFibreFailure, symmetricContour = kwArgs['useFibreFailure'], kwArgs['symmetricContour']
    elemIdxPuckMax, elemIdxBendMax = kwArgs['elemIdxPuckMax'], kwArgs['elemIdxBendMax']
    targetFuncScaling = kwArgs['targetFuncScaling']
    if puckAndStrainDiff is None:
        puck, strainDiff = getPuckStrainDiff(vessel, puckProperties, burstPressure, useIndices,
                                             symmetricContour, useFibreFailure, True)
    else:
        puck, strainDiff = puckAndStrainDiff
    maxPerElement = puck.max(axis=1)
    maxPuckIndex = maxPerElement.idxmax()

    maxStrainDiff = strainDiff.max()
    maxStrainDiffIndex = np.argmax(strainDiff)
    strainDiffAtCritIdx = strainDiff[elemIdxBendMax]

    maxPuck = maxPerElement.max()
    puckAtCritIdx = maxPerElement[elemIdxPuckMax]
    puckSum = np.sum(maxPerElement)

    layMass = vessel.getVesselLayer(layerNumber).getVesselLayerPropertiesSolver().getWindingLayerResults().fiberMass

    tfValues = np.array([maxPuck, puckAtCritIdx, puckSum, layMass, maxStrainDiff, strainDiffAtCritIdx])
    if scaleTf:
        tfValues *= targetFuncScaling
    return *tfValues, maxPuckIndex, maxStrainDiffIndex


def getPuckStrainDiff(vessel, puckProperties, burstPressure, useIndices=None,
                      symmetricContour=True, useFibreFailure=True, useMeridianStrain=True):
    """returns the puck values and strain diffs for the actual

    """
    results = getLinearResults(vessel, puckProperties, burstPressure, useIndices=useIndices,
                               symmetricContour=symmetricContour)
    puck = results[7] if useFibreFailure else results[8]
    strainDiff = abs(results[3] - results[4]) if useMeridianStrain else abs(results[5] - results[6])
    return puck, strainDiff


def getLinearResults(vessel, puckProperties, burstPressure, useIndices=None,
                     symmetricContour=True):
    """Calculates puck results and returns them as dataframe

    :param vessel: µWind vessel instance
    :param puckProperties: µWind puckProperties instance
    :param burstPressure: burst pressure in MPa
    :param useIndices: list of element indicies that should be used for evaluation
    :param symmetricContour:
    :return: 2-tuple with dataframes (fibre failure, inter fibre failure)
    """
    puck = pychain.failure.PuckFailureCriteria2D()
    puck.setPuckProperties(puckProperties)
    shellModel, shellModel2 = _getShellModels(vessel, burstPressure, symmetricContour)

    # get stresses in the fiber COS (elemNr, layerNr)
    S11, S22, S12 = shellModel.calculateLayerStressesBottom()
    if not symmetricContour:
        stressesMandrel2 = shellModel2.calculateLayerStressesBottom()
        S11 = np.append(S11[::-1], stressesMandrel2[0], axis=0)
        S22 = np.append(S22[::-1], stressesMandrel2[1], axis=0)
        S12 = np.append(S12[::-1], stressesMandrel2[2], axis=0)
    numberOfElements, numberOfLayers = S11.shape
    stresses = np.zeros((numberOfElements,numberOfLayers, 6))
    stresses[:, :, 0] = S11
    stresses[:, :, 1] = S22
    stresses[:, :, 5] = S12
    stressVec = pychain.utility.StressVector()
    puckFF, puckIFF = [], []
    if useIndices is not None:
        useIndicesSet = set(useIndices)
    for elemIdx, elemStresses in enumerate(stresses):
        if useIndices is not None and elemIdx not in useIndicesSet:
            failures = np.zeros((numberOfLayers,2))
        else:
            failures = []
            for layerStress in elemStresses:
                if np.all(abs(layerStress)<1e-8): # for hoop layers, the stress in dome region is 0
                    failures.append([0.,0.])
                else:
                    stressVec.fromVector(layerStress)
                    puckResult = puck.getExposure(stressVec)
                    failures.append([puckResult.f_FF, puckResult.f_E0_IFF])
            failures = np.array(failures)
        puckFF.append(failures[:,0])
        puckIFF.append(failures[:,1])
    columns = [f'puckFFlay{layerNumber}' for layerNumber in range(numberOfLayers)]
    puckFF = pd.DataFrame(np.array(puckFF), columns=columns)
    columns = [f'puckIFFlay{layerNumber}' for layerNumber in range(numberOfLayers)]
    puckIFF = pd.DataFrame(np.array(puckIFF), columns=columns)

    epsAxialBot = shellModel.getEpsAxialBottom(0)
    epsAxialTop = shellModel.getEpsAxialTop(0)
    epsCircBot = shellModel.getEpsCircBottom(0)
    epsCircTop = shellModel.getEpsCircTop(0)
    if not symmetricContour:
        epsAxialBot = np.append(epsAxialBot[::-1], shellModel2.getEpsAxialBottom(0))
        epsAxialTop = np.append(epsAxialTop[::-1], shellModel2.getEpsAxialTop(0))
        epsCircBot = np.append(epsCircBot[::-1], shellModel2.getEpsCircBottom(0))
        epsCircTop = np.append(epsCircTop[::-1], shellModel2.getEpsCircTop(0))
    if useIndices is not None:
        zeroIndices = np.array([idx not in useIndicesSet for idx in range(len(epsAxialBot))])
        epsAxialBot[zeroIndices] = 0.
        epsAxialTop[zeroIndices] = 0.
        epsCircBot[zeroIndices] = 0.
        epsCircTop[zeroIndices] = 0.
    return S11, S22, S12, epsAxialBot, epsAxialTop, epsCircBot, epsCircTop, puckFF, puckIFF



def _getShellModels(vessel, burstPressure, symmetricContour):
    # build shell model for internal calculation
    converter = pychain.mycrofem.VesselConverter()
    shellModel = converter.buildAxShellModell(vessel, burstPressure, True, True)  # pressure in MPa (bar / 10.)
    shellModel2 = None if symmetricContour else converter.buildAxShellModell(vessel, burstPressure, True, False)

    # run linear solver
    linerSolver = pychain.mycrofem.LinearSolver(shellModel)
    linerSolver.run(True)
    if not symmetricContour:
        linerSolver = pychain.mycrofem.LinearSolver(shellModel2)
        linerSolver.run(True)
    return shellModel, shellModel2

