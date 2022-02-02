import os

import numpy as np

from tankoh2 import log
from tankoh2.design.winding.material import getComposite
from tankoh2.design.winding.optimize import optimizeAngle, minimizeUtilization
from tankoh2.design.winding.solver import getMaxFibreFailureByShift, getPuck, getCriticalElementIdx, \
    getLinearResults
from tankoh2.design.winding.winding import windHoopLayer, windLayer, getAngleAndPolarOpeningDiffByAngle, \
    getNegAngleAndPolarOpeningDiffByAngle
from tankoh2.design.winding.windingutils import getLayerThicknesses
from tankoh2.geometry.dome import AbstractDome
from tankoh2.service.plot.generic import plotDataFrame
from tankoh2.service.plot.muwind import plotContour, plotStressEpsPuck, plotThicknesses
from tankoh2.service.utilities import getTimeString


def printLayer(layerNumber, verbose = False, postfix = ''):
    sep = '\n' + '=' * 80
    log.info((sep if verbose else '') + f'\nLayer {layerNumber} {postfix}' + (sep if verbose else ''))


def resetVesselAnglesShifts(anglesShifts, vessel):
    for layerNumber, (angle, shift) in enumerate(anglesShifts):
        if abs(angle-90) < 1e-2:
            windHoopLayer(vessel,layerNumber, shift)
        else:
            windLayer(vessel, layerNumber, angle)


def checkThickness(vessel, angle, bounds):
    """when angle is close to fitting radius, sometimes the thickness of a layer is corrupt

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
                    polarOpeningRadius, dropIndicies, verbose):
    if verbose:
        log.info('Add helical layer')
    # get location of critical element
    minAngle, _, _ = optimizeAngle(vessel, polarOpeningRadius, layerNumber, 1., False,
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

def _getHoopAndHelicalIndicies(mandrel, liner, dome, elementCount, relRadiusHoopLayerEnd):
    rMax = mandrel.getRArray()[0]
    dropHoopIndexStart = np.argmax((-mandrel.getRArray()+rMax)>rMax*1e-4) - 10
    dropHoopIndexEnd = np.argmin(np.abs(mandrel.getRArray() - dome.cylinderRadius*relRadiusHoopLayerEnd))
    hoopOrHelicalIndex = np.argmin(np.abs(mandrel.getRArray() - dome.cylinderRadius*0.995))
    maxHoopShift = mandrel.getLArray()[dropHoopIndexEnd] - liner.cylinderLength/2
    dropHoopIndicies = list(range(0, dropHoopIndexStart)) + list(range(dropHoopIndexEnd, elementCount))
    dropHelicalIndicies = range(0, hoopOrHelicalIndex)
    return hoopOrHelicalIndex, maxHoopShift, dropHoopIndicies, dropHelicalIndicies

def designLayers(vessel, maxLayers, polarOpeningRadius, puckProperties, burstPressure, runDir,
                 composite, compositeArgs, verbose, useFibreFailure, relRadiusHoopLayerEnd):
    """
        :param vessel: vessel instance of mywind
        :param maxLayers: maximum numbers of layers
        :param polarOpeningRadius: min polar opening where fitting is attached [mm]
        :param puckProperties: puckProperties instance of mywind
        :param burstPressure: burst pressure [MPa]
        :param runDir: directory where to store results
        :param composite: composite instance of mywind
        :param compositeArgs: properties defining the composite:
            thicknesses, hoopLayerThickness, helixLayerThickenss, material,
            sectionAreaFibre, rovingWidth, numberOfRovings, tex, designFilename, tankname
        :param verbose: flag if verbose output is needed
        :param useFibreFailure: flag, use fibre failure or inter fibre failure
        :param relRadiusHoopLayerEnd: relative radius (to cyl radius) where hoop layers end
        :return: frpMass, volume, area, composite, iterations, anglesShifts

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
    minAngle, _, _ = optimizeAngle(vessel, polarOpeningRadius, layerNumber, 1., False,
                                   targetFunction=getAngleAndPolarOpeningDiffByAngle)
    plotContour(False,  os.path.join(runDir, f'contour.png'), mandrel.getXArray(), mandrel.getRArray())

    indiciesAndShifts = _getHoopAndHelicalIndicies(mandrel, liner, dome, elementCount, relRadiusHoopLayerEnd)
    hoopOrHelicalIndex, maxHoopShift, dropHoopIndicies, dropHelicalIndicies = indiciesAndShifts

    # introduce layer up to the fitting. Optimize required angle
    printLayer(layerNumber, verbose, '- initial helical layer')
    angle, _, _ = optimizeAngle(vessel, polarOpeningRadius, layerNumber, minAngle, False,
                                targetFunction=getNegAngleAndPolarOpeningDiffByAngle)
    anglesShifts.append((angle,0))
    layerNumber += 1

    # add hoop layer
    printLayer(layerNumber, verbose, '- initial hoop layer')
    resHoop = optimizeHoop(vessel, layerNumber, puckProperties, burstPressure,
                           dropHoopIndicies, maxHoopShift, verbose)
    shift, funcVal, loopIt, newDesignIndex = resHoop
    windHoopLayer(vessel, layerNumber, shift)
    anglesShifts.append((90, shift))

    indiciesAndShifts = _getHoopAndHelicalIndicies(mandrel, liner, dome, elementCount, relRadiusHoopLayerEnd)
    hoopOrHelicalIndex, maxHoopShift, dropHoopIndicies, dropHelicalIndicies = indiciesAndShifts

    # create other layers
    for layerNumber in range(layerNumber + 1, maxLayers):
        printLayer(layerNumber, verbose)
        puckFF, puckIFF = getPuck(vessel, puckProperties, None, burstPressure)
        puck = puckFF if useFibreFailure else puckIFF
        elemIdxmax, layermax = getCriticalElementIdx(puck)

        if puck.max().max() < 1:
            if verbose:
                log.info('End Iteration')
            # stop criterion reached
            columns = ['lay{}_{:04.1f}'.format(i, angle) for i, (angle, _) in enumerate(anglesShifts)]
            puck.columns = columns
            plotDataFrame(False, os.path.join(runDir, f'puck_{layerNumber}.png'), puck,
                          yLabel='puck fibre failure' if useFibreFailure else 'puck inter fibre failure')
            layerNumber -= 1
            break

        # add one layer
        composite = getComposite([a for a,_ in anglesShifts]+[90], [compositeArgs[2]]*(layerNumber+1), *compositeArgs[1:])
        vessel.setComposite(composite)
        resetVesselAnglesShifts(anglesShifts, vessel)

        #  check zone of highest puck values
        if (anglesShifts[layermax][0] > 89):
            resHoop = optimizeHoop(vessel, layerNumber, puckProperties, burstPressure,
                                   dropHoopIndicies, maxHoopShift, verbose)
            resHelical = optimizeHelical(vessel, layerNumber, puckProperties, burstPressure,
                                         polarOpeningRadius, dropHoopIndicies, verbose)
            if resHoop[1] < resHelical[1] * 1.25: #  puck result with helical layer must be 1.25 times better
                # add hoop layer
                shift, funcVal, loopIt, newDesignIndex = resHoop
                windHoopLayer(vessel, layerNumber, shift)
                anglesShifts.append((90, shift))
            else:
                angle, funcVal, loopIt, newDesignIndex = resHelical
                windLayer(vessel, layerNumber, angle)
                anglesShifts.append((angle, 0))
        else:
            angle, funcVal, loopIt, newDesignIndex = optimizeHelical(vessel, layerNumber, puckProperties, burstPressure,
                                                                     polarOpeningRadius, dropHelicalIndicies, verbose)

            anglesShifts.append((angle,0))
        iterations += loopIt
        columns = ['lay{}_{:04.1f}'.format(i, angle) for i, (angle,_) in enumerate(anglesShifts[:-1])]
        puck.columns=columns
        plotDataFrame(False, os.path.join(runDir, f'puck_{layerNumber}.png'), puck, None,
                      vlines=[elemIdxmax, hoopOrHelicalIndex, newDesignIndex], vlineColors=['red', 'black', 'green'],
                      yLabel='puck fibre failure' if useFibreFailure else 'puck inter fibre failure')
    else:
        log.warning('Reached max layers. You need to specify more initial layers')


    vessel.finishWinding()
    results = getLinearResults(vessel, puckProperties, layerNumber, burstPressure)
    if show or save:
        plotStressEpsPuck(show, os.path.join(runDir, f'sig_eps_puck_{layerNumber}.png') if save else '',
                          *results)
        thicknesses = getLayerThicknesses(vessel)
        columns = ['lay{}_{:04.1f}'.format(i, angle) for i, (angle,_) in enumerate(anglesShifts)]
        thicknesses.columns=columns
        plotThicknesses(show, os.path.join(runDir, f'thicknesses_{getTimeString()}.png'), thicknesses)

    # get volume and surface area
    stats = vessel.calculateVesselStatistics()
    frpMass = stats.overallFRPMass  # in [kg]

    volume = liner.getVolume()  # [l]
    areaDome = AbstractDome.getArea([dome.getXCoords(), dome.getRCoords()])
    area = 2 * np.pi * liner.cylinderRadius * liner.cylinderLength + 2 * areaDome  # [mm**2]
    area *= 1e-6  # [m**2]
    return frpMass, volume, area, composite, iterations, *(np.array(anglesShifts).T)