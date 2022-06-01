"""control a tank optimization"""

import os
from datetime import datetime
import numpy as np

from tankoh2 import log, pychain, programDir
from tankoh2.service.utilities import indent
from tankoh2.service.plot.muwind import plotStressEpsPuck
from tankoh2.design.winding.designopt import designLayers
from tankoh2.design.winding.windingutils import copyAsJson, updateName
from tankoh2.design.winding.contour import getLiner, getDome
from tankoh2.design.winding.material import getMaterial, getComposite
from tankoh2.design.winding.solver import getLinearResults
import tankoh2.design.existingdesigns as parameters
from tankoh2.control.genericcontrol import saveParametersAndResults, parseDesginArgs, getBurstPressure
from tankoh2.masses.massestimation import getInsulationMass, getFairingMass, getLinerMass
from tankoh2.geometry.dome import getDome as getDomeTankoh
from tankoh2.geometry.liner import Liner

def createDesign(**kwargs):
    """Create a winding design

    For a list of possible parameters, please refer to tankoh2.design.existingdesigns.allDesignKeywords
    """
    startTime = datetime.now()
    # #########################################################################################
    # SET Parameters of vessel
    # #########################################################################################

    log.info('='*100)
    log.info('Create frp winding design with these parameters: \n'+(indent(kwargs.items())))
    log.info('='*100)

    designArgs = parseDesginArgs(kwargs)

    # General
    tankname = designArgs['tankname']
    nodeNumber = designArgs['nodeNumber']  # number of nodes of full model.
    runDir = designArgs['runDir']
    verbose = designArgs['verbose']

    # Optimization
    layersToWind = designArgs['maxlayers']
    relRadiusHoopLayerEnd = designArgs['relRadiusHoopLayerEnd']

    # Geometry - generic
    polarOpeningRadius = designArgs['polarOpeningRadius']  # mm
    dcyl = designArgs['dcyl']  # mm
    if 'lcyl' not in designArgs:
        designArgs['lcyl'] = designArgs['lcylByR'] * dcyl/2
    lcylinder = designArgs['lcyl']  # mm

    # Geometry - domes
    dome = getDome(dcyl / 2., polarOpeningRadius, designArgs['domeType'].lower(), *designArgs['domeContour'])
    dome2 = None if designArgs['dome2Type'] is None else getDome(dcyl / 2., polarOpeningRadius,
                                                                 designArgs['dome2Type'].lower(),
                                                                 *designArgs['dome2Contour'])

    length = lcylinder + dome.domeLength + (dome.domeLength if dome2 is None else dome2.domeLength)

    # Design Args
    pressure = None
    safetyFactor = None

    if 'burstPressure' not in designArgs:
        designArgs['burstPressure'] = getBurstPressure(designArgs, length)
    burstPressure = designArgs['burstPressure']

    failureMode = designArgs['failureMode']
    useFibreFailure = failureMode.lower() == 'fibrefailure'

    # Material
    materialName = designArgs['materialName']

    # Fiber roving parameter
    hoopLayerThickness = designArgs['hoopLayerThickness']
    helixLayerThickenss = designArgs['helixLayerThickenss']
    rovingWidth = designArgs['rovingWidth']
    numberOfRovings = designArgs['numberOfRovings']
    #bandWidth = rovingWidth * numberOfRovings
    tex = designArgs['tex'] # g / km
    rho = designArgs['fibreDensity']  # g / cm^3
    sectionAreaFibre = tex / (1000. * rho)

    saveParametersAndResults(designArgs)

    # input files
    materialName = materialName if materialName.endswith('.json') else materialName+'.json'
    materialFilename = materialName
    if not os.path.exists(materialName):
        materialFilename = os.path.join(programDir, 'data', materialName)
    # output files
    linerFilename = os.path.join(runDir, tankname + ".liner")
    designFilename = os.path.join(runDir, tankname + ".design")
    vesselFilename = os.path.join(runDir, tankname + ".vessel")
    windingResultFilename = os.path.join(runDir, tankname + ".wresults")

    # #########################################################################################
    # Create Liner
    # #########################################################################################
    liner = getLiner(dome, lcylinder, linerFilename, tankname, dome2, nodeNumber=nodeNumber)
    fitting = liner.getFitting(False)
    fitting.r0 = polarOpeningRadius / 4
    fitting.r1 = polarOpeningRadius
    fitting.rD = 2 * polarOpeningRadius

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

    if 0:
        from tankoh2.design.winding.winding import windLayer, windHoopLayer
        angShifts = np.array([
            (12.72038202799424, 0), (90, 35.94180392812206), (23.124005957067567, 0), (90, 33.46518505785303),
            (14.297902386637837, 0), (14.32189665594325, 0), (13.667957693130539, 0), (90, 37.94368025883611),
            (13.50092137527006, 0), (13.02563160830356, 0), (90, 37.713072256057366), (12.029427674482442, 0),
            (29.059614964583034, 0), (90, 35.72851759988427), (90, 37.11035956801891),
            (60.2965179108075, 0)
        ])
        angles = angShifts[:,0]
        compositeArgs[0] = [helixLayerThickenss]*len(angles)
        vessel.setComposite(getComposite(angles, *compositeArgs))

        if 0:
            for layerNumber, (angle, shift) in enumerate(angShifts):
                if shift:
                    windHoopLayer(vessel, layerNumber, shift)
                else:
                    windLayer(vessel, layerNumber, angle)
        windLayer(vessel, 14, None, verbose)
        vessel.saveToFile(os.path.join(runDir, 'vessel_before_error.vessel.json'))
        windLayer(vessel, 15, 69.2965179108075, verbose)
    # #############################################################################
    # run winding simulation
    # #############################################################################
    vessel.saveToFile(vesselFilename)  # save vessel
    copyAsJson(vesselFilename, 'vessel')
    results = designLayers(vessel, layersToWind, polarOpeningRadius,
                           puckProperties, burstPressure, runDir,
                           composite, compositeArgs, verbose, useFibreFailure, relRadiusHoopLayerEnd)

    frpMass, volume, area, composite, iterations, angles, hoopLayerShifts = results
    duration = datetime.now() - startTime

    domeTankoh = getDomeTankoh(polarOpeningRadius, dcyl / 2, designArgs['domeType'].lower(), dome.domeLength)
    dome2Tankoh = None if dome2 is None else getDomeTankoh(polarOpeningRadius, dcyl / 2, designArgs['dome2Type'].lower(), dome.domeLength)
    linerTankoh = Liner(domeTankoh, lcylinder, dome2Tankoh)
    if burstPressure > 5:
        # compressed gas vessel
        auxMasses = [getLinerMass(linerTankoh), 0., 0.]
    else:
        # liquid, cryo vessel
        auxMasses = [getLinerMass(linerTankoh), getInsulationMass(linerTankoh), getFairingMass(linerTankoh)]
    totalMass = np.sum([frpMass]+auxMasses)
    results = frpMass, *auxMasses, totalMass, volume, area, liner.linerLength, \
        composite.getNumberOfLayers(), iterations, duration, angles, hoopLayerShifts
    saveParametersAndResults(designArgs, results)
    vessel.saveToFile(vesselFilename)  # save vessel
    updateName(vesselFilename, tankname, ['vessel'])
    if pressure:
        updateName(vesselFilename, pressure, ['vessel'], attrName='operationPressure')
    if safetyFactor:
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



if __name__ == '__main__':
    #if 1:
        #params = parameters.defaultUnsymmetricDesign.copy()
        #createDesign(**params)
    if 1:
        #params = parameters.ttDesignLh2
        params = parameters.conicalTankDesign
        createDesign(**params.copy())
    elif 0:
        createDesign(pressure=5)
    elif 1:
        parameters.vphDesign1['polarOpeningRadius'] = 23
        createDesign(**parameters.vphDesign1)
    else:
        rs=[]
        lengths = np.linspace(1000.,6000,11)
            #np.array([1]) * 1000
        for l in lengths:
            r=createWindingDesign(useFibreFailure=False,
                                safetyFactor=1.,
                                burstPressure=.5,
                                domeType = pychain.winding.DOME_TYPES.ISOTENSOID,
                                lcyl=l,
                                dcyl=2400,
                                #polarOpeningRadius=30.,
                                )
            rs.append(r)
        print(indent(results))
