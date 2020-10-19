"""control a tank optimization"""

import os, sys
# print('path')
# print('\n'.join(os.environ['PATH'].split(';')))
# print('pythonpath')
# print('\n'.join(sys.path))

import numpy as np
import pandas

from tankoh2 import programDir, log, pychain
from tankoh2.service import indent, getRunDir, plotStressEpsPuck
from tankoh2.utilities import updateName, copyAsJson
from tankoh2.contour import getLiner, getDome
from tankoh2.material import getMaterial, getComposite, readLayupData
from tankoh2.winding import windLayer, getAngleAndPolarOpeningDiffByAngle
from tankoh2.optimize import optimizeAngle
from tankoh2.solver import getLinearResults


def designLayers(vessel, maxLayers, minPolarOpening, puckProperties, bandWidth, runDir):
    """
    Strategy:
    #. Start with hoop layer
    #. Second layer:
        #. Maximize layer angle that still satisfies the fitting radius
        #. add layer with this angle
    #. Iteratively perform the following
    #. Get stresses and puck reserve factors
    #. Check if reserve factors are satisfied - if yes end iteration
    #. Reduce relevant locations to
        #. 1 element at cylindrical section and
        #. everything between radius 0 and raduis of 70° layer will be used
    #. identify most loaded element
    #. if most loaded element is in cylindrical section
        #. add hoop layer
        #. next iteration step
    #. if most loaded element is in dome area:
        #. get (critical) radius of most loaded element
        #. calculate polar opening radius for a layer, with it's band mid at the critical radius
        #. optimize layer angle to fit the target polar opening
        #. add layer
        #. next iteration step
    """

    vessel.resetWindingSimulation()

    show = False
    save = True
    radiusDropThreshold = windLayer(vessel, 0, 70)

    # start with hoop layer
    polarOpening = windLayer(vessel, 0, 90)

    # introduce layer up to the fitting. Optimize required angle
    layerNumber = 1
    angle, _, _ = optimizeAngle(vessel, minPolarOpening, layerNumber, True,
                                targetFunction=getAngleAndPolarOpeningDiffByAngle)

    # create other layers
    for layerNumber in range(layerNumber + 1, maxLayers):
        results = getLinearResults(vessel, puckProperties, layerNumber - 1)
        if show or save:
            plotStressEpsPuck(show,
                              os.path.join(runDir, f'sig_eps_puck_{layerNumber - 1}.png') if save else '',
                              *results)
        puckFF, puckIFF = results[7:9]

        # x-coordinate, radius, length on mandrel
        xrl = pandas.DataFrame(np.array([vessel.getVesselLayer(layerNumber - 1).getOuterMandrel1().getXArray(),
                              vessel.getVesselLayer(layerNumber - 1).getOuterMandrel1().getRArray(),
                              vessel.getVesselLayer(layerNumber - 1).getOuterMandrel1().getLArray()]).T,
                              columns=['x', 'radius', 'length'])

        # only observe one cylinder element and dome elements starting at radiusDropThreshold
        dropRadiusIndex = xrl['radius'].lt(radiusDropThreshold).idxmax()
        dropIndicies = range(1, dropRadiusIndex)
        puckFF.drop(dropIndicies, inplace=True)
        puckIFF.drop(dropIndicies, inplace=True)
        # identify critical element
        layermax = puckFF.max().argmax()
        idxmax = puckFF.idxmax()[layermax]

        if idxmax == 0:
            vessel.setLayerAngle(layerNumber, 90)
            vessel.runWindingSimulation(layerNumber + 1)
        else:
            # get location of critical element
            radiusCrit = float(xrl['radius'].loc[idxmax])
            lengthCrit = float(xrl['length'].loc[idxmax])
            lengthPolarOpening = lengthCrit + bandWidth
            radiusPolarOpening = np.interp(lengthPolarOpening, xrl['length'], xrl['radius'])
            if radiusPolarOpening < minPolarOpening:
                radiusPolarOpening = minPolarOpening
            angle, _, _ = optimizeAngle(vessel, radiusPolarOpening, layerNumber, True)

    vessel.finishWinding()

    results = getLinearResults(vessel, puckProperties, layerNumber)
    if show or save:
        plotStressEpsPuck(show, os.path.join(runDir, f'sig_eps_puck_{layerNumber}.png') if save else '',
                          *results)


def main():
    # #########################################################################################
    # SET Parameters of vessel
    # #########################################################################################
    layersToWind = 7
    tankname = 'NGT-BIT-2020-09-16'
    dataDir = os.path.join(programDir, 'data')
    dzyl = 400.  # mm
    lzylinder = 500.  # mm
    hoopLayerThickness = 0.125
    helixLayerThickenss = 0.129
    rovingWidth = 3.175
    numberOfRovings = 4
    bandWidth = rovingWidth * numberOfRovings
    tex = 446  # g / km
    rho = 1.78  # g / cm^3
    sectionAreaFibre = tex / (1000. * rho)
    safetyFactor = 2.5

    # design constants AND not recognized issues
    minPolarOpening = 20  # mm
    # band pattern not recognized

    # input files
    layupDataFilename = os.path.join(dataDir, "Winding_" + tankname + ".txt")
    materialFilename = os.path.join(dataDir, "CFRP_HyMod.json")
    # output files
    runDir = getRunDir()
    linerFilename = os.path.join(runDir, tankname + ".liner")
    designFilename = os.path.join(runDir, tankname + ".design")
    windingFile = os.path.join(runDir, tankname + "_realised_winding.txt")
    vesselFilename = os.path.join(runDir, tankname + ".vessel")
    windingResultFilename = os.path.join(runDir, tankname + ".wresults")

    # #########################################################################################
    # Create Liner
    # #########################################################################################
    dome = getDome(dzyl / 2., minPolarOpening, pychain.winding.DOME_TYPES.ISOTENSOID)
    liner = getLiner(dome, lzylinder, linerFilename, tankname)

    # ###########################################
    # Create material
    # ###########################################
    material = getMaterial(materialFilename)
    puckProperties = material.puckProperties

    angles, thicknesses, wendekreisradien, krempenradien = readLayupData(layupDataFilename)[:, :layersToWind]
    try:
        angles[2] = 40.
        angles[5] = 90.
        angles[6] = 90.
    except:
        pass
    composite = getComposite(material, angles, thicknesses, hoopLayerThickness, helixLayerThickenss,
                             sectionAreaFibre, rovingWidth, numberOfRovings, tex,
                             designFilename, tankname)
    composite.info()
    # create vessel and set liner and composite
    vessel = pychain.winding.Vessel()
    vessel.setLiner(liner)
    vessel.setComposite(composite)

    # #############################################################################
    # run winding simulation
    # #############################################################################
    designLayers(vessel, layersToWind, minPolarOpening, puckProperties, bandWidth, runDir)

    with open(windingFile, "w") as file:
        file.write('\t'.join(["Layer number", "Angle", "Polar opening"]) + '\n')
    outArr = []
    # save vessel
    vessel.saveToFile(vesselFilename)  # save vessel
    updateName(vesselFilename, tankname, ['vessel'])
    copyAsJson(vesselFilename, 'vessel')

    # save winding results
    windingResults = pychain.winding.VesselWindingResults()
    windingResults.buildFromVessel(vessel)
    windingResults.saveToFile(windingResultFilename)
    copyAsJson(windingResultFilename, 'wresults')

    from tankoh2.utilities import getElementThicknesses
    t = getElementThicknesses(vessel)

    # #############################################################################
    # run Evaluation
    # #############################################################################
    results = getLinearResults(vessel, puckProperties, layersToWind - 1)
    # plotStressEpsPuck(True,None, *results)

    vessel.printSimulationStatus()

    log.info('FINISHED')


if __name__ == '__main__':
    main()
