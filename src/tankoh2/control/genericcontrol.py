"""generic methods for tank controls"""

import numpy as np
import os

from tankoh2 import log
from tankoh2.service.utilities import indent, getRunDir
from tankoh2.service.exception import Tankoh2Error
from tankoh2.design.existingdesigns import defaultDesign, allDesignKeywords, frpKeywords
from tankoh2.geometry.dome import DomeEllipsoid

resultNamesFrp = ['shellMass', 'volume', 'area', 'lcylinder', 'numberOfLayers', 'iterations', 'duration', 'angles', 'hoopLayerShifts']
resultUnitsFrp = ['kg', 'dm^2', 'm^2', 'mm', '', '', 's', '°', 'mm']

resultNamesMetal = ['metalMass', 'volume', 'area', 'lcylinder', 'duration']
resultUnitsMetal = ['kg', 'dm^2', 'm^2', 'mm', 's']

def saveParametersAndResults(inputKwArgs, results=None, verbose = False):
    filename = 'all_parameters_and_results.txt'
    runDir = inputKwArgs.get('runDir')
    np.set_printoptions(linewidth=np.inf) # to put arrays in one line
    outputStr = [
        'INPUTS\n\n',
        indent(inputKwArgs.items())
    ]
    if results is not None:
        if len(results) == len(resultNamesFrp):
            resultNames, resultUnits = resultNamesFrp, resultUnitsFrp
        else:
            resultNames, resultUnits = resultNamesMetal, resultUnitsMetal
        outputStr += ['\n\nOUTPUTS\n\n',
                      indent(zip(resultNames, resultUnits, results))]
    logFunc = log.info if verbose else log.debug
    logFunc('Parameters' + ('' if results is None else ' and results') + ':' + ''.join(outputStr))

    if results is not None:
        outputStr += ['\n\n' + indent([resultNames, resultUnits, results])]
    outputStr = ''.join(outputStr)
    with open(os.path.join(runDir, filename), 'w') as f:
        f.write(outputStr)
    log.info('Inputs, Outputs:\n'+ outputStr)
    np.set_printoptions(linewidth=75)  # reset to default


def parseDesginArgs(inputKwArgs, frpOrMetal ='frp'):
    """Parse keyworded arguments, add missing parameters with defaults and return a new dict.
    :param inputKwArgs: dict with input keyworded arguments
    :param frpOrMetal: flag to switch between FRP winding and metal calculations.
    For metal calculations, all winding parameters are removed.
    :return: dict with updated keyworded arguments
    """

    # check if unknown args are used
    notDefinedArgs = set(inputKwArgs.keys()).difference(allDesignKeywords)
    if notDefinedArgs:
        log.warning(f'These input keywords are unknown: {notDefinedArgs}')

    # update missing args with default design args
    inputKwArgs['runDir'] = inputKwArgs['runDir'] if 'runDir' in inputKwArgs else getRunDir()
    designArgs = defaultDesign.copy()
    designArgs.update(inputKwArgs)

    # remove frp-only arguments
    allowed = ['frp', 'metal']
    if not frpOrMetal in allowed:
        raise Tankoh2Error(f'The parameter windingOrMetal can only be one of {allowed} but got '
                           f'"{frpOrMetal}" instead.')
    if frpOrMetal == 'metal':
        for key in frpKeywords:
            inputKwArgs.pop(key)

    # remove args that are superseded by other args (e.g. due to inclusion of default design args)
    removeIfIncluded = [('lcylByR', 'lcyl'),
                        ('pressure', 'burstPressure'),
                        ('safetyFactor', 'burstPressure'),
                        ('valveReleaseFactor', 'burstPressure'),
                        ('useHydrostaticPressure', 'burstPressure'),
                        ('tankLocation', 'burstPressure'),
                        ]
    for removeIt, included in removeIfIncluded:
        if included in designArgs:
            designArgs.pop(removeIt)

    # for elliptical domes, create the contour since µWind does not support is natively
    if designArgs['domeType'] == 'ellipse':
        if not designArgs['domeAxialHalfAxis']:
            raise Tankoh2Error('domeType == "ellipse" but domeLength is not defined')

        de = DomeEllipsoid(designArgs['dcly'] / 2, designArgs['domeAxialHalfAxis'], designArgs['polarOpeningRadius'])
        designArgs['domeContour'] = de.getContour(designArgs['nodeNumber'] // 2)
    return designArgs

