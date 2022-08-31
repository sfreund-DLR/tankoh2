import os

import numpy as np
import logging
import pandas as pd

from tankoh2 import log
from tankoh2.service.exception import Tankoh2Error
from tankoh2.service.utilities import indent
from tankoh2.design.winding.material import getComposite
from tankoh2.design.winding.optimize import optimizeAngle, minimizeUtilization
from tankoh2.design.winding.solver import getMaxPuckByAngle, getMaxPuckByShift, getCriticalElementIdx, \
    getLinearResults, getLinearResultsAsDataFrame
from tankoh2.design.winding.winding import windHoopLayer, windLayer, getPolarOpeningDiffByAngleBandMid
from tankoh2.design.winding.windingutils import getLayerThicknesses
from tankoh2.geometry.dome import AbstractDome, flipContour
from tankoh2.service.plot.generic import plotDataFrame, plotContour
from tankoh2.service.plot.muwind import plotStressEpsPuck, plotThicknesses, plotPuckAndTargetFunc


maxHelicalAngle = 70

def printLayer(layerNumber, postfix = ''):
    sep = '\n' + '=' * 80
    verbose = log.level < logging.INFO
    log.info((sep if verbose else '') + f'\nLayer {layerNumber} {postfix}' + (sep if verbose else ''))


def windAnglesAndShifts(anglesShifts, vessel, compositeArgs):
    layerNumber = len(anglesShifts)
    hoopLayerThickness, helixLayerThickenss = compositeArgs[1:3]
    angles = [a for a, _ in anglesShifts]
    thicknesses = [helixLayerThickenss if angle < 90 else hoopLayerThickness for angle in angles]
    composite = getComposite(angles, thicknesses, *compositeArgs[3:])
    log.debug(f'Layer {layerNumber}, already wound angles, shifts: {anglesShifts}')
    vessel.setComposite(composite)
    for layerNumber, (angle, shift) in enumerate(anglesShifts):
        if angle>89:
            vessel.setHoopLayerShift(layerNumber, shift, True)
    try:
        vessel.finishWinding()
    except (IndexError, RuntimeError):
        vessel.saveToFile('backup.vessel')
        log.info(indent(anglesShifts))
        raise
    return composite


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
                    polarOpeningRadius, bandWidth, useIndices, useFibreFailure, verbosePlot, symmetricContour):
    log.debug('Optimize helical layer')
    # get location of critical element

    windLayer(vessel, layerNumber, maxHelicalAngle)
    minAngle, _, _ = optimizeAngle(vessel, polarOpeningRadius, layerNumber, (1., maxHelicalAngle), bandWidth,
                                   targetFunction=getPolarOpeningDiffByAngleBandMid)
    bounds = [minAngle, maxHelicalAngle]

    optArgs = [vessel, layerNumber, puckProperties, burstPressure, useIndices, useFibreFailure,
            symmetricContour]
    for tryIterations in range(20):
        angle, funcVal, loopIt, tfPlotVals = minimizeUtilization(bounds, getMaxPuckByAngle, optArgs,
                                                                 verbosePlot, localOptimization='both')

        layerOk, bounds = checkThickness(vessel, angle, bounds, symmetricContour)
        if layerOk:
            break

    else:
        raise Tankoh2Error('Could not correct the thickness of the actual layer. Possibly the number of '
                           'nodes in respect to the tank radius and band width is not sufficient')
    layerPolarOpeningRadius1 = windLayer(vessel, layerNumber, angle)
    radii1 = vessel.getVesselLayer(layerNumber).getOuterMandrel1().getRArray()
    if symmetricContour:
        newDesignIndexes = [np.argmin(np.abs(radii1 - layerPolarOpeningRadius1))]
    else:
        elemCount1 = len(radii1) - 1
        layerPolarOpeningRadius2 = vessel.getPolarOpeningR(layerNumber, False)
        radii2 = vessel.getVesselLayer(layerNumber).getOuterMandrel2().getRArray()
        newDesignIndexes = [elemCount1 - np.argmin(np.abs(radii1 - layerPolarOpeningRadius1)),
                            elemCount1 + np.argmin(np.abs(radii2 - layerPolarOpeningRadius2))]
    log.debug(f'anlge {angle}, puck value {funcVal}, loopIterations {loopIt}, '
              f'polar opening contour coord {newDesignIndexes}')

    return angle, funcVal, loopIt, newDesignIndexes, tfPlotVals


def optimizeHoop(vessel, layerNumber, puckProperties, burstPressure,
                 useIndices, useFibreFailure, maxHoopShift, verbosePlot, symmetricContour):
    """
    :param vessel:
    :param layerNumber:
    :param puckProperties:
    :param burstPressure:
    :param useIndices: element indicies that should be used for strength evaluation
    :param useFibreFailure:
    :param maxHoopShift:
    :param verbosePlot:
    :param symmetricContour: Flag if the contour is symmetric
    :return:
    """
    log.debug('Optimize hoop layer')
    bounds = [0, maxHoopShift]

    optArgs = [vessel, layerNumber, puckProperties, burstPressure, useIndices, useFibreFailure,
            symmetricContour]
    shift, funcVal, loopIt, tfPlotVals = minimizeUtilization(bounds, getMaxPuckByShift, optArgs, verbosePlot)

    mandrel1 = vessel.getVesselLayer(layerNumber).getOuterMandrel1()
    r1, l1 = mandrel1.getRArray(), mandrel1.getLArray()
    cylLenIdx1 = len(r1) - np.argmin(np.abs(r1 - r1[0])[::-1]) # np.argmin from the back of the mandrels radii
    hoopLength1 = l1[cylLenIdx1] + shift
    if symmetricContour:
        newDesignIndexes = [np.argmin(np.abs(l1 - hoopLength1))]
    else:
        mandrel2 = vessel.getVesselLayer(layerNumber).getOuterMandrel1()
        elemCount1 = len(r1) - 1
        r2, l2 = mandrel2.getRArray(), mandrel2.getLArray()
        cylLenIdx2 = len(r2) - np.argmin(np.abs(r2 - r2[0])[::-1])  # np.argmin from the back of the mandrels radii
        hoopLength2 = l2[cylLenIdx2] + shift
        newDesignIndexes = [elemCount1 - np.argmin(np.abs(l1 - hoopLength1)),
                            elemCount1 + np.argmin(np.abs(l2 - hoopLength2))]
    log.debug(f'hoop shift {shift}, puck value {funcVal}, loopIterations {loopIt}, '
              f'hoop end contour coord {newDesignIndexes}')

    return shift, funcVal, loopIt, newDesignIndexes, tfPlotVals

def _getHoopAndHelicalIndices(vessel, symmetricContour,
                               relRadiusHoopLayerEnd):
    """calculate borders and element regions for optimization

    :param vessel: µWind vessel instance
    :param symmetricContour: Flag if the contour is symmetric
    :param relRadiusHoopLayerEnd: relative radius (to cyl radius) where hoop layers end
    :return:
        - hoopIndexEnd: index which distinguishes between indicies of
            cylindrical and dome section (mandrel1)
        - maxHoopShift: maximal length of hoop shifts into dome section
        - useHoopIndices:
        - useHelicalIndices
    """
    liner = vessel.getLiner()
    mandrel1 = liner.getMandrel1()
    if symmetricContour:
        mandrels = [mandrel1]
    else:
        mandrels = [liner.getMandrel2() if not symmetricContour else None, mandrel1]

    useHoopIndices, useHelicalIndices = np.array([], dtype=np.int), np.array([], dtype=np.int)
    maxHoopShifts = []
    for mandrel in mandrels:
        r = mandrel.getRArray()
        rCyl = r[0]
        mandrelElementCount = len(r)-1
        hoopHelicalBorderIndex = np.argmin(np.abs(r - rCyl*relRadiusHoopLayerEnd))
        maxHoopShifts.append(mandrel.getLArray()[hoopHelicalBorderIndex] - liner.cylinderLength/2)

        hoopIndexStart = int(np.argmax((-mandrel.getRArray()+rCyl)>rCyl*1e-4) * 0.7) # not all hoop elements must be evaluated
        hoopIndices = np.linspace(hoopIndexStart, hoopHelicalBorderIndex, hoopHelicalBorderIndex-hoopIndexStart+1, dtype=np.int)
        if mandrel is mandrel1:
            hoopIndices = np.append([0], hoopIndices)
        helicalIndices = np.linspace(hoopHelicalBorderIndex, mandrelElementCount, mandrelElementCount-hoopHelicalBorderIndex+1, dtype=np.int)
        if not symmetricContour and mandrel is mandrel1:
            # shift existing indices and include by mandrel 1 indices
            useHoopIndices += mandrelElementCount
            useHelicalIndices += mandrelElementCount
            # twist indices
            hoopIndices = mandrelElementCount - hoopIndices[::-1]
            helicalIndices = mandrelElementCount - helicalIndices[::-1]

        useHoopIndices = np.append(hoopIndices, useHoopIndices)
        useHelicalIndices = np.append(helicalIndices, useHelicalIndices)

    hoopBounds = [np.min(useHoopIndices), np.max(useHoopIndices)]
    maxHoopShift = np.min(maxHoopShifts)
    return *hoopBounds, maxHoopShift, useHoopIndices, useHelicalIndices


def designLayers(vessel, maxLayers, polarOpeningRadius, bandWidth, puckProperties, burstPressure, symmetricContour,
                 runDir, compositeArgs, verbosePlot,
                 useFibreFailure, relRadiusHoopLayerEnd, initialAnglesAndShifts):
    """Perform design optimization layer by layer

    :param vessel: vessel instance of mywind
    :param maxLayers: maximum numbers of layers
    :param polarOpeningRadius: min polar opening where fitting is attached [mm]
    :param bandWidth: width of the band
    :param puckProperties: puckProperties instance of mywind
    :param burstPressure: burst pressure [MPa]
    :param symmetricContour: Flag if the contour is symmetric
    :param runDir: directory where to store results
    :param compositeArgs: properties defining the composite:
        thicknesses, hoopLayerThickness, helixLayerThickenss, material,
        sectionAreaFibre, rovingWidth, numberOfRovings, tex, designFilename, tankname
    :param verbosePlot: flag if more plots should be created
    :param useFibreFailure: flag, use fibre failure or inter fibre failure
    :param relRadiusHoopLayerEnd: relative radius (to cyl radius) where hoop layers end
    :param initialAnglesAndShifts: List with tuples defining angles and shifts used before optimization starts
    :return: frpMass, volume, area, composite, iterations, anglesShifts

    Strategy:

    #. Start with helical layer:
        #. Maximize layer angle that still attaches to the fitting
        #. add layer with this angle
    #. If puck FF is used, add hoop layer
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
        #. Minimize puck fibre failure:
                #. Set angle
                #. Use analytical linear solver
                #. return max puck fibre failure
            #. Apply optimal angle to actual layer
            #. next iteration step
    #. postprocessing: plot stresses, strains, puck, thickness
    """
    def getPuck():
        puckFF, puckIFF = getLinearResults(vessel, puckProperties, burstPressure,
                                           puckOnly=True, symmetricContour=symmetricContour)
        return  puckFF if useFibreFailure else puckIFF

    vessel.resetWindingSimulation()

    show = False
    save = True
    layerNumber = 0
    iterations = 0
    hoopOrHelicalFac = 1
    liner = vessel.getLiner()

    indiciesAndShifts = _getHoopAndHelicalIndices(vessel, symmetricContour, relRadiusHoopLayerEnd)
    hoopStart, hoopEnd, maxHoopShift, useHoopIndices, useHelicalIndices = indiciesAndShifts
    x,r = liner.getMandrel1().getXArray(), liner.getMandrel1().getRArray()
    if not symmetricContour:
        x,r = flipContour(x,r)
        x = np.append(x, liner.getMandrel2().getXArray()[1:] + np.max(x))
        r = np.append(r, liner.getMandrel2().getRArray()[1:])
    plotContour(False,  os.path.join(runDir, f'contour.png'), x, r,
                vlines=[hoopStart, hoopEnd], vlineColors=['black', 'black'])
    log.debug('Find minimal possible angle')

    minAngle, _, _ = optimizeAngle(vessel, polarOpeningRadius, layerNumber, (1., maxHelicalAngle),
                                   bandWidth, targetFunction=getPolarOpeningDiffByAngleBandMid)

    if initialAnglesAndShifts is not None and len(initialAnglesAndShifts) > 0:
        # wind given angles
        composite = windAnglesAndShifts(initialAnglesAndShifts, vessel, compositeArgs)
        anglesShifts = initialAnglesAndShifts
        layerNumber = len(anglesShifts) - 1
    else:
        # introduce layer up to the fitting. Optimize required angle
        printLayer(layerNumber, '- initial helical layer')
        windLayer(vessel, layerNumber, minAngle)
        anglesShifts = [(minAngle,0)]

    # layerNumber += 1
    #
    # # wind layer up to the end of conical tank section
    # conicalAngle = 15
    # printLayer(layerNumber, '- conical layer')
    # anglesShifts += [(conicalAngle, 0)]

    composite = windAnglesAndShifts(anglesShifts, vessel, compositeArgs)

    # create other layers
    vessel.saveToFile(os.path.join(runDir, 'backup.vessel'))  # save vessel
    puck = None
    for layerNumber in range(layerNumber + 1, maxLayers):
        puck = getPuck()
        elemIdxmax, layermax = getCriticalElementIdx(puck)

        if puck.max().max() < 1:
            log.debug('End Iteration')
            # stop criterion reached
            columns = ['lay{}_{:04.1f}'.format(i, angle) for i, (angle, _) in enumerate(anglesShifts)]
            puck.columns = columns
            plotDataFrame(False, os.path.join(runDir, f'puck_{layerNumber}.png'), puck,
                          yLabel='puck fibre failure' if useFibreFailure else 'puck inter fibre failure')
            layerNumber -= 1
            break

        # add one layer
        printLayer(layerNumber)
        log.debug(f'Layer {layerNumber}, already wound angles, shifts: {anglesShifts}')
        composite = windAnglesAndShifts(anglesShifts + [(90, 0.)], vessel, compositeArgs)
        from tankoh2.design.winding.material import saveComposite
        saveComposite(composite, 'test', 'testDesign')

        # check zone of highest puck values
        if layerNumber == 1 and useFibreFailure:
            # this layer should be a hoop layer
            optHoopRegion = True

        elif useFibreFailure:
            # check if max puck value occurred in hoop or helical layer
            optHoopRegion = anglesShifts[layermax][0] > 89

        else:
            optHoopRegion = hoopStart <= elemIdxmax <= hoopEnd
            log.info(f'{hoopStart} <= {elemIdxmax} <= {hoopEnd}')
        if optHoopRegion:
            resHoop = optimizeHoop(vessel, layerNumber, puckProperties, burstPressure,
                                   #[elemIdxmax],
                                   useHoopIndices,
                                   useFibreFailure, maxHoopShift, verbosePlot, symmetricContour)
            resHelical = optimizeHelical(vessel, layerNumber, puckProperties, burstPressure,
                                         polarOpeningRadius, bandWidth,
                                         #[elemIdxmax],
                                         useHoopIndices,
                                         useFibreFailure, verbosePlot, symmetricContour)
            if not (layerNumber == 1 and useFibreFailure):
                log.info(f'Max Puck in hoop region. Min Puck hoop {resHoop[1]}, min puck helical {resHelical[1]}')
            if (layerNumber == 1 and useFibreFailure) or (resHoop[1] < resHelical[1] * hoopOrHelicalFac):  # puck result with helical layer must be hoopOrHelicalFac times better
                # add hoop layer
                shift = resHoop[0]
                windHoopLayer(vessel, layerNumber, shift)  # must be run since optimizeHelical ran last time
                anglesShifts.append((90, shift))
                optResult = resHoop

            else:
                optResult = resHelical
                anglesShifts.append((optResult[0], 0))
        else:
            optResult = optimizeHelical(vessel, layerNumber, puckProperties, burstPressure,
                                        polarOpeningRadius, bandWidth,
                                        #[elemIdxmax],
                                        useHelicalIndices,
                                        useFibreFailure, verbosePlot, symmetricContour)

            anglesShifts.append((optResult[0],0))

        _, _, loopIt, newDesignIndexes, tfValues = optResult
        iterations += loopIt
        plotPuckAndTargetFunc(puck, tfValues, anglesShifts, optResult[0], layerNumber, runDir,
                              verbosePlot, useFibreFailure, show, elemIdxmax, hoopStart, hoopEnd,
                              newDesignIndexes)

        vessel.saveToFile(os.path.join(runDir, 'backup.vessel'))  # save vessel
    else:
        if puck is None:
            puck = getPuck()
        log.warning(f'Reached max layers ({maxLayers}) but puck values are '
                    f'still greater 1 ({puck.max().max()}). You need to specify more initial layers')

    vessel.finishWinding()

    # postprocessing
    # ##############################################################################

    results = getLinearResults(vessel, puckProperties, burstPressure, symmetricContour=symmetricContour)
    thicknesses = getLayerThicknesses(vessel, symmetricContour)
    if show or save:
        plotStressEpsPuck(show, os.path.join(runDir, f'sig_eps_puck.png') if save else '',
                          *results)
        plotThicknesses(show, os.path.join(runDir, f'thicknesses.png'), thicknesses)

    thicknesses.columns = ['thk_lay{}'.format(i) for i, (angle,_) in enumerate(anglesShifts)]
    mechResults = getLinearResultsAsDataFrame(results)
    elementalResults = pd.concat([thicknesses, mechResults], join='outer', axis=1)
    elementalResults.to_csv(os.path.join(runDir, 'elementalResults.csv'), sep=';')

    if log.level == logging.DEBUG:
        # vessel.printSimulationStatus()
        composite.info()

    # get volume and surface area
    stats = vessel.calculateVesselStatistics()
    frpMass = stats.overallFRPMass  # in [kg]
    dome = liner.getDome1()
    areaDome = AbstractDome.getArea([dome.getXCoords(), dome.getRCoords()])
    area = 2 * np.pi * liner.cylinderRadius * liner.cylinderLength + 2 * areaDome  # [mm**2]
    area *= 1e-6  # [m**2]
    return frpMass, area, iterations, *(np.array(anglesShifts).T)
