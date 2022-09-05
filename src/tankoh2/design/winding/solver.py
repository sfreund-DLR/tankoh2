"""solver related methods"""

import numpy as np
import pandas as pd

from tankoh2 import pychain, log
from tankoh2.design.winding.winding import windLayer
from tankoh2.design.winding.windingutils import getLayerThicknesses


def getMaxPuckByAngle(angle, args):
    """Sets the given angle, winding sim, puck analysis

    :return: maximum puck fibre failure"""
    return getMaxPuckLocalPuckMassIndexByAngle(angle, args)[0]


def getWeightedTargetFuncByAngle(angle, args):
    """Sets the given angle, winding sim, puck analysis

    :return: maximum puck fibre failure"""
    return np.sum(getMaxPuckLocalPuckMassIndexByAngle(angle, args)[:-1])


def getMaxPuckLocalPuckMassIndexByAngle(angle, args):
    """Sets the given angle, winding sim, puck analysis

    :return: maximum puck fibre failure"""
    vessel, layerNumber, puckProperties, burstPressure, _, useFibreFailure, _, _, _, _ = args
    if hasattr(angle, '__iter__'):
        angle = angle[0]
    if angle is not None:
        log.debug(f'Layer {layerNumber}, wind angle {angle}')
        actualPolarOpening = windLayer(vessel, layerNumber, angle)
        if actualPolarOpening is np.inf:
            return np.inf, 0
    maxPuck, puckAtCritIdx, puckSum, layMass, maxIndex = getMaxPuckLocalPuckMass(args)
    failure = 'fibre failure' if useFibreFailure else 'inter fibre failure'
    log.debug(f'Layer {layerNumber}, angle {angle}, max {failure} {maxPuck}, '
              f'{failure} at crit index {puckAtCritIdx}, layer mass {layMass}, index {maxIndex}')
    return maxPuck, puckAtCritIdx, puckSum, layMass, maxIndex


def getMaxPuckByShift(shift, args):
    """Sets the given hoop shift, winding sim, puck analysis

    :return: maximum puck fibre failure
    """
    return getMaxPuckLocalPuckMassIndexByShift(shift, args)[0]


def getWeightedTargetFuncByShift(angle, args):
    """Sets the given angle, winding sim, puck analysis

    :return: maximum puck fibre failure"""
    return np.sum(getMaxPuckLocalPuckMassIndexByShift(angle, args)[:-1])


def getMaxPuckLocalPuckMassIndexByShift(shift, args):
    """Sets the given hoop shift, winding sim, puck analysis

    :param shift:
    :param args:
    :return: tuple, (maximum puck fibre failure, index of max FF/IFF)
    """
    if hasattr(shift, '__iter__'):
        shift = shift[0]
    vessel, layerNumber, puckProperties, burstPressure, _, useFibreFailure, _, _, _, _ = args
    vessel.setHoopLayerShift(layerNumber, shift, True)
    actualPolarOpening = windLayer(vessel, layerNumber)
    if actualPolarOpening is np.inf:
        return np.inf, 0
    maxPuck, puckAtCritIdx, puckSum, layMass, maxIndex = getMaxPuckLocalPuckMass(args)
    failure = 'fibre failure' if useFibreFailure else 'inter fibre failure'
    log.debug(f'Layer {layerNumber}, hoop shift {shift}, max {failure} {maxPuck}, '
              f'{failure} at crit index {puckAtCritIdx}, layer mass {layMass}, index {maxIndex}')
    return maxPuck, puckAtCritIdx, puckSum, layMass, maxIndex



def getMaxPuckLocalPuckMass(args, puck=None, scaleTf=True):
    """Return maximum fibre failure of the all layers after winding the given angle"""
    vessel, layerNumber, puckProperties, burstPressure, useIndices, useFibreFailure, _, symmetricContour, \
        critIdx, targetFuncScaling = args
    if puck is None:
        index = 0 if useFibreFailure else 1
        puck = getLinearResults(
            vessel, puckProperties, burstPressure, useIndices, True, symmetricContour)[index]
    maxPerElement = puck.max(axis=1)
    maxIndex = maxPerElement.idxmax()

    maxPuck = maxPerElement.max()
    puckAtCritIdx = maxPerElement[critIdx]
    puckSum = np.sum(maxPerElement)
    layMass = vessel.getVesselLayer(layerNumber).getVesselLayerPropertiesSolver().getWindingLayerResults().fiberMass

    tfValues = np.array([maxPuck, puckAtCritIdx, puckSum, layMass])
    if scaleTf:
        tfValues *= targetFuncScaling
    return *tfValues, maxIndex


def getLinearResults(vessel, puckProperties, burstPressure, useIndices=None, puckOnly = False,
                     symmetricContour=True):
    """Calculates puck results and returns them as dataframe

    :param vessel: µWind vessel instance
    :param puckProperties: µWind puckProperties instance
    :param layerNumber: 0-based
    :param useIndices: list of element indicies that should be used for evaluation
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
        useIndices = set(useIndices)
    for elemIdx, elemStresses in enumerate(stresses):
        if useIndices is not None and elemIdx not in useIndices:
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
    if puckOnly:
        # if useIndices is not None:
        #     noUseIndices = set(puckFF.index).difference(useIndices)
        #     puckFF.drop(noUseIndices, inplace=True)
        #     puckIFF.drop(noUseIndices, inplace=True)
        return puckFF, puckIFF

    epsAxialBot = shellModel.getEpsAxialBottom(0)
    epsAxialTop = shellModel.getEpsAxialTop(0)
    epsCircBot = shellModel.getEpsCircBottom(0)
    epsCircTop = shellModel.getEpsCircTop(0)
    if not symmetricContour:
        epsAxialBot = np.append(epsAxialBot[::-1], shellModel.getEpsAxialBottom(0))
        epsAxialTop = np.append(epsAxialTop[::-1], shellModel.getEpsAxialTop(0))
        epsCircBot = np.append(epsCircBot[::-1], shellModel.getEpsCircBottom(0))
        epsCircTop = np.append(epsCircTop[::-1], shellModel.getEpsCircTop(0))
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


