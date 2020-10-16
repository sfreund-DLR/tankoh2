"""solver related methods"""

import numpy as np
import pandas

from tankoh2 import pychain

def getLinearResults(vessel, puckProperties, layersWinded):
    # build shell model for internal calculation
    converter = pychain.mycrofem.VesselConverter()
    shellModel = converter.buildAxShellModell(vessel, 10)  # pressure in MPa (bar / 10.)

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
    for layer in range(layersWinded):
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


