"""control a tank optimization"""

import datetime
import numpy as np

from tankoh2 import log
from tankoh2.geometry.dome import getDome, DomeGeneric
from tankoh2.geometry.liner import Liner
from tankoh2.design.metal.mechanics import getMaxWallThickness
from tankoh2.design.metal.material import getMaterial
from tankoh2.design.existingdesigns import defaultDesign
from tankoh2.control.genericcontrol import saveParametersAndResults, parseDesginArgs, getBurstPressure
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

    # Geometry
    domeType = designArgs['domeType'].lower()
    domeX, domeR = designArgs['domeContour']
    polarOpeningRadius = designArgs['polarOpeningRadius']  # mm
    dcyl = designArgs['dcyl']  # mm
    if 'lcyl' not in designArgs:
        designArgs['lcyl'] = designArgs['lcylByR'] * dcyl/2
    lcylinder = designArgs['lcyl']  # mm
    if domeX is not None and domeR is not None:
        dome = DomeGeneric(domeX, domeR)
    else:
        dome = getDome(dcyl/2, polarOpeningRadius, domeType, designArgs.get('domeLengthByR', 0.) * dcyl / 2)
    dome2 = None if designArgs['dome2Type'] is None else getDome(polarOpeningRadius, dcyl / 2,
                                                                designArgs['dome2Type'].lower(),
                                                                dome.domeLength)
    length = lcylinder + dome.domeLength + (dome.domeLength if dome2 is None else dome2.domeLength)

    # Pressure Args
    if 'burstPressure' not in designArgs:
        designArgs['burstPressure'] = getBurstPressure(designArgs, length)
    burstPressure = designArgs['burstPressure']
    designPressure = designArgs['pressure']

    materialName = designArgs['materialName']
    material = getMaterial(materialName)
    # #########################################################################################
    # Create Liner
    # #########################################################################################
    liner = Liner(dome, lcylinder, dome2)


    # #############################################################################
    # run calculate wall thickness
    # #############################################################################
    volume, area, linerLength = liner.volume / 1000 /1000, liner.area/100/100/100, liner.length
    wallThickness = getMaxWallThickness(designPressure, burstPressure, material, dcyl)
    #wallThickness = getWallThickness(material, burstPressure, dcyl / 1000) * 1000  # [mm]
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
        params['dcyl'] = 2*r
        params['lcyl'] = h
        params['safetyFactor'] = 2.25
        params['pressure'] = .2
        createDesign(**params)
        print('volumne', vc+vs, 'area', ac+asp)

