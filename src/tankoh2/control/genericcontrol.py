"""generic methods for tank controls"""

import numpy as np
import os
import logging

from tankoh2 import log
from tankoh2.service.utilities import createRstTable, getRunDir, indent
from tankoh2.service.exception import Tankoh2Error
from tankoh2.design.existingdesigns import defaultDesign, allArgs, frpKeywords
from tankoh2.geometry.dome import DomeEllipsoid
from tankoh2.geometry.liner import Liner
from tankoh2.settings import useRstOutput

resultNamesFrp = ['shellMass', 'liner mass', 'insultaion mass', 'fairing mass', 'total mass', 'volume',
                  'area', 'lcylinder', 'numberOfLayers', 'iterations', 'duration', 'angles',
                  'hoopLayerShifts']
resultUnitsFrp = ['kg', 'kg', 'kg', 'kg', 'kg', 'dm^3', 'm^2', 'mm', '', '', 's', '°', 'mm']

resultNamesMetal = ['metalMass', 'insultaion mass', 'fairing mass', 'total mass',  'volume', 'area',
                    'lcylinder', 'wallThickness', 'duration']
resultUnitsMetal = ['kg', 'kg', 'kg', 'kg', 'dm^3', 'm^2', 'mm', 'mm', 's']

indentFunc = createRstTable if useRstOutput else indent


def saveParametersAndResults(inputKwArgs, results=None, verbose = False):
    filename = 'all_parameters_and_results.txt'
    runDir = inputKwArgs.get('runDir')
    np.set_printoptions(linewidth=np.inf) # to put arrays in one line
    outputStr = [
        'INPUTS\n\n',
        indentFunc(inputKwArgs.items())
    ]
    if results is not None:
        if len(results) == len(resultNamesFrp):
            resultNames, resultUnits = resultNamesFrp, resultUnitsFrp
        else:
            resultNames, resultUnits = resultNamesMetal, resultUnitsMetal
        outputStr += ['\n\nOUTPUTS\n\n',
                      indentFunc(zip(resultNames, resultUnits, results))]
    logFunc = log.info if verbose else log.debug
    logFunc('Parameters' + ('' if results is None else ' and results') + ':' + ''.join(outputStr))

    if results is not None:
        outputStr += ['\n\n' + indentFunc([resultNames, resultUnits, results])]
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
    notDefinedArgs = set(inputKwArgs.keys()).difference(allArgs['name'])
    if notDefinedArgs:
        log.warning(f'These input keywords are unknown: {notDefinedArgs}')

    # update missing args with default design args
    inputKwArgs['runDir'] = inputKwArgs['runDir'] if 'runDir' in inputKwArgs else getRunDir()
    designArgs = defaultDesign.copy()

    removeIfIncluded = np.array([('lcylByR', 'lcyl'),
                        ('pressure', 'burstPressure'),
                        ('safetyFactor', 'burstPressure'),
                        ('valveReleaseFactor', 'burstPressure'),
                        ('useHydrostaticPressure', 'burstPressure'),
                        ('tankLocation', 'burstPressure'),
                        ])
    # cleanup default args so they don't interfere with dependent args from inputKwArgs
    for arg in removeIfIncluded[:,1]:
        if arg in designArgs:
            designArgs.pop(arg)
    designArgs.update(inputKwArgs)

    # remove args that are superseded by other args (e.g. due to inclusion of default design args)
    for removeIt, included in removeIfIncluded:
        if included in designArgs:
            designArgs.pop(removeIt)

    # remove frp-only arguments
    allowed = ['frp', 'metal']
    if not frpOrMetal in allowed:
        raise Tankoh2Error(f'The parameter windingOrMetal can only be one of {allowed} but got '
                           f'"{frpOrMetal}" instead.')
    if frpOrMetal == 'metal':
        for key in frpKeywords:
            inputKwArgs.pop(key, None)

    # for elliptical domes, create the contour since µWind does not support is natively
    if designArgs['domeType'] == 'ellipse':
        if not designArgs['domeLengthByR']:
            raise Tankoh2Error('domeType == "ellipse" but "domeLengthByR" is not defined')

        r = designArgs['dcly'] / 2
        de = DomeEllipsoid(r, designArgs['domeLengthByR'] * r, designArgs['polarOpeningRadius'])
        designArgs['domeContour'] = de.getContour(designArgs['nodeNumber'] // 2)
    if 'verbose' in designArgs and designArgs['verbose']:
        log.setLevel(logging.DEBUG)
        # todo: pop verbose arg and remove verbose in subsequent functions, using log.debug instead
    designArgs.pop('help',None)
    return designArgs

