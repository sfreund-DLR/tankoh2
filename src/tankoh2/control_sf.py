"""control a tank optimization"""

import os, sys
import numpy as np
import datetime

import tankoh2.utilities
from tankoh2 import programDir, log, pychain
from tankoh2.service import indent, getRunDir, plotStressEpsPuck, plotDataFrame, getTimeString, plotContour
from tankoh2.utilities import updateName, copyAsJson, getLayerThicknesses
from tankoh2.contour import getLiner, getDome
from tankoh2.material import getMaterial, getComposite, readLayupData, saveComposite
from tankoh2.winding import windLayer, windHoopLayer, getNegAngleAndPolarOpeningDiffByAngle, \
    getAngleAndPolarOpeningDiffByAngle
from tankoh2.optimize import optimizeAngle, minimizeUtilization
from tankoh2.solver import getLinearResults, getCriticalElementIdx, getPuck, \
    getPuckLinearResults, getMaxFibreFailureByShift
from tankoh2.existingdesigns import defaultDesign

resultNames = ['frpMass', 'volume', 'area', 'lzylinder', 'numberOfLayers', 'iterations', 'duration', 'angles', 'hoopLayerShifts']
resultUnits = ['kg', 'dm^2', 'm^2', 'mm', '', '', 's', '°', 'mm']

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
                 composite, compositeArgs, verbose, useFibreFailure):
    """
        :param vessel: vessel instance of mywind
        :param maxLayers: maximum numbers of layers
        :param minPolarOpening: min polar opening where fitting is attached [mm]
        :param puckProperties: puckProperties instance of mywind
        :param burstPressure: burst pressure [MPa]
        :param runDir: directory where to store results
        :param composite: composite instance of mywind
        :param compositeArgs: properties defining the composite:
            thicknesses, hoopLayerThickness, helixLayerThickenss, material,
            sectionAreaFibre, rovingWidth, numberOfRovings, tex, designFilename, tankname
        :param verbose: flag if verbose output is needed
        :param useFibreFailure: flag, use fibre failure or inter fibre failure
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
    minAngle, _, _ = optimizeAngle(vessel, minPolarOpening, layerNumber, 1., False,
                                   targetFunction=getAngleAndPolarOpeningDiffByAngle)
    plotContour(False,  os.path.join(runDir, f'contour.png'), mandrel.getXArray(), mandrel.getRArray())

    rMax = mandrel.getRArray()[0]
    dropHoopIndexStart = np.argmax((-mandrel.getRArray()+rMax)>rMax*1e-4) - 10
    #dropHoopIndexEnd = np.argmin(np.abs(mandrel.getRArray() - dome.cylinderRadius*0.98))
    dropHoopIndexEnd = np.argmin(np.abs(mandrel.getRArray() - dome.cylinderRadius*0.74))
    hoopOrHelicalIndex = np.argmin(np.abs(mandrel.getRArray() - dome.cylinderRadius*0.995))
    maxHoopShift = mandrel.getLArray()[dropHoopIndexEnd] - liner.cylinderLength/2
    dropHoopIndicies = list(range(0, dropHoopIndexStart)) + list(range(dropHoopIndexEnd, elementCount))
    dropHelicalIndicies = range(0, hoopOrHelicalIndex)

    # introduce layer up to the fitting. Optimize required angle
    printLayer(layerNumber, verbose)
    angle, _, _ = optimizeAngle(vessel, minPolarOpening, layerNumber, minAngle, False,
                                targetFunction=getNegAngleAndPolarOpeningDiffByAngle)
    anglesShifts.append((angle,0))
    layerNumber += 1

    # add hoop layer
    resHoop = optimizeHoop(vessel, layerNumber, puckProperties, burstPressure,
                           dropHoopIndicies, maxHoopShift, verbose)
    shift, funcVal, loopIt, newDesignIndex = resHoop
    windHoopLayer(vessel, layerNumber, shift)
    anglesShifts.append((90, shift))

    #printLayer(layerNumber, verbose)
    #windLayer(vessel, layerNumber, 90)
    #anglesShifts.append((90.,0))


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
                                         minPolarOpening, dropHoopIndicies, verbose)
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
                                                                     minPolarOpening, dropHelicalIndicies, verbose)

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
        plotDataFrame(show, os.path.join(runDir, f'thicknesses_{getTimeString()}.png'), thicknesses,
                      yLabel='layer thicknesses')

    # get volume and surface area
    stats = vessel.calculateVesselStatistics()
    frpMass = stats.overallFRPMass  # in [kg]

    volume = liner.getVolume()  # [l]
    r, x = dome.getRCoords(), dome.getXCoords()
    areaDome = np.pi * (r[:-1] + r[1:]) * np.sqrt((r[:-1] - r[1:]) ** 2 + (x[:-1] - x[1:]) ** 2)
    area = 2 * np.pi * liner.cylinderRadius * liner.cylinderLength + 2 * np.sum(areaDome)  # [mm**2]
    area *= 1e-6  # [m**2]
    return frpMass, volume, area, composite, iterations, *(np.array(anglesShifts).T)


def createWindingDesign(**kwargs):
    startTime = datetime.datetime.now()
    # #########################################################################################
    # SET Parameters of vessel
    # #########################################################################################

    log.info('='*100)
    log.info('createWindingDesign with these parameters: \n'+(indent(kwargs.items())))
    log.info('='*100)

    kwargs['runDir'] = kwargs['runDir'] if 'runDir' in kwargs else getRunDir()
    designArgs = defaultDesign.copy()
    designArgs.update(kwargs)

    # General
    tankname = designArgs['tankname']
    nodeNumber = designArgs['nodeNumber']  # might not exactly be matched due to approximations
    dataDir = designArgs['dataDir']
    runDir = designArgs['runDir']
    verbose = designArgs['verbose']

    # Optimization
    layersToWind = designArgs['maxlayers']

    # Geometry
    domeType = designArgs['domeType'] # CIRCLE; ISOTENSOID
    domeX, domeR = designArgs['domeContour'] # (x,r)
    minPolarOpening = designArgs['minPolarOpening']  # mm
    dzyl = designArgs['dzyl']  # mm
    if 'lzyl' not in designArgs:
        designArgs['lzyl'] = designArgs['lzylByR'] * dzyl/2
    lzylinder = designArgs['lzyl']  # mm

    # Design
    safetyFactor = designArgs['safetyFactor']
    pressure = designArgs['pressure']  # pressure in MPa (bar / 10.)
    if 'burstPressure' not in designArgs:
        designArgs['burstPressure'] = safetyFactor * pressure
    burstPressure = designArgs['burstPressure']
    useFibreFailure = designArgs['useFibreFailure']

    # Material
    materialname = designArgs['materialname']

    # Fiber roving parameter
    hoopLayerThickness = designArgs['hoopLayerThickness']
    helixLayerThickenss =designArgs['helixLayerThickenss']
    rovingWidth = designArgs['rovingWidth']
    numberOfRovings = designArgs['numberOfRovings']
    #bandWidth = rovingWidth * numberOfRovings
    tex = designArgs['tex'] # g / km
    rho = designArgs['fibreDensity']  # g / cm^3
    sectionAreaFibre = tex / (1000. * rho)

    saveParametersAndResults(designArgs)

    # input files
    materialFilename = os.path.join(dataDir, materialname+".json")
    # output files
    linerFilename = os.path.join(runDir, tankname + ".liner")
    designFilename = os.path.join(runDir, tankname + ".design")
    vesselFilename = os.path.join(runDir, tankname + ".vessel")
    windingResultFilename = os.path.join(runDir, tankname + ".wresults")

    # #########################################################################################
    # Create Liner
    # #########################################################################################
    dome = getDome(dzyl / 2., minPolarOpening, domeType, domeX, domeR)
    liner = getLiner(dome, lzylinder, linerFilename, tankname, nodeNumber=nodeNumber)
    fitting = liner.getFitting(False)
    fitting.r3 = 40.

    # ###########################################
    # Create material
    # ###########################################
    material = getMaterial(materialFilename)
    puckProperties = material.puckProperties

    angles, thicknesses, = [90.] * 2, [helixLayerThickenss] * 2
    compositeArgs = [thicknesses, hoopLayerThickness, helixLayerThickenss, material,
                     sectionAreaFibre, rovingWidth, numberOfRovings, numberOfRovings, tex, designFilename, tankname]
    composite = getComposite(angles, *compositeArgs)
    # create vessel and set liner and composite
    vessel = pychain.winding.Vessel()
    vessel.setLiner(liner)
    vessel.setComposite(composite)

    # #############################################################################
    # run winding simulation
    # #############################################################################
    vessel.saveToFile(vesselFilename)  # save vessel
    tankoh2.utilities.copyAsJson(vesselFilename, 'vessel')
    results = designLayers(vessel, layersToWind, minPolarOpening,
                           puckProperties, burstPressure, runDir,
                           composite, compositeArgs, verbose, useFibreFailure)

    frpMass, volume, area, composite, iterations, angles, hoopLayerShifts = results
    duration = datetime.datetime.now() - startTime
    results = frpMass, volume, area, liner.linerLength, composite.getNumberOfLayers(), iterations, duration, angles, hoopLayerShifts
    saveParametersAndResults(designArgs, results)
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

    log.info(f'iterations {iterations}, runtime {duration.seconds} seconds')
    log.info('FINISHED')

    return results


def saveParametersAndResults(inputKwArgs, results=None, verbose = False):
    filename = 'all_parameters_and_results.txt'
    runDir = inputKwArgs.get('runDir')
    outputStr = [
        'INPUTS\n\n',
        indent(inputKwArgs.items())
    ]
    if results is not None:
        outputStr += ['\n\nOUTPUTS\n\n',
                      indent(zip(resultNames, resultUnits, results))]
    logFunc = log.info if verbose else log.debug
    logFunc('Parameters' + ('' if results is None else ' and results') + ':' + ''.join(outputStr))

    if results is not None:
        outputStr += ['\n\n' + indent([resultNames, resultUnits, results])]
    with open(os.path.join(runDir, filename), 'w') as f:
        f.write(''.join(outputStr))

if __name__ == '__main__':
    if 1:
        from existingdesigns import hymodDesign
        createWindingDesign(**defaultDesign)
    else:
        rs=[]
        lengths = np.linspace(1000.,6000,11)
            #np.array([1]) * 1000
        for l in lengths:
            r=createWindingDesign(useFibreFailure=False,
                                safetyFactor=1.,
                                burstPressure=.5,
                                domeType = pychain.winding.DOME_TYPES.ISOTENSOID,
                                lzyl=l,
                                dzyl=2400,
                                #minPolarOpening=30.,
                                )
            rs.append(r)
        print(indent(results))
