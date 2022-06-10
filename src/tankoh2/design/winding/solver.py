"""solver related methods"""

import numpy as np
import pandas

from tankoh2 import pychain, log
from tankoh2.design.winding.winding import windLayer


def getCriticalElementIdx(puck):
    """Returns the index of the most critical element

    :param puck: 2d array defining puckFF or puckIFF for each element and layer
    """
    # identify critical element
    layermax = puck.max().argmax()
    return puck.idxmax()[layermax], layermax


def getMaxPuckByAngle(angle, args):
    """Returns the maximum puck fibre failure index after setting and winding the given angle"""
    vessel, layerNumber, puckProperties, burstPressure, _, useFibreFailure, verbose, _ = args
    if hasattr(angle, '__iter__'):
        angle = angle[0]
    if angle is not None:
        log.debug(f'Layer {layerNumber}, wind angle {angle}')
        actualPolarOpening = windLayer(vessel, layerNumber, angle, verbose)
        if actualPolarOpening is np.inf:
            return np.inf
    maxPuck, maxIndex = _getMaxPuck(args)
    if verbose:
        failure = 'fibre failure' if useFibreFailure else 'inter fibre failure'
        log.info(f'Layer {layerNumber}, angle {angle}, max {failure} {maxPuck}, index {maxIndex}')
    return maxPuck


def getMaxPuckByShift(shift, args):
    """Returns the maximum puck fibre failure index after setting and winding the given hoop layer shift"""
    if hasattr(shift, '__iter__'):
        shift = shift[0]
    vessel, layerNumber, puckProperties, burstPressure, _, useFibreFailure, verbose, _ = args
    vessel.setHoopLayerShift(layerNumber, shift, True)
    actualPolarOpening = windLayer(vessel, layerNumber, verbose=verbose)
    if actualPolarOpening is np.inf:
        return np.inf
    maxPuck, maxIndex = _getMaxPuck(args)
    if verbose:
        failure = 'fibre failure' if useFibreFailure else 'inter fibre failure'
        log.info(f'Layer {layerNumber}, hoop shift {shift}, max {failure} {maxPuck}, index {maxIndex}')
    return maxPuck


def _getMaxPuck(args):
    """Return maximum fibre failure of the all layers after winding the given angle"""
    vessel, _, puckProperties, burstPressure, useIndices, useFibreFailure, _, symmetricContour = args
    index = 0 if useFibreFailure else 1
    maxPerElement = getLinearResults(
        vessel, puckProperties, burstPressure, useIndices, True, symmetricContour)[index].max(axis=1)
    maxIndex = maxPerElement.idxmax()
    maxPuck = maxPerElement.max()
    return maxPuck, maxIndex

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
        stressesMandrel2 = shellModel.calculateLayerStressesBottom()
        S11 = np.append(S11[::-1], stressesMandrel2[0], axis=0)
        S22 = np.append(S22[::-1], stressesMandrel2[0], axis=0)
        S12 = np.append(S12[::-1], stressesMandrel2[0], axis=0)
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
    columns = [f'layer {layerNumber}' for layerNumber in range(numberOfLayers)]
    puckFF = pandas.DataFrame(np.array(puckFF), columns=columns)
    puckIFF = pandas.DataFrame(np.array(puckIFF), columns=columns)
    if puckOnly:
        if useIndices is not None:
            noUseIndices = set(puckFF.index).difference(useIndices)
            puckFF.drop(noUseIndices, inplace=True)
            puckIFF.drop(noUseIndices, inplace=True)
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
    shellModel = converter.buildAxShellModell(vessel, burstPressure, True)  # pressure in MPa (bar / 10.)
    shellModel2 = None if symmetricContour else converter.buildAxShellModell(vessel, burstPressure, False)

    # run linear solver
    linerSolver = pychain.mycrofem.LinearSolver(shellModel)
    linerSolver.run(True)
    if not symmetricContour:
        linerSolver = pychain.mycrofem.LinearSolver(shellModel2)
        linerSolver.run(True)
    return shellModel, shellModel2

