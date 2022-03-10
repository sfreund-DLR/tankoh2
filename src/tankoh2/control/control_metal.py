"""control a tank optimization"""

import datetime
import numpy as np

from tankoh2 import log
from tankoh2.geometry.dome import getDome
from tankoh2.geometry.liner import Liner
from tankoh2.design.loads import getHydrostaticPressure
from tankoh2.design.metal.mechanics import getWallThickness
from tankoh2.design.metal.material import getMaterial
from tankoh2.design.existingdesigns import defaultDesign
from tankoh2.control.genericcontrol import saveParametersAndResults, parseDesginArgs
from tankoh2.masses.massestimation import getInsulationMass, getFairingMass


def createDesign(**kwargs):
    """Create a winding design

    For a list of possible parameters, please refer to tankoh2.design.existingdesigns.allDesignKeywords
    """
    startTime = datetime.datetime.now()
    # #########################################################################################
    # SET Parameters of vessel
    # #########################################################################################

    designArgs = parseDesginArgs(kwargs, 'metal')

    # General
    tankname = designArgs['tankname']
    nodeNumber = designArgs['nodeNumber']  # number of nodes of full model.
    runDir = designArgs['runDir']
    verbose = designArgs['verbose']

    # Geometry
    domeType = designArgs['domeType'].lower()
    domeX, domeR = designArgs['domeContour']
    polarOpeningRadius = designArgs['polarOpeningRadius']  # mm
    dcly = designArgs['dcly']  # mm
    if 'lcyl' not in designArgs:
        designArgs['lcyl'] = designArgs['lcylByR'] * dcly/2
    lcylinder = designArgs['lcyl']  # mm
    dome = getDome(dcly/2, polarOpeningRadius, domeType, designArgs.get('domeLengthByR', 0.) * dcly / 2)
    length = lcylinder + 2 * dome.domeLength

    # Pressure Args
    if 'burstPressure' not in designArgs:
        safetyFactor = designArgs['safetyFactor']
        pressure = designArgs['pressure']  # pressure in MPa (bar / 10.)
        valveReleaseFactor = designArgs['valveReleaseFactor']
        useHydrostaticPressure = designArgs['useHydrostaticPressure']
        tankLocation = designArgs['tankLocation']
        hydrostaticPressure = getHydrostaticPressure(tankLocation, length, dcly) if useHydrostaticPressure else 0.
        designArgs['burstPressure'] = (pressure + hydrostaticPressure) * safetyFactor * valveReleaseFactor
    burstPressure = designArgs['burstPressure']

    materialName = designArgs['materialName']
    material = getMaterial(materialName)
    # #########################################################################################
    # Create Liner
    # #########################################################################################
    liner = Liner(dome, lcylinder)


    # #############################################################################
    # run calculate wall thickness
    # #############################################################################
    volume, area, linerLength = liner.volume / 1000 /1000, liner.area/100/100/100, liner.length
    wallThickness = getWallThickness(material, burstPressure, dcly / 1000) * 1000  # [mm]
    wallVol = liner.getWallVolume(wallThickness) / 1000 / 1000  # [dm*3]
    massMetal = material['roh'] * wallVol / 1000  # [kg]

    duration = datetime.datetime.now() - startTime
    if burstPressure > 5:
        # compressed gas vessel
        auxMasses = [0., 0.]
    else:
        # liquid, cryo vessel
        auxMasses = [getInsulationMass(liner), getFairingMass(liner)]
    totalMass = np.sum([massMetal]+auxMasses)
    results = massMetal, *auxMasses, totalMass, volume, area, linerLength, wallThickness, duration

    saveParametersAndResults(designArgs, results)

    log.info('FINISHED')

    return results



if __name__ == '__main__':
    if 1:
        params = defaultDesign.copy()
        params['domeType'] = 'circle'
        params['materialName'] = 'alu2219'
        createDesign(**params)
    elif 1:
        params = defaultDesign.copy()
        params['domeType'] = 'ellipse'
        params['domeLengthByR'] = 0.5
        params['materialName'] = 'alu2219'
        createDesign(**params)
    elif 1:
        r = h = 100
        asp = 4*np.pi*r**2
        vs = 4/3*np.pi*r**3
        ac = 2*np.pi*r*h
        vc = np.pi*r**2*h

        params = defaultDesign.copy()
        params['materialName'] = 'alu2219'
        params['domeType'] = 'ellipse'
        params['polarOpeningRadius'] = 0
        params['domeLengthByR'] = 1
        params['dcly'] = 2*r
        params['lcyl'] = h
        params['safetyFactor'] = 2.25
        params['pressure'] = .2
        createDesign(**params)
        print('volumne', vc+vs, 'area', ac+asp)

