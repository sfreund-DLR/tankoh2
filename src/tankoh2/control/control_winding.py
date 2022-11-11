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
from tankoh2.design.winding.material import getMaterial, getComposite, checkFibreVolumeContent
from tankoh2.design.winding.solver import getLinearResults
import tankoh2.design.existingdesigns as parameters
from tankoh2.control.genericcontrol import saveParametersAndResults, parseDesginArgs, getBurstPressure, \
    saveLayerBook
from tankoh2.masses.massestimation import getInsulationMass, getFairingMass, getLinerMass
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
    log.info('Create frp winding design with these non-default parameters: \n'+(indent(kwargs.items())))
    log.info('='*100)

    designArgs = parseDesginArgs(kwargs)

    # General
    tankname = designArgs['tankname']
    nodeNumber = designArgs['nodeNumber']  # number of nodes of full model.
    runDir = designArgs['runDir']
    verbosePlot = designArgs['verbosePlot']
    initialAnglesAndShifts = designArgs.get('initialAnglesAndShifts', None)

    # Optimization
    layersToWind = designArgs['maxlayers']
    relRadiusHoopLayerEnd = designArgs['relRadiusHoopLayerEnd']
    targetFuncWeights = designArgs['targetFuncWeights']

    # Geometry - generic
    polarOpeningRadius = designArgs['polarOpeningRadius']  # mm
    dcyl = designArgs['dcyl']  # mm
    lcylinder = designArgs['lcyl']  # mm
    tankLength = designArgs['tankLength']

    # Design Args
    pressure = None
    safetyFactor = None

    if 'burstPressure' not in designArgs:
        designArgs['burstPressure'] = getBurstPressure(designArgs, tankLength)
    burstPressure = designArgs['burstPressure']

    failureMode = designArgs['failureMode']
    useFibreFailure = failureMode.lower() == 'fibrefailure'

    # Material
    materialName = designArgs['materialName']

    # Fiber roving parameter
    layerThkHoop = designArgs['layerThkHoop']
    layerThkHelical = designArgs['layerThkHelical']
    rovingWidthHoop = designArgs['rovingWidthHoop']
    rovingWidthHelical = designArgs['rovingWidthHelical']
    numberOfRovings = designArgs['numberOfRovings']
    bandWidth = rovingWidthHoop * numberOfRovings
    tex = designArgs['tex'] # g / km
    rho = designArgs['fibreDensity']  # g / cm^3
    sectionAreaFibre = tex / (1000. * rho)
    checkFibreVolumeContent(layerThkHoop, layerThkHelical, sectionAreaFibre,
                            rovingWidthHoop, rovingWidthHelical, tex)

    saveParametersAndResults(designArgs, createMessage=False)

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
    # Geometry - domes
    dome = getDome(dcyl / 2., polarOpeningRadius, designArgs['domeType'], *designArgs['domeContour'])
    dome2 = None if designArgs['dome2Type'] is None else getDome(dcyl / 2., polarOpeningRadius,
                                                                 designArgs['dome2Type'],
                                                                 *designArgs['dome2Contour'])

    liner = getLiner(dome, lcylinder, linerFilename, 'liner_'+tankname, dome2=dome2, nodeNumber=nodeNumber)
    # ###########################################
    # Create material
    # ###########################################
    material = getMaterial(materialFilename)
    puckProperties = material.puckProperties

    compositeArgs = [layerThkHoop, layerThkHelical, material, sectionAreaFibre,
                     rovingWidthHoop, rovingWidthHelical, numberOfRovings, numberOfRovings, tex,
                     designFilename, tankname]
    composite = getComposite([90.], *compositeArgs)
    # create vessel and set liner and composite
    vessel = pychain.winding.Vessel()
    vessel.setLiner(liner)
    vessel.setComposite(composite)

    # #############################################################################
    # run winding simulation
    # #############################################################################
    vessel.saveToFile(vesselFilename)  # save vessel
    copyAsJson(vesselFilename, 'vessel')
    results = designLayers(vessel, layersToWind, polarOpeningRadius, bandWidth, puckProperties, burstPressure,
                           dome2 is None, runDir, compositeArgs, verbosePlot,
                           useFibreFailure, relRadiusHoopLayerEnd, initialAnglesAndShifts, targetFuncWeights)

    frpMass, area, iterations, reserveFac, angles, hoopLayerShifts = results
    angles = np.around(angles, decimals=3)
    hoopLayerShifts = np.around(hoopLayerShifts, decimals=3)
    duration = datetime.now() - startTime

    # #############################################################################
    # postprocessing
    # #############################################################################

    domeTankoh = designArgs['dome']
    dome2Tankoh = designArgs['dome2']
    linerTankoh = Liner(domeTankoh, lcylinder, dome2Tankoh)
    linerThk, insThk, fairThk = designArgs['linerThickness'], designArgs['insulationThickness'], designArgs['fairingThickness'],
    if burstPressure > 5:
        # compressed gas vessel
        auxMasses = [getLinerMass(linerTankoh, linerThk), 0., 0.]
    else:
        # liquid, cryo vessel
        auxMasses = [getLinerMass(linerTankoh, linerThk), getInsulationMass(linerTankoh, insThk),
                     getFairingMass(linerTankoh, fairThk)]
    totalMass = np.sum([frpMass]+auxMasses)
    linerInnerTankoh = linerTankoh.getLinerResizedByThickness(-1*linerThk)
    volume = linerInnerTankoh.volume / 1e6
    results = frpMass, *auxMasses, totalMass, volume, area, liner.linerLength, \
        vessel.getNumberOfLayers(), reserveFac, iterations, duration, angles, hoopLayerShifts
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

    saveLayerBook(runDir, tankname)

    # #############################################################################
    # run Evaluation
    # #############################################################################
    if 0:
        results = getLinearResults(vessel, puckProperties, layersToWind - 1, burstPressure)
        plotStressEpsPuck(True, None, *results)


    log.info(f'iterations {iterations}, runtime {duration.seconds} seconds')
    log.info('FINISHED')

    return results



if __name__ == '__main__':
    if 0:
        #params = parameters.defaultDesign.copy()
        params = parameters.defaultUnsymmetricDesign.copy()
        createDesign(**params)
    elif 1:
        params = parameters.atheat3.copy()
        params['verbosePlot'] = True
        createDesign(**params)
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
