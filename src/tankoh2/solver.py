"""solver related methods"""

import numpy as np
import pandas

from tankoh2 import pychain, log
from tankoh2.winding import windLayer


def getCriticalElementIdx(vessel, layerNumber, puckProperties, radiusDropThreshold, burstPressure):
    """Returns the index of the most critical element

    """
    return getCriticalElementIdxAndPuckFF(vessel, layerNumber, puckProperties, radiusDropThreshold, burstPressure)[0]

def getCriticalElementIdxAndPuckFF(vessel, layerNumber, puckProperties, radiusDropThreshold, burstPressure):
    """Returns the index of the most critical element

    """
    mandrel = vessel.getVesselLayer(layerNumber - 1).getOuterMandrel1()
    dropRadiusIndex = np.argmin(np.abs(mandrel.getRArray() - radiusDropThreshold))
    dropIndicies = range(1, dropRadiusIndex)
    puckFF, puckIFF = getPuckLinearResults(vessel, puckProperties, burstPressure, dropIndicies)

    # identify critical element
    layermax = puckFF.max().argmax()
    idxmax = puckFF.idxmax()[layermax]
    return idxmax, puckFF

def getLinearResults(vessel, puckProperties, layerNumber, burstPressure, dropIndicies=None):
    """

    :param vessel:
    :param puckProperties:
    :param layerNumber: 0-based
    :return:
    """
    # build shell model for internal calculation
    converter = pychain.mycrofem.VesselConverter()
    shellModel = converter.buildAxShellModell(vessel, burstPressure)  # pressure in MPa (bar / 10.)

    # run linear solver
    linerSolver = pychain.mycrofem.LinearSolver(shellModel)
    linerSolver.run(True)

    # get stresses in the fiber COS
    S11, S22, S12 = shellModel.calculateLayerStressesBottom()
    # get  x coordinates (element middle)
    xCoords = shellModel.getElementCoordsX()
    # rCoords = shellModel.getElementCoordsR()
    # xCoords = shellModel.getNodeCoordsX()
    rCoords = shellModel.getNodeCoordsR()
    rCoords = (rCoords[:-1] + rCoords[1:]) / 2
    epsAxialBot = shellModel.getEpsAxialBottom(0)
    epsAxialTop = shellModel.getEpsAxialTop(0)
    epsCircBot = shellModel.getEpsCircBottom(0)
    epsCircTop = shellModel.getEpsCircTop(0)

    puck = pychain.failure.PuckFailureCriteria2D()
    puck.setPuckProperties(puckProperties)
    stresses = np.zeros((6,S11.shape[0],S11.shape[1]))
    stresses[0, :, :] = S11
    stresses[1, :, :] = S22
    stresses[5, :, :] = S12
    stressVec = pychain.utility.StressVector()
    puckFF, puckIFF = np.zeros(S11.shape), np.zeros(S11.shape)
    for layer in range(layerNumber+1):
        failures = []
        for elemNr in range(len(xCoords)):
            stressVec.fromVector(stresses[:, elemNr, layer])
            puckResult = puck.getExposure(stressVec)
            failures.append([puckResult.f_FF, puckResult.f_E0_IFF])
        failures = np.array(failures)
        puckFF[:,layer] = failures[:,0]
        puckIFF[:,layer] = failures[:,1]
    puckFF = pandas.DataFrame(puckFF, columns=[f'layer {layer}' for layer in range(puckFF.shape[1])])
    puckIFF = pandas.DataFrame(puckIFF, columns=[f'layer {layer}' for layer in range(puckIFF.shape[1])])
    return S11, S22, S12, epsAxialBot, epsAxialTop, epsCircBot, epsCircTop, puckFF, puckIFF

def getMaxFibreFailure(angle, args):
    """Return maximum fibre failure of the all layers after winding the given angle"""
    vessel, layerNumber, puckProperties, burstPressure, dropIndicies, verbose = args
    if hasattr(angle, '__iter__'):
        angle = angle[0]
    if angle is not None:
        actualPolarOpening = windLayer(vessel, layerNumber, angle, verbose)
        if actualPolarOpening is np.inf:
            return np.inf
    maxPerElement = getPuckLinearResults(vessel, puckProperties, burstPressure, dropIndicies)[0].max(axis=1)
    maxFF = maxPerElement.max()
    if verbose:
        maxIndex = maxPerElement.idxmax()
        log.info(f'angle {angle}, max fibre failure {maxFF}, index {maxIndex}')
    return maxFF

def getPuckLinearResults(vessel, puckProperties, burstPressure, dropIndicies=None):
    """Calculates puck results and returns them as dataframe

    :param vessel:
    :param puckProperties:
    :param layerNumber: 0-based
    :return: 2-tuple with dataframes (fibre failure, inter fibre failure)
    """
    # build shell model for internal calculation
    converter = pychain.mycrofem.VesselConverter()
    shellModel = converter.buildAxShellModell(vessel, burstPressure)  # pressure in MPa (bar / 10.)

    # run linear solver
    linerSolver = pychain.mycrofem.LinearSolver(shellModel)

    puck = pychain.failure.PuckFailureCriteria2D()
    puck.setPuckProperties(puckProperties)
    linerSolver.run(True)

    # get stresses in the fiber COS (elemNr, layerNr)
    S11, S22, S12 = shellModel.calculateLayerStressesBottom()
    numberOfElements, numberOfLayers = S11.shape
    stresses = np.zeros((numberOfElements,numberOfLayers, 6))
    stresses[:, :, 0] = S11
    stresses[:, :, 1] = S22
    stresses[:, :, 5] = S12
    stressVec = pychain.utility.StressVector()
    puckFF, puckIFF = [], []
    for elemIdx, elemStresses in enumerate(stresses):
        if dropIndicies is not None and elemIdx in dropIndicies:
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
    puckFF = pandas.DataFrame(np.array(puckFF), columns=[f'lay{layer}' for layer in range(numberOfLayers)])
    puckIFF = pandas.DataFrame(np.array(puckIFF), columns=[f'lay{layer}' for layer in range(numberOfLayers)])
    puckFF.drop(dropIndicies, inplace=True)
    puckIFF.drop(dropIndicies, inplace=True)
    return puckFF, puckIFF


