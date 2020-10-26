"""control a tank optimization"""

import os, sys
import numpy as np
import datetime

from tankoh2 import programDir, log, pychain
from tankoh2.service import indent, getRunDir, plotStressEpsPuck, plotPuckFF
from tankoh2.utilities import updateName, copyAsJson, getRadiusByShiftOnMandrel, getCoordsShiftFromLength
from tankoh2.contour import getLiner, getDome
from tankoh2.material import getMaterial, getComposite, readLayupData, saveComposite
from tankoh2.winding import windLayer, getNegAngleAndPolarOpeningDiffByAngle, \
    getAngleAndPolarOpeningDiffByAngle
from tankoh2.optimize import optimizeAngle, minimizeUtilization
from tankoh2.solver import getLinearResults, getCriticalElementIdx, getCriticalElementIdxAndPuckFF, \
    getMaxFibreFailure, getPuckLinearResults
from tankoh2.exception import Tankoh2Error


def printLayer(layerNumber):
    log.info('\n' + '=' * 80 + f'\nLayer {layerNumber}\n' + '=' * 80)


def designLayers(vessel, maxLayers, minPolarOpening, puckProperties, burstPressure, runDir, compositeArgs):
    """
    Strategy:
    #. Start with hoop layer
    #. Second layer:
        #. Maximize layer angle that still attaches to the fitting
        #. add layer with this angle
    #. Iteratively perform the following
    #. Get puck fibre failures
    #. TODO: Check if reserve factors are satisfied - if yes end iteration
    #. Reduce relevant locations to
        #. 1 element at cylindrical section and
        #. every element between polar opening radii of 0 and of 70° angle layers
    #. identify critical element
    #. if critical element is in cylindrical section
        #. add hoop layer
        #. next iteration step
    #. if most loaded element is in dome area:
        #. Define Optimization bounds [minAngle, 70°] and puck result bounds
        #. Minimize puck fibre failue:
            #. Set angle
            #. Use analytical linear solver
            #. return max puck fibre failure
        #. Apply optimal angle to actual layer
        #. next iteration step
    """

    vessel.resetWindingSimulation()

    angles = []
    show = False
    save = True
    layerNumber = 0
    iterations = 0
    radiusDropThreshold = windLayer(vessel, layerNumber, 70)
    mandrel = vessel.getVesselLayer(layerNumber).getOuterMandrel1()
    dropRadiusIndex = np.argmin(np.abs(mandrel.getRArray() - radiusDropThreshold))

    minAngle, _, _ = optimizeAngle(vessel, minPolarOpening, layerNumber, 1., False,
                                   targetFunction=getAngleAndPolarOpeningDiffByAngle)

    # start with hoop layer
    printLayer(layerNumber)
    windLayer(vessel, layerNumber, 90)
    angles.append(90.)

    # introduce layer up to the fitting. Optimize required angle
    layerNumber += 1
    printLayer(layerNumber)
    angle, _, _ = optimizeAngle(vessel, minPolarOpening, layerNumber, minAngle, False,
                                targetFunction=getNegAngleAndPolarOpeningDiffByAngle)
    angles.append(angle)

    # create other layers
    for layerNumber in range(layerNumber + 1, maxLayers):
        printLayer(layerNumber)
        elemIdxmax, puckFF = getCriticalElementIdxAndPuckFF(vessel, puckProperties, dropRadiusIndex,
                                                            burstPressure)

        puckFFConvergence, _ = getPuckLinearResults(vessel, puckProperties, burstPressure)
        if puckFFConvergence.max().max() < 1:
            # stop criterion reached
            # cut composite by the layers not winded
            plotPuckFF(False, os.path.join(runDir, f'puck_{layerNumber}.png'), puckFFConvergence)
            composite = getComposite(angles, *compositeArgs)
            vessel.setComposite(composite)
            layerNumber -= 1
            break
        if elemIdxmax == 0:
            # insert hoop layer
            windLayer(vessel, layerNumber, angle=90)
            angles.append(90)
            indicies, poIndex = [], 0
        else:
            #insert helical layer
            # get location of critical element
            minAngle, _, _ = optimizeAngle(vessel, minPolarOpening, layerNumber, 1., False,
                                           targetFunction=getAngleAndPolarOpeningDiffByAngle)
            dropIndicies = range(0, dropRadiusIndex)
            angleBounds = [minAngle, 70]
            # critLength = mandrel.getLArray()[elemIdxmax:elemIdxmax+2].mean() # convert nodal coordinates to element middle coords
            # shift = 4*bandWidth
            # x,radii,lengths,indicies = getCoordsShiftFromLength(mandrel, critLength, [-shift, shift])

            angle, _, loopIt = minimizeUtilization(vessel, layerNumber, angleBounds, dropIndicies,
                                                   puckProperties, burstPressure, verbose=True)
            angles.append(angle)
            mandrel = vessel.getVesselLayer(layerNumber).getOuterMandrel1()
            poIndex = np.argmin(np.abs(mandrel.getRArray() - vessel.getPolarOpeningR(layerNumber, True)))
            iterations += loopIt

        plotPuckFF(False, os.path.join(runDir, f'puck_{layerNumber}.png'), puckFFConvergence, None,
                   vlines=[elemIdxmax, dropRadiusIndex, poIndex], vlineColors=['red', 'black', 'green'])

    if layerNumber == maxLayers:
        raise Tankoh2Error('Reached max layers. You need to specify more initial layers')

    vessel.finishWinding()
    results = getLinearResults(vessel, puckProperties, layerNumber, burstPressure)
    if show or save:
        plotStressEpsPuck(show, os.path.join(runDir, f'sig_eps_puck_{layerNumber}.png') if save else '',
                          *results)

    # get volume and surface area
    stats = vessel.calculateVesselStatistics()
    frpMass = stats.overallFRPMass  # in [kg]
    liner = vessel.getLiner()
    volume = liner.getVolume()  # [l]
    dome = liner.getDome1()
    r, x = dome.getRCoords(), dome.getXCoords()
    areaDome = np.pi * (r[:-1] + r[1:]) * np.sqrt((r[:-1] - r[1:]) ** 2 + (x[:-1] - x[1:]) ** 2)
    area = 2 * np.pi * liner.cylinderRadius * liner.cylinderLength + 2 * np.sum(areaDome)  # [mm**2]
    area *= 1e-6  # [m**2]
    return frpMass, volume, area, composite, iterations


def main(**kwargs):
    startTime = datetime.datetime.now()
    # #########################################################################################
    # SET Parameters of vessel
    # #########################################################################################

    # design constants AND not recognized issues
    minPolarOpening = 20  # mm
    # band pattern not recognized

    layersToWind = 100
    tankname = 'exact_h2'
    dataDir = os.path.join(programDir, 'data')
    hoopLayerThickness = 0.125
    helixLayerThickenss = 0.129
    rovingWidth = 3.175
    numberOfRovings = 4
    bandWidth = rovingWidth * numberOfRovings
    tex = 446  # g / km
    rho = 1.78  # g / cm^3
    sectionAreaFibre = tex / (1000. * rho)
    pressure = 10.  # pressure in MPa (bar / 10.)
    safetyFactor = 2.25

    # potential external inputs
    burstPressure = kwargs['burstPressure'] if 'burstPressure' in kwargs else pressure * safetyFactor
    dzyl = kwargs['dzyl'] if 'dzyl' in kwargs else 400.  # mm
    lzylinder = kwargs['lzyl'] if 'lzyl' in kwargs else 500.  # mm

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

    angles, thicknesses, = [90.] * layersToWind, [helixLayerThickenss] * layersToWind
    compositeArgs = [thicknesses, hoopLayerThickness, helixLayerThickenss, material,
                             sectionAreaFibre, rovingWidth, numberOfRovings, tex, designFilename, tankname]
    composite = getComposite(angles, *compositeArgs)
    composite.info()
    # create vessel and set liner and composite
    vessel = pychain.winding.Vessel()
    vessel.setLiner(liner)
    vessel.setComposite(composite)

    # #############################################################################
    # run winding simulation
    # #############################################################################
    frpMass, volume, area, composite, iterations = designLayers(vessel, layersToWind, minPolarOpening,
                                                     puckProperties, burstPressure, runDir, compositeArgs)

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

    # #############################################################################
    # run Evaluation
    # #############################################################################
    if 0:
        results = getLinearResults(vessel, puckProperties, layersToWind - 1, burstPressure)
        plotStressEpsPuck(True, None, *results)

    # vessel.printSimulationStatus()
    saveComposite(composite, designFilename.replace('.design', '_optimized.design'), tankname)
    composite.info()

    duration = datetime.datetime.now() - startTime
    log.info(f'iterations {iterations}, runtime {duration.seconds} seconds')

    log.info('FINISHED')

    return frpMass, volume, area


if __name__ == '__main__':
    main()
