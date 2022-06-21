import os

import numpy as np
from matplotlib import pylab as plt


from tankoh2 import log
from tankoh2.service.exception import Tankoh2Error
from tankoh2.design.winding.material import getComposite
from tankoh2.design.winding.optimize import optimizeAngle, minimizeUtilization
from tankoh2.design.winding.solver import getMaxPuckByAngle, getMaxPuckByShift, getCriticalElementIdx, \
    getLinearResults
from tankoh2.design.winding.winding import windHoopLayer, windLayer, getAngleAndPolarOpeningDiffByAngle, \
    getNegAngleAndPolarOpeningDiffByAngle
from tankoh2.design.winding.windingutils import getLayerThicknesses
from tankoh2.geometry.dome import AbstractDome, flipContour
from tankoh2.service.plot.generic import plotDataFrame, plotContour
from tankoh2.service.plot.muwind import plotStressEpsPuck, plotThicknesses, plotPuckAndTargetFunc


maxHelicalAngle = 70

def printLayer(layerNumber, verbose = False, postfix = ''):
    sep = '\n' + '=' * 80
    log.info((sep if verbose else '') + f'\nLayer {layerNumber} {postfix}' + (sep if verbose else ''))


def resetVesselAnglesShifts(anglesShifts, vessel):
    for layerNumber, (angle, shift) in enumerate(anglesShifts):
        if abs(angle-90) < 1e-2:
            windHoopLayer(vessel,layerNumber, shift)
        else:
            windLayer(vessel, layerNumber, angle)


def checkThickness(vessel, angle, bounds, symmetricContour):
    """when angle is close to fitting radius, sometimes the thickness of a layer is corrupt

    will be resolved by increasing the angle a little
    """
    thicknesses = getLayerThicknesses(vessel, symmetricContour)
    lastLayThick = thicknesses.loc[:, thicknesses.columns[-1]]
    if lastLayThick[::-1].idxmax() - lastLayThick.idxmax() > lastLayThick.shape[0] * 0.1:
        #adjust bounds
        bounds = [angle+0.1, bounds[1]]
        return False, bounds
    return True, bounds


def optimizeHelical(vessel, layerNumber, puckProperties, burstPressure,
                    polarOpeningRadius, useIndices, useFibreFailure, verbose, verbosePlot, symmetricContour):
    if verbose:
        log.info('Optimize helical layer')
    # get location of critical element

    windLayer(vessel, layerNumber, maxHelicalAngle)
    minAngle = vessel.estimateCylinderAngle(layerNumber, polarOpeningRadius)
    # minAngle, _, _ = optimizeAngle(vessel, polarOpeningRadius, layerNumber, (1., maxHelicalAngle), False,
    #                                targetFunction=getAngleAndPolarOpeningDiffByAngle)
    bounds = [minAngle, maxHelicalAngle]

    optArgs = [vessel, layerNumber, puckProperties, burstPressure, useIndices, useFibreFailure, verbose,
            symmetricContour]
    for tryIterations in range(20):
        angle, funcVal, loopIt, tfPlotVals = minimizeUtilization(bounds, getMaxPuckByAngle, optArgs, verbosePlot)
        layerOk, bounds = checkThickness(vessel, angle, bounds, symmetricContour)
        if layerOk:
            break
    else:
        raise Tankoh2Error('Could not correct the thickness of the actual layer. Possibly the number of '
                           'nodes in respect to the tank radius and band width is not sufficient')
    polarOpeningRadiusOfLayer = windLayer(vessel, layerNumber, angle)
    mandrel = vessel.getVesselLayer(layerNumber).getOuterMandrel1()
    newDesignIndex = np.argmin(np.abs(mandrel.getRArray() - polarOpeningRadiusOfLayer))
    log.debug(f'anlge {angle}, puck value {funcVal}, loopIterations {loopIt}, '
              f'polar opening contour coord {newDesignIndex}')
    return angle, funcVal, loopIt, newDesignIndex, tfPlotVals


def optimizeHoop(vessel, layerNumber, puckProperties, burstPressure,
                 useIndices, useFibreFailure, maxHoopShift, verbose, verbosePlot, symmetricContour):
    """

    :param vessel:
    :param layerNumber:
    :param puckProperties:
    :param burstPressure:
    :param useIndices: element indicies that should be used for strength evaluation
    :param useFibreFailure:
    :param maxHoopShift:
    :param verbose:
    :param verbosePlot:
    :param symmetricContour: Flag if the contour is symmetric
    :return:
    """
    if verbose:
        log.info('Optimize hoop layer')
    bounds = [-maxHoopShift/5, maxHoopShift]

    optArgs = [vessel, layerNumber, puckProperties, burstPressure, useIndices, useFibreFailure, verbose,
            symmetricContour]
    shift, funcVal, loopIt, tfPlotVals = minimizeUtilization(bounds, getMaxPuckByShift, optArgs, verbosePlot)

    mandrel = vessel.getVesselLayer(layerNumber).getOuterMandrel1()
    r, l = mandrel.getRArray(), mandrel.getLArray()
    cylLenIdx = len(r) - np.argmin(np.abs(r - r[0])[::-1]) # np.argmin from the back of the mandrels radii
    hoopLength = l[cylLenIdx] + shift
    newDesignIndex = np.argmin(np.abs(l - hoopLength))
    log.debug(f'hoop shift {shift}, puck value {funcVal}, loopIterations {loopIt}, '
              f'hoop end contour coord {newDesignIndex}')
    return shift, funcVal, loopIt, newDesignIndex, tfPlotVals


def _getHoopAndHelicalIndices(vessel, symmetricContour,
                               relRadiusHoopLayerEnd):
    """calculate borders and element regions for optimization

    :param vessel: µWind vessel instance
    :param symmetricContour: Flag if the contour is symmetric
    :param relRadiusHoopLayerEnd: relative radius (to cyl radius) where hoop layers end
    :return:
        - cylinderEndIndex: index which distinguishes between indicies of
            cylindrical and dome section (mandrel1)
        - maxHoopShift: maximal length of hoop shifts into dome section
        - useHoopIndices:
        - useHelicalIndices
    """
    liner = vessel.getLiner()
    mandrel1 = liner.getMandrel1()
    mandrel2 = liner.getMandrel2() if not symmetricContour else None

    useHoopIndices, useHelicalIndices = np.array([], dtype=np.int), np.array([], dtype=np.int)
    cylinderEndIndex, maxHoopShift = None, None
    for mandrel in [mandrel2, mandrel1]:
        if mandrel is None:
            continue
        r = mandrel.getRArray()
        rCyl = r[0]
        elementCount = len(r)-1
        hoopIndexEnd = np.argmin(np.abs(r - rCyl*relRadiusHoopLayerEnd))
        cylinderEndIndex = np.argmin(np.abs(r - rCyl*0.995)[::-1])
        maxHoopShift = mandrel.getLArray()[hoopIndexEnd] - liner.cylinderLength/2

        hoopIndexStart = int(np.argmax((-mandrel.getRArray()+rCyl)>rCyl*1e-4) * 0.7) # not all hoop elements must be evaluated
        hoopIndices = np.linspace(hoopIndexStart, hoopIndexEnd, hoopIndexEnd-hoopIndexStart+1, dtype=np.int)
        helicalIndices = np.linspace(hoopIndexEnd, elementCount, elementCount-hoopIndexEnd+1, dtype=np.int)
        if not symmetricContour and mandrel is mandrel1:
            # shift existing indices and include by mandrel 1 indices
            useHoopIndices += elementCount
            useHelicalIndices += elementCount
            # twist indices
            hoopIndices = elementCount - hoopIndices[::-1]
            helicalIndices = elementCount - helicalIndices[::-1]

        useHoopIndices = np.append(hoopIndices, useHoopIndices)
        useHelicalIndices = np.append(helicalIndices, useHelicalIndices)

    return cylinderEndIndex, hoopIndexEnd, maxHoopShift, useHoopIndices, useHelicalIndices


def designLayers(vessel, maxLayers, polarOpeningRadius, puckProperties, burstPressure, symmetricContour,
                 runDir, composite, compositeArgs, verbose, verbosePlot,
                 useFibreFailure, relRadiusHoopLayerEnd):
    """Perform design optimization layer by layer

    :param vessel: vessel instance of mywind
    :param maxLayers: maximum numbers of layers
    :param polarOpeningRadius: min polar opening where fitting is attached [mm]
    :param puckProperties: puckProperties instance of mywind
    :param burstPressure: burst pressure [MPa]
    :param symmetricContour: Flag if the contour is symmetric
    :param runDir: directory where to store results
    :param composite: composite instance of mywind
    :param compositeArgs: properties defining the composite:
        thicknesses, hoopLayerThickness, helixLayerThickenss, material,
        sectionAreaFibre, rovingWidth, numberOfRovings, tex, designFilename, tankname
    :param verbose: flag if verbose output is needed
    :param verbosePlot: flag if more plots should be created
    :param useFibreFailure: flag, use fibre failure or inter fibre failure
    :param relRadiusHoopLayerEnd: relative radius (to cyl radius) where hoop layers end
    :return: frpMass, volume, area, composite, iterations, anglesShifts

    Strategy:

    #. Start with helical layer:
        #. Maximize layer angle that still attaches to the fitting
        #. add layer with this angle
    #. Add hoop layer
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
    hoopOrHelicalFac = 1.
    liner = vessel.getLiner()

    indiciesAndShifts = _getHoopAndHelicalIndices(vessel, symmetricContour, relRadiusHoopLayerEnd)
    cylinderEndIndex, hoopIndexEnd, maxHoopShift, useHoopIndices, useHelicalIndices = indiciesAndShifts
    x,r = liner.getMandrel1().getXArray(), liner.getMandrel1().getRArray()
    if not symmetricContour:
        x,r = flipContour(x,r)
        x = np.append(x, liner.getMandrel2().getXArray()[1:] + np.max(x))
        r = np.append(r, liner.getMandrel2().getRArray()[1:])
    plotContour(False,  os.path.join(runDir, f'contour.png'), x, r, 'Contour',
                vlines=[hoopIndexEnd], vlineColors=['black'])

    log.debug('Find minimal possible angle')

    #minAngle, _, _ = optimizeAngle(vessel, polarOpeningRadius, layerNumber, (1., maxHelicalAngle), False,
    #                               targetFunction=getAngleAndPolarOpeningDiffByAngle)
    windLayer(vessel, layerNumber, maxHelicalAngle)
    minAngle = vessel.estimateCylinderAngle(layerNumber, polarOpeningRadius)


    # introduce layer up to the fitting. Optimize required angle
    printLayer(layerNumber, verbose, '- initial helical layer')
    windLayer(vessel, layerNumber, minAngle)
    #angle, _, _ = optimizeAngle(vessel, polarOpeningRadius, layerNumber, (minAngle, maxHelicalAngle), False,
    #                            targetFunction=getNegAngleAndPolarOpeningDiffByAngle)
    anglesShifts.append((minAngle,0))

    # create other layers
    vessel.saveToFile(os.path.join(runDir, 'backup.vessel'))  # save vessel
    for layerNumber in range(layerNumber + 1, maxLayers):
        printLayer(layerNumber, verbose)
        puckFF, puckIFF = getLinearResults(vessel, puckProperties, burstPressure,
                                           puckOnly=True, symmetricContour=symmetricContour)
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
        log.debug(f'Layer {layerNumber}, already wound angles, shifts: {anglesShifts}')
        vessel.setComposite(composite)
        resetVesselAnglesShifts(anglesShifts, vessel)

        # check zone of highest puck values
        if layerNumber == 1 and useFibreFailure:
            # this layer should be a hoop layer
            optHoopRegion = True
        elif useFibreFailure:
            # check if max puck value occurred in hoop or helical layer
            optHoopRegion = anglesShifts[layermax][0] > 89
        else:
            optHoopRegion = elemIdxmax < cylinderEndIndex
        if optHoopRegion:
            resHoop = optimizeHoop(vessel, layerNumber, puckProperties, burstPressure, useHoopIndices,
                                   useFibreFailure, maxHoopShift, verbose, verbosePlot, symmetricContour)
            resHelical = optimizeHelical(vessel, layerNumber, puckProperties, burstPressure,
                                         polarOpeningRadius, useHoopIndices, useFibreFailure,
                                         verbose, verbosePlot, symmetricContour)
            if layerNumber == 1 or (resHoop[1] < resHelical[1] * hoopOrHelicalFac): #  puck result with helical layer must be hoopOrHelicalFac times better
                # add hoop layer
                shift = resHoop[0]
                windHoopLayer(vessel, layerNumber, shift)  # must be run since optimizeHelical ran last time
                anglesShifts.append((90, shift))
                optResult = resHoop
            else:
                anglesShifts.append((optResult[0], 0))
                optResult = resHelical
        else:
            optResult = optimizeHelical(vessel, layerNumber, puckProperties, burstPressure,
                                        polarOpeningRadius, useHelicalIndices, useFibreFailure,
                                        verbose, verbosePlot, symmetricContour)
            anglesShifts.append((optResult[0],0))
        _, _, loopIt, newDesignIndex, tfValues = optResult
        iterations += loopIt
        plotPuckAndTargetFunc(puck, tfValues, anglesShifts, optResult[0], layerNumber, runDir,
                              verbosePlot, useFibreFailure, show, elemIdxmax, hoopIndexEnd, newDesignIndex)
        vessel.saveToFile(os.path.join(runDir, 'backup.vessel'))  # save vessel
    else:
        log.warning('Reached max layers. You need to specify more initial layers')


    vessel.finishWinding()
    results = getLinearResults(vessel, puckProperties, burstPressure, symmetricContour=symmetricContour)
    if show or save:
        plotStressEpsPuck(show, os.path.join(runDir, f'sig_eps_puck_{layerNumber}.png') if save else '',
                          *results)
        thicknesses = getLayerThicknesses(vessel, symmetricContour)
        columns = ['lay{}_{:04.1f}'.format(i, angle) for i, (angle,_) in enumerate(anglesShifts)]
        thicknesses.columns=columns
        plotThicknesses(show, os.path.join(runDir, f'thicknesses.png'), thicknesses)

    # get volume and surface area
    stats = vessel.calculateVesselStatistics()
    frpMass = stats.overallFRPMass  # in [kg]

    volume = liner.getVolume()  # [l]
    dome = liner.getDome1()
    areaDome = AbstractDome.getArea([dome.getXCoords(), dome.getRCoords()])
    area = 2 * np.pi * liner.cylinderRadius * liner.cylinderLength + 2 * areaDome  # [mm**2]
    area *= 1e-6  # [m**2]
    return frpMass, volume, area, composite, iterations, *(np.array(anglesShifts).T)
