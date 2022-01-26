"""control a tank optimization"""

import os
import datetime

from tankoh2 import log, pychain
from tankoh2.design.winding.designopt import designLayers
from tankoh2.service.utilities import indent
from tankoh2.service.plot.muwind import plotStressEpsPuck
from tankoh2.design.loads import getHydrostaticPressure
from tankoh2.design.winding.windingutils import copyAsJson, updateName
from tankoh2.design.winding.contour import getLiner, getDome
from tankoh2.design.winding.material import getMaterial, getComposite
from tankoh2.design.winding.solver import getLinearResults
from tankoh2.design.existingdesigns import defaultDesign
from tankoh2.control.genericcontrol import saveParametersAndResults, parseDesginArgs



def createDesign(**kwargs):
    """Create a winding design

    For a list of possible parameters, please refer to tankoh2.design.existingdesigns.allDesignKeywords
    """
    startTime = datetime.datetime.now()
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
    dataDir = designArgs['dataDir']
    runDir = designArgs['runDir']
    verbose = designArgs['verbose']

    # Optimization
    layersToWind = designArgs['maxlayers']
    relRadiusHoopLayerEnd = designArgs['relRadiusHoopLayerEnd']

    # Geometry
    domeType = designArgs['domeType'].lower() # CIRCLE; ISOTENSOID
    domeX, domeR = designArgs['domeContour'] # (x,r)
    polarOpeningRadius = designArgs['polarOpeningRadius']  # mm
    dcly = designArgs['dcly']  # mm
    if 'lcyl' not in designArgs:
        designArgs['lcyl'] = designArgs['lcylByR'] * dcly/2
    lcylinder = designArgs['lcyl']  # mm
    dome = getDome(dcly / 2., polarOpeningRadius, domeType, domeX, domeR)
    length = lcylinder + 2 * dome.domeLength

    # Design Args
    if 'burstPressure' not in designArgs:
        safetyFactor = designArgs['safetyFactor']
        pressure = designArgs['pressure']  # pressure in MPa (bar / 10.)
        valveReleaseFactor = designArgs['valveReleaseFactor']
        useHydrostaticPressure = designArgs['useHydrostaticPressure']
        tankLocation = designArgs['tankLocation']
        hydrostaticPressure = getHydrostaticPressure(tankLocation, length, dcly) if useHydrostaticPressure else 0.
        designArgs['burstPressure'] = (pressure + hydrostaticPressure) * safetyFactor * valveReleaseFactor
    burstPressure = designArgs['burstPressure']
    useFibreFailure = designArgs['useFibreFailure']

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
    materialFilename = os.path.join(dataDir, materialName+".json")
    # output files
    linerFilename = os.path.join(runDir, tankname + ".liner")
    designFilename = os.path.join(runDir, tankname + ".design")
    vesselFilename = os.path.join(runDir, tankname + ".vessel")
    windingResultFilename = os.path.join(runDir, tankname + ".wresults")

    # #########################################################################################
    # Create Liner
    # #########################################################################################
    liner = getLiner(dome, lcylinder, linerFilename, tankname, nodeNumber=nodeNumber)
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
    copyAsJson(vesselFilename, 'vessel')
    results = designLayers(vessel, layersToWind, polarOpeningRadius,
                           puckProperties, burstPressure, runDir,
                           composite, compositeArgs, verbose, useFibreFailure, relRadiusHoopLayerEnd)

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



if __name__ == '__main__':
    if 0:
        params = defaultDesign.copy()
        params['domeType'] = 'ellipse'
        params['domeAxialHalfAxis'] = 300
        params['relRadiusHoopLayerEnd'] = 0.95
        createDesign(**params)
    elif 0:
        createWindingDesign(pressure=5)
    elif 1:
        from tankoh2.design.existingdesigns import vphDesign1
        vphDesign1['polarOpeningRadius'] = 23
        createDesign(**vphDesign1)
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
                                dcly=2400,
                                #polarOpeningRadius=30.,
                                )
            rs.append(r)
        print(indent(results))
