"""control a tank optimization"""

import os, sys
import numpy as np

from tankoh2 import programDir, log, pychain
from tankoh2.service import indent, getRunDir, plotStressEpsPuck, plotPuckFF
from tankoh2.utilities import updateName, copyAsJson, getRadiusByShiftOnMandrel, getCoordsShiftFromLength
from tankoh2.contour import getLiner, getDome
from tankoh2.material import getMaterial, getComposite, readLayupData
from tankoh2.winding import windLayer, getNegAngleAndPolarOpeningDiffByAngle, getAngleAndPolarOpeningDiffByAngle
from tankoh2.optimize import optimizeAngle, minimizeUtilization
from tankoh2.solver import getLinearResults, getCriticalElementIdx, getCriticalElementIdxAndPuckFF, getMaxFibreFailure

def printLayer(layerNumber):
    log.info('\n' + '=' * 80 + f'\nLayer {layerNumber}\n' + '=' * 80)

def designLayers(vessel, maxLayers, minPolarOpening, puckProperties, bandWidth, burstPressure, runDir):
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
    layerNumber = 0
    iterations = 0
    radiusDropThreshold = windLayer(vessel, layerNumber, 70)
    minAngle, _, _ = optimizeAngle(vessel, minPolarOpening, layerNumber, 1., False, targetFunction=getAngleAndPolarOpeningDiffByAngle)

    # start with hoop layer
    printLayer(layerNumber)
    windLayer(vessel, layerNumber, 90)

    # introduce layer up to the fitting. Optimize required angle
    layerNumber += 1
    printLayer(layerNumber)
    angle, _, _ = optimizeAngle(vessel, minPolarOpening, layerNumber, minAngle, False,
                                targetFunction=getNegAngleAndPolarOpeningDiffByAngle)

    # create other layers
    for layerNumber in range(layerNumber + 1, maxLayers):
        printLayer(layerNumber)
        mandrel = vessel.getVesselLayer(layerNumber - 1).getOuterMandrel1()
        elemIdxmax, puckFF = getCriticalElementIdxAndPuckFF(vessel, layerNumber, puckProperties, radiusDropThreshold, burstPressure)

        if elemIdxmax == 0:
            windLayer(vessel, layerNumber, angle=90)
            indicies=[]
        else:
            # get location of critical element
            minAngle, _, _ = optimizeAngle(vessel, minPolarOpening, layerNumber, 1., False,
                                           targetFunction=getAngleAndPolarOpeningDiffByAngle)
            critLength = mandrel.getLArray()[elemIdxmax:elemIdxmax+2].mean() # convert nodal coordinates to element middle coords
            shift = 4*bandWidth
            x,radii,lengths,indicies = getCoordsShiftFromLength(mandrel, critLength, [-shift, shift])

            mandrel = vessel.getVesselLayer(layerNumber - 1).getOuterMandrel1()
            dropRadiusIndex = np.argmin(np.abs(mandrel.getRArray() - radiusDropThreshold))
            dropIndicies = range(0, dropRadiusIndex)
            angleBounds = [minAngle, 70]

            #dropIndicies = list(range(0, indicies[0])) + list(range(indicies[1], len(mandrel.getLArray())-2))
            #angleBounds = [optimizeAngle(vessel, radius, layerNumber,minAngle)[0] for radius in radii[::-1]]

            angle,_,loopIt = minimizeUtilization(vessel, layerNumber, angleBounds, dropIndicies, puckProperties, burstPressure, verbose=True)
            iterations += loopIt
            #radiusCrit = mandrel.getRArray()[idxmax]
            #radiusPolarOpening = getRadiusByShiftOnMandrel(mandrel, radiusCrit, bandWidth)
            #if radiusPolarOpening < minPolarOpening:
            #    radiusPolarOpening = minPolarOpening
            #angle, _, _ = optimizeAngle(vessel, radiusPolarOpening, layerNumber,minAngle, True)
        plotPuckFF(False,os.path.join(runDir,f'puck_{layerNumber}.png'),puckFF,None, [elemIdxmax]+list(indicies))
        getMaxFibreFailure(None, [vessel, layerNumber, puckProperties, burstPressure, [], True])
    vessel.finishWinding()

    results = getLinearResults(vessel, puckProperties, layerNumber, burstPressure)
    if show or save:
        plotStressEpsPuck(show, os.path.join(runDir, f'sig_eps_puck_{layerNumber}.png') if save else '',
                          *results)
    print(f'iterations {iterations}')

def main():
    # #########################################################################################
    # SET Parameters of vessel
    # #########################################################################################
    layersToWind = 15
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
    pressure = 100.  # pressure in MPa (bar / 10.)
    safetyFactor = 2.5
    burstPressure = pressure * safetyFactor

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
    designLayers(vessel, layersToWind, minPolarOpening, puckProperties, bandWidth, burstPressure, runDir)

    with open(windingFile, "w") as file:
        file.write('\t'.join(["Layer number", "Angle", "Polar opening"]) + '\n')
    outArr = []
    # save vessel
    vessel.saveToFile(vesselFilename)  # save vessel
    updateName(vesselFilename, tankname, ['vessel'])
    updateName(vesselFilename, pressure, ['vessel'], attrName='operationPressure')
    updateName(vesselFilename, safetyFactor, ['vessel'], attrName='securityFactor')
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
    if 0:
        results = getLinearResults(vessel, puckProperties, layersToWind - 1, burstPressure)
        plotStressEpsPuck(True,None, *results)

    #vessel.printSimulationStatus()
    composite.info()

    log.info('FINISHED')


if __name__ == '__main__':
    main()
