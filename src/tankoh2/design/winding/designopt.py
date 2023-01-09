import os

import numpy as np
import logging
import pandas as pd
from collections import OrderedDict

from tankoh2 import log
from tankoh2.settings import doHoopOpt, maxHoopShiftMuWind
from tankoh2.design.winding.solver import getMaxPuckLocalPuckMassIndexByShift
from tankoh2.service.exception import Tankoh2Error
from tankoh2.service.utilities import indent
from tankoh2.design.winding.material import getComposite
from tankoh2.design.winding.optimize import optimizeAngle, minimizeUtilization
from tankoh2.design.winding.solver import getLinearResults, getMaxPuckLocalPuckMass, \
    getWeightedTargetFuncByShift, getWeightedTargetFuncByAngle, getPuckStrainDiff
from tankoh2.design.winding.winding import windHoopLayer, windLayer, getPolarOpeningDiffByAngleBandMid
from tankoh2.design.winding.windingutils import getLayerThicknesses, getLinearResultsAsDataFrame, \
    getMostCriticalElementIdxPuck, checkAnglesAndShifts
from tankoh2.geometry.dome import AbstractDome, flipContour
from tankoh2.service.plot.generic import plotDataFrame, plotContour
from tankoh2.service.plot.muwind import plotStressEpsPuck, plotThicknesses, plotPuckAndTargetFunc


maxHelicalAngle = 70


def printLayer(layerNumber, postfix = ''):
    sep = '\n' + '=' * 80
    verbose = log.level < logging.INFO
    log.info((sep if verbose else '') + f'\nLayer {layerNumber} {postfix}' + (sep if verbose else ''))


def getOptScalingFactors(targetFuncWeights, puck, strainDiff, optKwargs):
    r"""Adapt mass scaling since puck values are reduced over time and mass slightly increased.

    As result, the scaling between mass and puck must be adapted for each iteration to keep the proposed
    weights of targetFuncWeights.

    Perform the following operation:

    .. math::
        \lambda = \omega / \bar{y} \cdot y_{i, y_i \neq 0}

    Where :math:`\lambda` are the new scaling factors, :math:`\omega` are the initial weights and
    :math:`\bar{y}` is the vector of the target function constituents.

    :param targetFuncWeights: initial weights of the target functions constituents
    :param puck: puck values
    :param strainDiff: difference of the strains (top, bot) for each element
    :param optKwargs: list of arguments. See tankoh2.design.winding.optimize.minimizeUtilization for a description
    :return: vector to scale the optimization values
        (used in tankoh2.design.winding.solver._getMaxPuckLocalPuckMass) for the next iteration.
        - scale puckMax
        - scale puck at last critical index
        - scale to sum(puck)
        - scale mass

    """
    vessel, layerNumberTotal = optKwargs['vessel'], optKwargs['layerNumber']
    lastTargetFucValues = np.array(getMaxPuckLocalPuckMass(optKwargs, (puck, strainDiff), False)[:-2])
    lastLayersMass = np.sum([vessel.getVesselLayer(layerNumber).getVesselLayerPropertiesSolver().getWindingLayerResults().fiberMass
                             for layerNumber in range(layerNumberTotal)])
    meanLayerMass = lastLayersMass / layerNumberTotal
    lastTargetFucValues[3] = meanLayerMass
    omega = targetFuncWeights
    scaling = [y for weight, y in zip(targetFuncWeights, lastTargetFucValues) if weight > 1e-8][0]

    targetFuncScaling = omega / lastTargetFucValues * scaling
    return targetFuncScaling


def windAnglesAndShifts(anglesShifts, vessel, compositeArgs):
    layerNumber = len(anglesShifts)
    angles = [a for a, _ in anglesShifts]
    composite = getComposite(angles, *compositeArgs)
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
    """When angle is close to fitting radius, sometimes the thickness of a layer is corrupt

    will be resolved by increasing the angle a little
    """
    thicknesses = getLayerThicknesses(vessel, symmetricContour)
    lastLayThick = thicknesses.loc[:, thicknesses.columns[-1]]
    if lastLayThick[::-1].idxmax() - lastLayThick.idxmax() > lastLayThick.shape[0] * 0.1:
        #adjust bounds
        bounds = [angle+0.1, bounds[1]]
        return False, bounds
    return True, bounds


def optimizeHelical(polarOpeningRadius, bandWidth, optKwArgs):
    """Optimize the angle of helical layers

    :param polarOpeningRadius: polar opening radius of tank
    :param bandWidth: width of the band
    :param optKwArgs: dict with optimization arguments. See tankoh2.design.winding.optimize.minimizeUtilization
         for a description
    :return:
    """
    log.debug('Optimize helical layer')
    # get location of critical element
    vessel, layerNumber = optKwArgs['vessel'], optKwArgs['layerNumber']
    symmetricContour = optKwArgs['symmetricContour']
    windLayer(vessel, layerNumber, maxHelicalAngle)
    minAngle, _, _ = optimizeAngle(vessel, polarOpeningRadius, layerNumber, (1., maxHelicalAngle), bandWidth,
                                   targetFunction=getPolarOpeningDiffByAngleBandMid)
    bounds = [minAngle, maxHelicalAngle]

    for tryIterations in range(20):
        angle, funcVal, loopIt, tfPlotVals = minimizeUtilization(bounds,
                                                                 #getMaxPuckByAngle,
                                                                 getWeightedTargetFuncByAngle,
                                                                 optKwArgs, localOptimization='both')

        layerOk, bounds = checkThickness(vessel, angle, bounds, symmetricContour)
        if layerOk:
            break

    else:
        raise Tankoh2Error('Could not correct the thickness of the actual layer. Possibly the number of '
                           'nodes in respect to the tank radius and band width is not sufficient')

    # calculate border indices of the new layer
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
              f'polar opening contour coord index {newDesignIndexes}')

    return angle, funcVal, loopIt, newDesignIndexes, tfPlotVals


def distributeHoop(maxHoopShift, anglesShifts, compositeArgs, optArgs):
    """Distributes all existing hoop layers with a linear hoop shift

    All existing 90 deg layers will be distributed linearly in the interval [-maxHoopShift, maxHoopShift].

    This is a alternative option in contrast to optimizeHoop()
    :param maxHoopShift: maximum hoop shift allowed.
    :param anglesShifts: Existing angles and hoop shifts
    :param compositeArgs: composite properties as required by tankoh2.design.winding.material.getComposite()
    :param optArgs: args to the optimizer callback function.
    See tankoh2.design.optimize.minimizeUtilization() for a detailed description

    :return: tuple:
        - hoop shift,
        - funcVal,
        - loopIt,
        - newDesignIndexes,
        - tfPlotVals
    """
    vessel = optArgs['vessel']
    hoopLayerCount = len([angle for angle,s in anglesShifts if angle > 89])
    maxBound = np.min([maxHoopShift, maxHoopShiftMuWind])  # 250 is the maximum defined in µWind at the moment
    minBound = -maxBound / 2
    if hoopLayerCount == 0:
        hoopShifts = [np.mean([minBound, maxBound])]
    else:
        hoopShifts = np.linspace(maxBound, minBound, hoopLayerCount + 1, endpoint=False)
    hoopShiftsIter = iter(hoopShifts)
    for (angle, _), index in zip(anglesShifts, range(len(anglesShifts))):
        if angle > 89:
            anglesShifts[index] = (angle, next(hoopShiftsIter))
    windAnglesAndShifts(anglesShifts + [(90,next(hoopShiftsIter))], vessel, compositeArgs)
    checkAnglesAndShifts(anglesShifts + [(90,hoopShifts[-1])], vessel)
    results = getMaxPuckLocalPuckMassIndexByShift(hoopShifts[-1], optArgs)
    tfValue = np.sum(results[:-2])
    return hoopShifts[-1], tfValue, 1, [], None


def optimizeHoop(maxHoopShift, optKwArgs):
    """
    :param maxHoopShift: maximum hoop shift
    :param optKwArgs: dcit with optimization arguments. See tankoh2.design.winding.optimize.minimizeUtilization
         for a description
    :return: tuple:
        - hoop shift,
        - funcVal,
        - loopIt,
        - newDesignIndexes,
        - tfPlotVals
    """
    log.debug('Optimize hoop layer')
    bounds = [0, min(maxHoopShift, maxHoopShiftMuWind)]

    vessel, layerNumber = optKwArgs['vessel'], optKwArgs['layerNumber']
    symmetricContour = optKwArgs['symmetricContour']
    windHoopLayer(vessel, layerNumber, 0)

    shift, funcVal, loopIt, tfPlotVals = minimizeUtilization(bounds,
                                                             #getMaxPuckByShift,
                                                             getWeightedTargetFuncByShift,
                                                             optKwArgs)

    # calculate border indices of the new layer
    mandrel1 = vessel.getVesselLayer(layerNumber).getOuterMandrel1()
    r1, l1 = mandrel1.getRArray(), mandrel1.getLArray()
    elemCount1 = mandrel1.numberOfNodes - 1
    cylLenIdx1 = mandrel1.numberOfNodes - np.argmin(np.abs(r1 - r1[0])[::-1]) # np.argmin from the back of the mandrels radii
    hoopLength1 = l1[cylLenIdx1] + shift
    if symmetricContour:
        newDesignIndexes = [np.argmin(np.abs(l1 - hoopLength1))]
    else:
        mandrel2 = vessel.getVesselLayer(layerNumber).getOuterMandrel1()
        r2, l2 = mandrel2.getRArray(), mandrel2.getLArray()
        cylLenIdx2 = mandrel2.numberOfNodes - np.argmin(np.abs(r2 - r2[0])[::-1])  # np.argmin from the back of the mandrels radii
        hoopLength2 = l2[cylLenIdx2] + shift
        newDesignIndexes = [elemCount1 - np.argmin(np.abs(l1 - hoopLength1)),
                            elemCount1 + np.argmin(np.abs(l2 - hoopLength2))]
    log.debug(f'hoop shift {shift}, puck value {funcVal}, loopIterations {loopIt}, '
              f'hoop end contour coord index {newDesignIndexes}')

    return shift, funcVal, loopIt, newDesignIndexes, tfPlotVals


def _getHoopAndHelicalIndices(vessel, symmetricContour,
                              relRadiusHoopLayerEnd):
    """calculate borders and element regions for optimization

    :param vessel: µWind vessel instance
    :param symmetricContour: Flag if the contour is symmetric
    :param relRadiusHoopLayerEnd: relative radius (to cyl radius) where hoop layers end
    :return:
        - hoopStart: index where the hoop region starts (0 if symm contour, on mandrel1 of unsymm contour)
        - hoopEnd: index where the hoop region ends (mandrel1 if symm contour, on mandrel2 of unsymm contour)
        - maxHoopShift: maximal length of hoop shifts into dome section
        - useHoopIndices: list of element indicies that will be evaluated (stress, puck) in the hoop region
        - useHelicalIndices: list of element indicies that will be evaluated (stress, puck) in the dome region
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
        mandrelElementCount = mandrel.numberOfNodes - 1
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
                 useFibreFailure, relRadiusHoopLayerEnd, initialAnglesAndShifts, targetFuncWeights):
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
        hoopLayerThickness, layerThkHelical, material, sectionAreaFibre, rovingWidthHoop, rovingWidthHelical,
        numberOfRovings, tex, designFilename, tankname
    :param verbosePlot: flag if more plots should be created
    :param useFibreFailure: flag, use fibre failure or inter fibre failure
    :param relRadiusHoopLayerEnd: relative radius (to cyl radius) where hoop layers end
    :param initialAnglesAndShifts: List with tuples defining angles and shifts used before optimization starts
    :param targetFuncWeights: initial weights of the target functions constituents
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
    def getPuckAndStrainDiff():

        puck, strainDiff = getPuckStrainDiff(vessel, puckProperties, burstPressure,
                                             symmetricContour=symmetricContour,
                                             useFibreFailure=useFibreFailure, useMeridianStrain=True)
        return puck, strainDiff

    vessel.resetWindingSimulation()

    show = False
    save = True
    layerNumber = 0
    iterations = 0
    hoopOrHelicalFac = 1.

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
        composite = windAnglesAndShifts(anglesShifts, vessel, compositeArgs)

    # create other layers
    vessel.saveToFile(os.path.join(runDir, 'backup.vessel'))  # save vessel
    for layerNumber in range(layerNumber + 1, maxLayers):
        puck, strainDiff = getPuckAndStrainDiff()
        elemIdxPuckMax, layermax = getMostCriticalElementIdxPuck(puck)
        elemIdxBendMax = np.argmax(strainDiff)
        puckMax = puck.max().max()

        if puckMax < 1:
            log.debug('End Iteration')
            # stop criterion reached
            columns = ['lay{}_{:04.1f}'.format(i, angle) for i, (angle, _) in enumerate(anglesShifts)]
            puck.columns = columns
            plotDataFrame(show, os.path.join(runDir, f'puck_{layerNumber}.png'), puck,
                          yLabel='puck fibre failure' if useFibreFailure else 'puck inter fibre failure')
            layerNumber -= 1
            break

        # add one layer
        printLayer(layerNumber)
        log.debug(f'Layer {layerNumber}, already wound angles, shifts: {anglesShifts}')
        windAnglesAndShifts(anglesShifts + [(90, 0.)], vessel, compositeArgs)

        # check zone of highest puck values
        add90DegLay1FF = layerNumber == 1 and useFibreFailure
        maxInHoopRegion = hoopStart <= elemIdxPuckMax <= hoopEnd
        if add90DegLay1FF:
            optHoopRegion = True  # this layer should be a hoop layer
        elif useFibreFailure:
            # check if max puck value occurred in hoop or helical layer
            optHoopRegion = anglesShifts[layermax][0] > 89
        else:
            optHoopRegion = maxInHoopRegion
            log.info(f'{hoopStart} <= {elemIdxPuckMax} <= {hoopEnd}')

        optKwargs = OrderedDict([
            ('vessel', vessel),
            ('layerNumber', layerNumber),
            ('puckProperties', puckProperties),
            ('burstPressure', burstPressure),
            ('useIndices', useHelicalIndices),
            ('useFibreFailure', useFibreFailure),
            ('verbosePlot', verbosePlot),
            ('symmetricContour', symmetricContour),
            ('elemIdxPuckMax', elemIdxPuckMax),
            ('elemIdxBendMax', elemIdxBendMax),
            ('targetFuncScaling',None),
        ])
        if optHoopRegion:
            targetFuncScaling = getOptScalingFactors(targetFuncWeights, puck, strainDiff, optKwargs)
            optKwargs['targetFuncScaling'] = targetFuncScaling
            optKwargs['useIndices'] = None
            resHelical = optimizeHelical(polarOpeningRadius, bandWidth, optKwargs)
            optKwargs['useIndices'] = useHoopIndices
            if doHoopOpt:
                resHoop = optimizeHoop(maxHoopShift, optKwargs)
            else:
                resHoop = distributeHoop(maxHoopShift, anglesShifts, compositeArgs, optKwargs)
            if not add90DegLay1FF:
                log.info(f'Max Puck in hoop region. Min targetFuc hoop {resHoop[1]}, '
                         f'min targetFuc helical {resHelical[1]} * {hoopOrHelicalFac}')
            if add90DegLay1FF or (resHoop[1] < resHelical[1] * hoopOrHelicalFac):  # puck result with helical layer must be hoopOrHelicalFac times better
                # add hoop layer
                shift = resHoop[0]
                windHoopLayer(vessel, layerNumber, shift)  # must be run since optimizeHelical ran last time
                anglesShifts.append((90, shift))
                checkAnglesAndShifts(anglesShifts, vessel)
                optResult = resHoop #  list(resHoop[:-1]) + list(resHelical[-1:])
            else:
                # add helical layer
                optResult = resHelical
                angle = optResult[0]
                windLayer(vessel, layerNumber, angle)  # must be run since optimizeHoop ran last time
                anglesShifts.append((angle, 0))
                checkAnglesAndShifts(anglesShifts, vessel)
                optResult = optimizeHelical(polarOpeningRadius, bandWidth, optKwargs)
        else:
            if maxInHoopRegion:
                # case FF: if an helical angle in the hoop region has the maximum, check at hoop indices
                optKwargs['useIndices'] = None
            targetFuncScaling = getOptScalingFactors(targetFuncWeights, puck, strainDiff, optKwargs)
            optKwargs['targetFuncScaling'] = targetFuncScaling
            optResult = optimizeHelical(polarOpeningRadius, bandWidth, optKwargs)
            anglesShifts.append((optResult[0],0))
            checkAnglesAndShifts(anglesShifts, vessel)

        composite = windAnglesAndShifts(anglesShifts, vessel, compositeArgs)
        _, _, loopIt, newDesignIndexes, tfValues = optResult
        iterations += loopIt
        plotPuckAndTargetFunc(puck, tfValues, anglesShifts, layerNumber, runDir,
                              verbosePlot, useFibreFailure, show, elemIdxPuckMax, hoopStart, hoopEnd,
                              newDesignIndexes, (targetFuncWeights, targetFuncScaling))

        vessel.saveToFile(os.path.join(runDir, f'backup.vessel'))  # save vessel
        if verbosePlot:
            vessel.saveToFile(os.path.join(runDir, 'plots', f'backup{layerNumber}.vessel'))  # save vessel
    else:
        puck, strainDiff = getPuckAndStrainDiff()
        puckMax = puck.max().max()
        columns = ['lay{}_{:04.1f}'.format(i, angle) for i, (angle, _) in enumerate(anglesShifts)]
        puck.columns = columns
        plotDataFrame(False, os.path.join(runDir, f'puck_{layerNumber+1}.png'), puck,
                      yLabel='puck fibre failure' if useFibreFailure else 'puck inter fibre failure')
        log.warning(f'Reached max layers ({maxLayers}) but puck values are '
                    f'still greater 1 ({puck.max().max()}). You need to specify more layers in "maxLayers" '
                    f'or adjust the optimization weights in "targetFuncWeights".')

    vessel.finishWinding()

    # postprocessing
    # ##############################################################################

    results = getLinearResults(vessel, puckProperties, burstPressure, symmetricContour=symmetricContour)
    thicknesses = getLayerThicknesses(vessel, symmetricContour)
    if show or save:
        plotStressEpsPuck(show, os.path.join(runDir, f'sig_eps_puck.png') if save else '', *results)
        plotThicknesses(show, os.path.join(runDir, f'thicknesses.png'), thicknesses)

    thicknesses.columns = ['thk_lay{}'.format(i) for i, (angle,_) in enumerate(anglesShifts)]
    mechResults = getLinearResultsAsDataFrame(results)

    mandrel = liner.getMandrel1()
    elementLengths = pd.DataFrame(np.array([mandrel.getLArray()]).T, columns=['elementLength'])
    elementalResults = pd.concat([elementLengths, thicknesses, mechResults], join='outer', axis=1)
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
    reserveFac = 1 / puckMax
    S11 = results[0]
    minCylinderStress = np.min(S11[0, :])
    maxCylinderStress = np.max(S11[0, :])
    stressRatio = minCylinderStress/maxCylinderStress
    return frpMass, area, iterations, reserveFac, stressRatio, *(np.array(anglesShifts).T)


