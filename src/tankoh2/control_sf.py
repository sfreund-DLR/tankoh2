"""control a tank optimization"""

import os, sys
import numpy as np
import datetime

from tankoh2 import programDir, log, pychain
from tankoh2.service import indent, getRunDir, plotStressEpsPuck, plotDataFrame, getTimeString
from tankoh2.utilities import updateName, copyAsJson, getLayerThicknesses
from tankoh2.contour import getLiner, getDome
from tankoh2.material import getMaterial, getComposite, readLayupData, saveComposite
from tankoh2.winding import windLayer, windHoopLayer, getNegAngleAndPolarOpeningDiffByAngle, \
    getAngleAndPolarOpeningDiffByAngle
from tankoh2.optimize import optimizeAngle, minimizeUtilization
from tankoh2.solver import getLinearResults, getCriticalElementIdx, getCriticalElementIdxAndPuckFF, \
    getPuckLinearResults, getMaxFibreFailureByShift
from tankoh2.exception import Tankoh2Error


def printLayer(layerNumber, verbose = False):
    sep = '\n' + '=' * 80
    log.info((sep if verbose else '') + f'\nLayer {layerNumber}' + (sep if verbose else ''))

def resetVesselAnglesShifts(anglesShifts, vessel):
    for layerNumber, (angle, shift) in enumerate(anglesShifts):
        if abs(angle-90) < 1e-2:
            windHoopLayer(vessel,layerNumber, shift)
        else:
            windLayer(vessel, layerNumber, angle)

def checkThickness(vessel, angle, bounds):
    """when angle is close to fitting radius, sometimes the tickness of a layer is corrupt

    will be resolved by increasing the angle a litte
    """
    thicknesses = getLayerThicknesses(vessel)
    lastLayThick = thicknesses.loc[:, thicknesses.columns[-1]]
    if lastLayThick[::-1].idxmax() - lastLayThick.idxmax() > lastLayThick.shape[0] * 0.1:
        #adjust bounds
        bounds = [angle+0.1, bounds[1]]
        return False, bounds
    return True, bounds

def optimizeHelical(vessel, layerNumber, puckProperties, burstPressure,
                    minPolarOpening, dropIndicies, verbose):
    if verbose:
        log.info('Add helical layer')
    # get location of critical element
    minAngle, _, _ = optimizeAngle(vessel, minPolarOpening, layerNumber, 1., False,
                                   targetFunction=getAngleAndPolarOpeningDiffByAngle)
    bounds = [minAngle, 70]

    layerOk = False
    while not layerOk:
        angle, funcVal, loopIt = minimizeUtilization(vessel, layerNumber, bounds, dropIndicies,
                                                     puckProperties, burstPressure, verbose=verbose)
        layerOk, bounds = checkThickness(vessel, angle, bounds)

    mandrel = vessel.getVesselLayer(layerNumber).getOuterMandrel1()
    newDesignIndex = np.argmin(np.abs(mandrel.getRArray() - vessel.getPolarOpeningR(layerNumber, True)))
    return angle, funcVal, loopIt, newDesignIndex

def optimizeHoop(vessel, layerNumber, puckProperties, burstPressure,
                 dropIndicies, maxHoopShift, verbose):
    if verbose:
        log.info('Add hoop layer')
    bounds = [0, maxHoopShift]
    shift, funcVal, loopIt = minimizeUtilization(vessel, layerNumber, bounds, dropIndicies,
                                                 puckProperties, burstPressure,
                                                 targetFunction=getMaxFibreFailureByShift, verbose=verbose)
    newDesignIndex = 0
    return shift, funcVal, loopIt, newDesignIndex

def designLayers(vessel, maxLayers, minPolarOpening, puckProperties, burstPressure, runDir,
                 composite, compositeArgs, verbose):
    """
    Strategy:
    #. Start with hoop layer
    #. Second layer:
        #. Maximize layer angle that still attaches to the fitting
        #. add layer with this angle
    #. Iteratively perform the following
    #. Get puck fibre failures
    #. Check if puck reserve factors are satisfied - if yes end iteration
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

    anglesShifts = []  # list of 2-tuple with angle and shift for each layer
    show = False
    save = True
    layerNumber = 0
    iterations = 0
    liner = vessel.getLiner()
    dome = liner.getDome1()
    radiusDropThreshold = windLayer(vessel, layerNumber, 70)
    mandrel = vessel.getVesselLayer(layerNumber).getOuterMandrel1()
    dropRadiusIndex = np.argmin(np.abs(mandrel.getRArray() - radiusDropThreshold))
    elementCount = mandrel.getRArray().shape[0]-1

    minAngle, _, _ = optimizeAngle(vessel, minPolarOpening, layerNumber, 1., False,
                                   targetFunction=getAngleAndPolarOpeningDiffByAngle)

    rMax = mandrel.getRArray()[0]
    dropHoopIndexStart = np.argmax((-mandrel.getRArray()+rMax)>rMax*1e-4) - 10
    dropHoopIndexEnd = np.argmin(np.abs(mandrel.getRArray() - dome.cylinderRadius*0.98))
    hoopOrHelicalIndex = np.argmin(np.abs(mandrel.getRArray() - dome.cylinderRadius*0.99))

    maxHoopShift = mandrel.getLArray()[dropHoopIndexEnd] - liner.cylinderLength/2

    # start with hoop layer
    printLayer(layerNumber, verbose)
    windLayer(vessel, layerNumber, 90)
    anglesShifts.append((90.,0))

    # introduce layer up to the fitting. Optimize required angle
    layerNumber += 1
    printLayer(layerNumber, verbose)
    angle, _, _ = optimizeAngle(vessel, minPolarOpening, layerNumber, minAngle, False,
                                targetFunction=getNegAngleAndPolarOpeningDiffByAngle)
    anglesShifts.append((angle,0))

    # create other layers
    for layerNumber in range(layerNumber + 1, maxLayers):
        printLayer(layerNumber, verbose)
        elemIdxmax, puckFF = getCriticalElementIdxAndPuckFF(vessel, puckProperties, None, burstPressure)

        puckFFConvergence, _ = getPuckLinearResults(vessel, puckProperties, burstPressure)
        if puckFFConvergence.max().max() < 1:
            if verbose:
                log.info('End Iteration')
            # stop criterion reached
            plotDataFrame(False, os.path.join(runDir, f'puck_{layerNumber}.png'), puckFFConvergence)
            layerNumber -= 1
            break
        elif layerNumber > maxLayers:
            raise Tankoh2Error('Reached max layers. You need to specify more initial layers')

        # add one layer
        composite = getComposite([a for a,_ in anglesShifts]+[90], [compositeArgs[2]]*(layerNumber+1), *compositeArgs[1:])
        vessel.setComposite(composite)
        resetVesselAnglesShifts(anglesShifts, vessel)

        #  check zone of highest puck values
        if elemIdxmax < hoopOrHelicalIndex:
            dropIndicies = list(range(0,dropHoopIndexStart)) + list(range(dropHoopIndexEnd,elementCount))
            resHoop = optimizeHoop(vessel, layerNumber, puckProperties, burstPressure,
                                   dropIndicies, maxHoopShift, verbose)
            resHelical = optimizeHelical(vessel, layerNumber, puckProperties, burstPressure,
                                         minPolarOpening, dropIndicies, verbose)
            if resHoop[1] * 1.25 < resHelical[1]: #  puck result with helical layer must be 1.25 times better
                # add hoop layer
                shift, funcVal, loopIt, newDesignIndex = resHoop
                windHoopLayer(vessel, layerNumber, shift)
                anglesShifts.append((90, shift))
            else:
                angle, funcVal, loopIt, newDesignIndex = resHelical
                windLayer(vessel, layerNumber, angle)
                anglesShifts.append((angle, 0))
        else:
            dropIndicies = range(0, hoopOrHelicalIndex)
            angle, funcVal, loopIt, newDesignIndex = optimizeHelical(vessel, layerNumber, puckProperties, burstPressure,
                                                                     minPolarOpening, dropIndicies, verbose)

            anglesShifts.append((angle,0))
        iterations += loopIt

        plotDataFrame(False, os.path.join(runDir, f'puck_{layerNumber}.png'), puckFFConvergence, None,
                      vlines=[elemIdxmax, hoopOrHelicalIndex, newDesignIndex], vlineColors=['red', 'black', 'green'])


    vessel.finishWinding()
    results = getLinearResults(vessel, puckProperties, layerNumber, burstPressure)
    if show or save:
        plotStressEpsPuck(show, os.path.join(runDir, f'sig_eps_puck_{layerNumber}.png') if save else '',
                          *results)
        thicknesses = getLayerThicknesses(vessel)
        plotDataFrame(show, os.path.join(runDir, f'thicknesses_{getTimeString()}.png'), thicknesses)

    # get volume and surface area
    stats = vessel.calculateVesselStatistics()
    frpMass = stats.overallFRPMass  # in [kg]

    volume = liner.getVolume()  # [l]
    r, x = dome.getRCoords(), dome.getXCoords()
    areaDome = np.pi * (r[:-1] + r[1:]) * np.sqrt((r[:-1] - r[1:]) ** 2 + (x[:-1] - x[1:]) ** 2)
    area = 2 * np.pi * liner.cylinderRadius * liner.cylinderLength + 2 * np.sum(areaDome)  # [mm**2]
    area *= 1e-6  # [m**2]
    return frpMass, volume, area, composite, iterations, anglesShifts


def createWindingDesign(**kwargs):
    startTime = datetime.datetime.now()
    verbose = False
    # #########################################################################################
    # SET Parameters of vessel
    # #########################################################################################

    log.info('='*100)
    log.info('createWindingDesign with these parameters: '+str(kwargs))
    log.info('='*100)

    # design constants AND not recognized issues

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
    minPolarOpening = kwargs['minPolarOpening'] if 'minPolarOpening' in kwargs else 20  # mm

    # input files
    materialFilename = os.path.join(dataDir, "CFRP_HyMod.json")
    # output files
    runDir = kwargs['runDir'] if 'runDir' in kwargs else getRunDir()
    linerFilename = os.path.join(runDir, tankname + ".liner")
    designFilename = os.path.join(runDir, tankname + ".design")
    vesselFilename = os.path.join(runDir, tankname + ".vessel")
    windingResultFilename = os.path.join(runDir, tankname + ".wresults")

    # #########################################################################################
    # Create Liner
    # #########################################################################################
    dome = getDome(dzyl / 2., minPolarOpening, pychain.winding.DOME_TYPES.CIRCLE) # ISOTENSOID
    liner = getLiner(dome, lzylinder, linerFilename, tankname)

    # ###########################################
    # Create material
    # ###########################################
    material = getMaterial(materialFilename)
    puckProperties = material.puckProperties

    angles, thicknesses, = [90.] * 2, [helixLayerThickenss] * 2
    compositeArgs = [thicknesses, hoopLayerThickness, helixLayerThickenss, material,
                             sectionAreaFibre, rovingWidth, numberOfRovings, tex, designFilename, tankname]
    composite = getComposite(angles, *compositeArgs)
    #compositeArgs = [helixLayerThickenss, material, pychain.material.LAYER_TYPES.BAP]
    # create vessel and set liner and composite
    vessel = pychain.winding.Vessel()
    vessel.setLiner(liner)
    vessel.setComposite(composite)

    # #############################################################################
    # run winding simulation
    # #############################################################################
    frpMass, volume, area, composite, iterations, anglesShifts = designLayers(vessel, layersToWind, minPolarOpening,
                                                                puckProperties, burstPressure, runDir,
                                                                composite, compositeArgs, verbose)

    np.savetxt(os.path.join(runDir, 'angles_shifts.txt'), anglesShifts)
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

    if verbose:
        # vessel.printSimulationStatus()
        composite.info()

    duration = datetime.datetime.now() - startTime
    log.info(f'iterations {iterations}, runtime {duration.seconds} seconds')

    log.info('FINISHED')

    return frpMass, volume, area, liner.linerLength, composite.getNumberOfLayers()


if __name__ == '__main__':
    createWindingDesign()
