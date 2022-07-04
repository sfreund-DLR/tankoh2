"""generic methods for tank controls"""

import numpy as np
import os
import logging

from tankoh2 import log
from tankoh2.service.utilities import createRstTable, getRunDir, indent
from tankoh2.service.exception import Tankoh2Error
from tankoh2.design.existingdesigns import defaultDesign, allArgs, windingOnlyKeywords, metalOnlyKeywords
from tankoh2.geometry.dome import DomeEllipsoid, DomeTorispherical, DomeConicalElliptical, DomeConicalTorispherical, getDome
from tankoh2.design.loads import getHydrostaticPressure
from tankoh2.settings import useRstOutput

resultNamesFrp = ['Output Name', 'shellMass', 'liner mass', 'insultaion mass', 'fairing mass', 'total mass', 'volume',
                  'area', 'length axial', 'numberOfLayers', 'iterations', 'duration', 'angles',
                  'hoopLayerShifts']
resultUnitsFrp = ['unit', 'kg', 'kg', 'kg', 'kg', 'kg', 'dm^3', 'm^2', 'mm', '', '', 's', '°', 'mm']

resultNamesMetal = ['Output Name', 'metalMass', 'insultaion mass', 'fairing mass', 'total mass',  'volume', 'area',
                    'length axial', 'wallThickness', 'duration']
resultUnitsMetal = ['unit', 'kg', 'kg', 'kg', 'kg', 'dm^3', 'm^2', 'mm', 'mm', 's']

indentFunc = createRstTable if useRstOutput else indent


def saveParametersAndResults(inputKwArgs, results=None):
    filename = 'all_parameters_and_results.txt'
    runDir = inputKwArgs.get('runDir')
    np.set_printoptions(linewidth=np.inf) # to put arrays in one line
    outputStr = [
        'INPUTS\n\n',
        indentFunc(inputKwArgs.items())
    ]
    if results is not None:
        if len(results) == len(resultNamesFrp) - 1:
            resultNames, resultUnits = resultNamesFrp, resultUnitsFrp
        else:
            resultNames, resultUnits = resultNamesMetal, resultUnitsMetal
        outputStr += ['\n\nOUTPUTS\n\n',
                      indentFunc(zip(resultNames, resultUnits, ['value']+list(results)))]
    log.info('Parameters' + ('' if results is None else ' and results') + ':' + ''.join(outputStr))

    if results is not None:
        outputStr += ['\n\n' + indentFunc([resultNames, resultUnits, ['value']+list(results)])]
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
    inputKwArgs['runDir'] = inputKwArgs['runDir'] if 'runDir' in inputKwArgs else getRunDir(inputKwArgs.get('tankname', ''))
    designArgs = defaultDesign.copy()

    removeIfIncluded = np.array([('lcylByR', 'lcyl'),
                        ('pressure', 'burstPressure'),
                        ('safetyFactor', 'burstPressure'),
                        ('valveReleaseFactor', 'burstPressure'),
                        ('useHydrostaticPressure', 'burstPressure'),
                        ('tankLocation', 'burstPressure'),
                        ])
    # cleanup default args so they don't interfere with dependent args from inputKwArgs
    for arg, supersedeArg in removeIfIncluded:
        if arg in inputKwArgs and supersedeArg not in inputKwArgs and supersedeArg in designArgs:
                designArgs.pop(supersedeArg)
    designArgs.update(inputKwArgs)

    # remove args that are superseded by other args (e.g. due to inclusion of default design args)
    for removeIt, included in removeIfIncluded:
        if included in designArgs:
            designArgs.pop(removeIt)

    if designArgs['domeType'] != 'ellipse':
        designArgs.pop('domeLengthByR')

    # remove frp-only arguments
    if frpOrMetal == 'metal':
        removeKeys = windingOnlyKeywords
    elif frpOrMetal == 'frp':
        removeKeys = metalOnlyKeywords
    else:
        raise Tankoh2Error(f'The parameter windingOrMetal can only be one of {["frp", "metal"]} but got '
                           f'"{frpOrMetal}" instead.')

    for key in removeKeys:
        designArgs.pop(key, None)

    volume = []

    for domeName in ['dome2', 'dome']:

        if f'{domeName}Type' not in designArgs or designArgs[f'{domeName}Type'] is None:
            # dome not given (especially for dome2)
            designArgs[f'{domeName}'] = None
            continue

        domeType = designArgs[f'{domeName}Type']
        r = designArgs['dcyl'] / 2
        if designArgs[f'{domeName}Type'] == 'ellipse':
            if not designArgs[f'{domeName}LengthByR']:
                raise Tankoh2Error(f'{domeName}Type == "ellipse" but "{domeName}LengthByR" is not defined')

        if designArgs[f'{domeName}Type'] == 'conicalElliptical':
            params = ['alpha', 'beta', 'gamma', 'delta1']
            for param in params:
                if not designArgs[param]:
                    raise Tankoh2Error(f'domeType == "conicalElliptical" but "{param}" is not defined')

        dome = getDome(r, designArgs['polarOpeningRadius'], domeType, designArgs.get(f'{domeName}LengthByR', 0.) * r,
                        designArgs['delta1'], r - designArgs['alpha'] * r, designArgs['beta'] * designArgs['gamma'] * designArgs['dcyl'],
                        designArgs['beta'] * designArgs['dcyl'] - designArgs['beta'] * designArgs['gamma'] * designArgs['dcyl'])

        volume.append(dome.volume)

        designArgs[f'{domeName}Contour'] = dome.getContour(designArgs['nodeNumber'] // 2)
        designArgs[f'{domeName}'] = dome

    designArgs['lcyl'] = (designArgs['volume'] * 1e9 - volume[0] - volume[-1]) / (np.pi * (designArgs['dcyl'] / 2) ** 2)

    if designArgs['lcyl'] < 20:

        designArgs['lcyl'] = 20
        log.warning('dCyl was adapted in order to fit volume requirement')

        while(designArgs['volume'] * 1e9 - volume[0] - volume[-1] - np.pi * designArgs['dcyl'] / 2 * designArgs['lcyl']) > 0.01 * designArgs['volume']:

            adaptGeometry = dome.adaptGeometry(5, designArgs['beta'])
            volume[-1] = adaptGeometry[0]
            designArgs['dcyl'] = adaptGeometry[-1]

        dome = getDome(r, designArgs['polarOpeningRadius'], domeType, designArgs.get(f'{domeName}LengthByR', 0.) * r,
                       designArgs['delta1'], r - designArgs['alpha'] * r,
                       designArgs['beta'] * designArgs['gamma'] * designArgs['dcyl'],
                       designArgs['beta'] * designArgs['dcyl'] - designArgs['beta'] * designArgs['gamma'] * designArgs['dcyl'])

    if 'lcyl' not in designArgs:
        designArgs['lcyl'] = designArgs['lcylByR'] * designArgs['dcyl']/2

    dome, dome2 = designArgs['dome'], designArgs['dome2']

    dome2 = designArgs['dome2'] if 'dome2' in designArgs is None else designArgs['dome']

    designArgs['tankLength'] = designArgs['lcyl'] + dome.domeLength + \
                               (dome.domeLength if dome2 is None else dome2.domeLength)

    if 'verbose' in designArgs and designArgs['verbose']:
        log.setLevel(logging.DEBUG)
        for handler in log.handlers:
            handler.setLevel(logging.DEBUG)
    designArgs.pop('help',None)
    return designArgs


def getBurstPressure(designArgs, length):
    """Calculate burst pressure

    The limit and ultimate pressure is calculated as

    .. math::

        p_{limit} = (p_{des} * f_{valve} + p_{hyd})

    .. math::

        p_{ult} = p_{limit} * f_{ult}

    - :math:`p_{des}` maximum operating pressure [MPa] (pressure in designArgs)
    - :math:`f_{valve}` factor for valve release (valveReleaseFactor in designArgs)
    - :math:`p_{hyd}` hydrostatic pressure according to CS 25.963 (d)
    - :math:`f_{ult}` ultimate load factor (safetyFactor in designArgs)
    """
    dcyl = designArgs['dcyl']
    safetyFactor = designArgs['safetyFactor']
    pressure = designArgs['pressure']  # pressure in MPa (bar / 10.)
    valveReleaseFactor = designArgs['valveReleaseFactor']
    useHydrostaticPressure = designArgs['useHydrostaticPressure']
    tankLocation = designArgs['tankLocation']
    hydrostaticPressure = getHydrostaticPressure(tankLocation, length, dcyl) if useHydrostaticPressure else 0.
    return (pressure + hydrostaticPressure) * safetyFactor * valveReleaseFactor