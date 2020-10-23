"""control a tank optimization"""

import os, sys
import numpy as np
import datetime

from tankoh2 import programDir, log, pychain
from tankoh2.service import indent, getRunDir, plotStressEpsPuck, plotPuckFF
from tankoh2.utilities import updateName, copyAsJson, getRadiusByShiftOnMandrel, getCoordsShiftFromLength
from tankoh2.contour import getLiner, getDome
from tankoh2.material import getMaterial, getComposite, readLayupData, saveComposite
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

    show = False
    save = True
    layerNumber = 0
    iterations = 0
    radiusDropThreshold = windLayer(vessel, layerNumber, 70)
    mandrel = vessel.getVesselLayer(layerNumber).getOuterMandrel1()
    dropRadiusIndex = np.argmin(np.abs(mandrel.getRArray() - radiusDropThreshold))

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
        elemIdxmax, puckFF = getCriticalElementIdxAndPuckFF(vessel, puckProperties, dropRadiusIndex, burstPressure)

        if elemIdxmax == 0:
            windLayer(vessel, layerNumber, angle=90)
            indicies, poIndex=[], 0
        else:
            # get location of critical element
            minAngle, _, _ = optimizeAngle(vessel, minPolarOpening, layerNumber, 1., False,
                                           targetFunction=getAngleAndPolarOpeningDiffByAngle)
            dropIndicies = range(0, dropRadiusIndex)
            angleBounds = [minAngle, 70]
            #critLength = mandrel.getLArray()[elemIdxmax:elemIdxmax+2].mean() # convert nodal coordinates to element middle coords
            #shift = 4*bandWidth
            #x,radii,lengths,indicies = getCoordsShiftFromLength(mandrel, critLength, [-shift, shift])

            angle,_,loopIt = minimizeUtilization(vessel, layerNumber, angleBounds, dropIndicies, puckProperties, burstPressure, verbose=True)
            mandrel = vessel.getVesselLayer(layerNumber).getOuterMandrel1()
            poIndex = np.argmin(np.abs(mandrel.getRArray()-vessel.getPolarOpeningR(layerNumber,True)))
            iterations += loopIt

        plotPuckFF(False,os.path.join(runDir,f'puck_{layerNumber}.png'),puckFF,None,
                   vlines=[elemIdxmax, dropRadiusIndex, poIndex], vlineColors=['red','black', 'green'])
        getMaxFibreFailure(None, [vessel, layerNumber, puckProperties, burstPressure, [], True])
    vessel.finishWinding()

    results = getLinearResults(vessel, puckProperties, layerNumber, burstPressure)
    if show or save:
        plotStressEpsPuck(show, os.path.join(runDir, f'sig_eps_puck_{layerNumber}.png') if save else '',
                          *results)
    return iterations

def main():
    # #########################################################################################
    # SET Parameters of vessel
    # #########################################################################################
    startTime= datetime.datetime.now()
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
    iterations = designLayers(vessel, layersToWind, minPolarOpening, puckProperties, bandWidth, burstPressure, runDir)

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


    # #############################################################################
    # run Evaluation
    # #############################################################################
    if 0:
        results = getLinearResults(vessel, puckProperties, layersToWind - 1, burstPressure)
        plotStressEpsPuck(True,None, *results)

    #vessel.printSimulationStatus()
    saveComposite(composite, designFilename.replace('.design','_optimized.design'), tankname)
    composite.info()

    duration = datetime.datetime.now() - startTime
    log.info(f'iterations {iterations}, runtime {duration.seconds} seconds')

    log.info('FINISHED')


if __name__ == '__main__':
    main()
