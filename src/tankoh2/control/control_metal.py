"""control a tank optimization"""

import datetime

from tankoh2 import log
from tankoh2.service.utilities import indent
from tankoh2.service.exception import Tankoh2Error
from tankoh2.geometry.dome import DomeEllipsoid, DomeSphere
from tankoh2.geometry.liner import Liner
from tankoh2.design.loads import getHydrostaticPressure
from tankoh2.design.metal.mechanics import getWallThickness
from tankoh2.design.metal.material import getMaterial
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
    log.info('Create metal design with these parameters: \n'+(indent(kwargs.items())))
    log.info('='*100)

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
    if domeType == 'circle':
        dome = DomeSphere(dcly/2, polarOpeningRadius)
    elif domeType == 'ellipse':
        lDomeHalfAxis = designArgs['domeAxialHalfAxis']
        dome = DomeEllipsoid(dcly/2, lDomeHalfAxis, polarOpeningRadius)
    else:
        raise Tankoh2Error(f'Dome type "{domeType}" not supported for metal tanks. Please contact the developer.')
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
    mass = material['roh'] * wallVol / 1000 # [kg]

    duration = datetime.datetime.now() - startTime
    results = mass, volume, area, linerLength, wallThickness, duration

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
        params['domeAxialHalfAxis'] = 100
        params['materialName'] = 'alu2219'
        createDesign(**params)
    elif 1:
        import numpy as np
        r = h = 100
        asp = 4*np.pi*r**2
        vs = 4/3*np.pi*r**3
        ac = 2*np.pi*r*h
        vc = np.pi*r**2*h

        params = defaultDesign.copy()
        params['materialName'] = 'alu2219'
        params['domeType'] = 'ellipse'
        params['polarOpeningRadius'] = 0
        params['domeAxialHalfAxis'] = r
        params['dcly'] = 2*r
        params['lcyl'] = h
        params['safetyFactor'] = 2.25
        params['pressure'] = .2
        createDesign(**params)
        print('volumne', vc+vs, 'area', ac+asp)

