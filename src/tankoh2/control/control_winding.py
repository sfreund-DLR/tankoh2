"""control a tank optimization"""

import os
import pandas as pd
from datetime import datetime
import numpy as np

from tankoh2 import log, pychain, programDir
from tankoh2.design.designutils import getMassByVolume
from tankoh2.service.utilities import indent
from tankoh2.design.winding.designopt import designLayers
from tankoh2.design.winding.windingutils import copyAsJson, updateName, getLayerNodalCoordinates, getMandrelNodalCoordinates
from tankoh2.design.winding.contour import getLiner, getDome
from tankoh2.design.winding.material import getMaterial, getComposite, checkFibreVolumeContent
import tankoh2.design.existingdesigns as parameters
from tankoh2.control.genericcontrol import saveParametersAndResults, parseDesignArgs, getBurstPressure, \
    saveLayerBook, _parameterNotSet
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
    designArgs = parseDesignArgs(kwargs)
    saveParametersAndResults(designArgs['runDir'], kwargs, designArgs)

    # General
    tankname = designArgs['tankname']
    nodeNumber = designArgs['nodeNumber']  # number of nodes of full model.
    runDir = designArgs['runDir']
    verbosePlot = designArgs['verbosePlot']
    initialAnglesAndShifts = designArgs.get('initialAnglesAndShifts', None)

    # Optimization
    layersToWind = designArgs['maxLayers']
    relRadiusHoopLayerEnd = designArgs['relRadiusHoopLayerEnd']
    targetFuncWeights = designArgs['targetFuncWeights']

    # Geometry - generic
    polarOpeningRadius = designArgs['polarOpeningRadius']  # mm
    dcyl = designArgs['dcyl']  # mm
    lcylinder = designArgs['lcyl']  # mm

    # Design Args
    pressure = None
    safetyFactor = None

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
                            rovingWidthHoop, rovingWidthHelical)

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
    mandrel = liner.getMandrel1()
    df = pd.DataFrame(np.array([mandrel.getXArray(),mandrel.getRArray(),mandrel.getLArray()]).T,
                      columns=['x','r','l'])
    df.to_csv(os.path.join(runDir, 'nodalResults.csv'), sep=';')

    vessel.setComposite(composite)

    # #############################################################################
    # run winding simulation
    # #############################################################################
    vessel.saveToFile(vesselFilename)  # save vessel
    copyAsJson(vesselFilename, 'vessel')
    results = designLayers(vessel, layersToWind, polarOpeningRadius, bandWidth, puckProperties, burstPressure,
                           dome2 is None, runDir, compositeArgs, verbosePlot,
                           useFibreFailure, relRadiusHoopLayerEnd, initialAnglesAndShifts, targetFuncWeights)

    frpMass, area, iterations, reserveFac, stressRatio, cylinderThickness, maxThickness, angles, hoopLayerShifts = results
    angles = np.around(angles, decimals=3)
    hoopByHelicalFrac = len([a for a in angles if a>89]) / len([a for a in angles if a<89])
    hoopLayerShifts = np.around(hoopLayerShifts, decimals=3)
    duration = datetime.now() - startTime

    # #############################################################################
    # postprocessing
    # #############################################################################

    domeTankoh = designArgs['dome']
    dome2Tankoh = designArgs['dome2']
    linerTankoh = Liner(domeTankoh, lcylinder, dome2Tankoh)
    linerThk, insThk, fairThk = designArgs['linerThickness'], designArgs['insulationThickness'], designArgs['fairingThickness'],
    if designArgs['temperature'] < 33:
        # liquid, cryo vessel
        auxMasses = [getLinerMass(linerTankoh, linerThickness=linerThk), getInsulationMass(linerTankoh, insulationThickness=insThk),
                     getFairingMass(linerTankoh, fairingThickness=fairThk)]
    else:
        # compressed gas vessel
        auxMasses = [getLinerMass(linerTankoh, linerThickness=linerThk), 0., 0.]
    totalMass = np.sum([frpMass]+auxMasses)
    linerInnerTankoh = linerTankoh.getLinerResizedByThickness(-1*linerThk)
    volume = linerInnerTankoh.volume / 1e6 # Volume considering liner
    if not _parameterNotSet(designArgs,'h2Mass'):
        h2Mass = designArgs['h2Mass']
        gravimetricIndex = h2Mass / (totalMass + h2Mass)
    elif not _parameterNotSet(designArgs, 'pressure'):
        h2Mass = getMassByVolume(volume/1e3, designArgs['pressure'], designArgs['maxFill'],
                                 temperature=designArgs['temperature'])
        gravimetricIndex = h2Mass / (totalMass + h2Mass)
    else:
        gravimetricIndex = 'Pressure not defined, cannot calculate mass from volume'
    results = [
        frpMass, *auxMasses, totalMass, volume, area, liner.linerLength, vessel.getNumberOfLayers(),
        cylinderThickness, maxThickness, reserveFac, gravimetricIndex, stressRatio, hoopByHelicalFrac,
        iterations, duration, angles, hoopLayerShifts]

    saveParametersAndResults(designArgs['runDir'], results=results)

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

    # write nodal layer results dataframe to csv
    mandrelCoordinatesDataframe = getMandrelNodalCoordinates(liner, dome2 is None)
    layerCoordinatesDataframe = getLayerNodalCoordinates(windingResults, dome2 is None)
    nodalResultsDataframe = pd.concat([mandrelCoordinatesDataframe, layerCoordinatesDataframe], join='outer', axis=1)
    nodalResultsDataframe.to_csv(os.path.join(runDir, 'nodalResults.csv'), sep=';',)

    saveLayerBook(runDir, tankname)

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

        params.update([
            ('tankname', params['tankname'] + '_hoopShiftOpt_maxCritBend'),
            ('verbosePlot', True),
            #('maxLayers', 20),
            ('targetFuncWeights', [1., 0., 0., 0., .25, 0.2])
        ])

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
