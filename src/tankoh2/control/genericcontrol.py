"""generic methods for tank controls"""

import numpy as np
import os

from tankoh2 import log
from tankoh2.service.utilities import indent, getRunDir
from tankoh2.service.exception import Tankoh2Error
from tankoh2.design.existingdesigns import defaultDesign

resultNames = ['shellMass', 'volume', 'area', 'lzylinder', 'numberOfLayers', 'iterations', 'duration', 'angles', 'hoopLayerShifts']
resultUnits = ['kg', 'dm^2', 'm^2', 'mm', '', '', 's', '°', 'mm']

def saveParametersAndResults(inputKwArgs, results=None, verbose = False):
    filename = 'all_parameters_and_results.txt'
    runDir = inputKwArgs.get('runDir')
    np.set_printoptions(linewidth=np.inf) # to put arrays in one line
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
    outputStr = ''.join(outputStr)
    with open(os.path.join(runDir, filename), 'w') as f:
        f.write(outputStr)
    log.info('Inputs, Outputs:\n'+ outputStr)
    np.set_printoptions(linewidth=75)  # reset to default


def parseDesginArgs(inputKwArgs, windingOrMetal = 'winding'):
    """Parse keyworded arguments, add missing parameters with defaults and return a new dict.
    :param inputKwArgs: dict with input keyworded arguments
    :param windingOrMetal: flag to switch between FRP winding and metal calculations.
    For metal calculations, all winding parameters are removed.
    :return: dict with updated keyworded arguments
    """
    allowed = ['winding', 'metal']
    if not windingOrMetal in allowed:
        raise Tankoh2Error(f'The parameter windingOrMetal can only be one of {allowed} but got '
                           f'"{windingOrMetal}" instead.')

    inputKwArgs['runDir'] = inputKwArgs['runDir'] if 'runDir' in inputKwArgs else getRunDir()
    designArgs = defaultDesign.copy()
    designArgs.update(inputKwArgs)
    removeIfIncluded = [('lzylByR', 'lzyl'),
                        ('pressure', 'burstPressure'),
                        ('safetyFactor', 'burstPressure'),
                        ('valveReleaseFactor', 'burstPressure'),
                        ('useHydrostaticPressure', 'burstPressure'),
                        ('tankLocation', 'burstPressure'),
                        ]
    for removeIt, included in removeIfIncluded:
        if included in designArgs:
            designArgs.pop(removeIt)
    return designArgs

