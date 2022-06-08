"""generic methods for tank controls"""

import numpy as np
import os
import logging

from tankoh2 import log
from tankoh2.service.utilities import createRstTable, getRunDir, indent
from tankoh2.service.exception import Tankoh2Error
from tankoh2.design.existingdesigns import defaultDesign, allArgs, windingOnlyKeywords, metalOnlyKeywords
from tankoh2.geometry.dome import DomeEllipsoid
from tankoh2.geometry.dome import DomeConical
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


def saveParametersAndResults(inputKwArgs, results=None, verbose = False):
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
    logFunc = log.info if verbose else log.debug
    logFunc('Parameters' + ('' if results is None else ' and results') + ':' + ''.join(outputStr))

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
    for arg in removeIfIncluded[:,1]:
        if arg in designArgs:
            designArgs.pop(arg)
    designArgs.update(inputKwArgs)

    if designArgs['domeType'] != 'ellipse':
        designArgs.pop('domeLengthByR')

    # remove args that are superseded by other args (e.g. due to inclusion of default design args)
    for removeIt, included in removeIfIncluded:
        if included in designArgs:
            designArgs.pop(removeIt)

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



    # for elliptical domes, create the contour since µWind does not support is natively
    for domeName in ['dome', 'dome2']:
        if designArgs[f'{domeName}Type'] == 'ellipse':
            if not designArgs[f'{domeName}LengthByR']:
                raise Tankoh2Error(f'{domeName}Type == "ellipse" but "domeLengthByR" is not defined')

            r = designArgs['dcyl'] / 2
            de = DomeEllipsoid(r, designArgs[f'{domeName}LengthByR'] * r, designArgs['polarOpeningRadius'])
            designArgs[f'{domeName}Contour'] = de.getContour(designArgs['nodeNumber'] // 2)

        if domeName == 'dome2':
            break # no conical structures for second dome

        # for conical domes, create the contour since µWind does not support is natively
        if designArgs[f'{domeName}Type'] == 'conical':
            if not designArgs['alpha']:
                raise Tankoh2Error('domeType == "conical" but "alpha" is not defined')
            if not designArgs['beta']:
                raise Tankoh2Error('domeType == "conical" but "beta" is not defined')
            if not designArgs['gamma']:
                raise Tankoh2Error('domeType == "conical" but "gamma" is not defined')
            if not designArgs['delta1']:
                raise Tankoh2Error('domeType == "conical" but "delta1" is not defined')
            if not designArgs['delta2']:
                raise Tankoh2Error('domeType == "conical" but "delta2" is not defined')
            if not designArgs['volume']:
                raise Tankoh2Error('domeType == "conical" but "volume" is not defined')

            rCyl = designArgs['dcyl'] / 2
            rSmall = rCyl - designArgs['alpha'] * rCyl
            lDome2 = designArgs['delta2'] * rCyl
            lRad = designArgs['beta'] * designArgs['gamma'] * designArgs['dcyl']
            lCone = designArgs['beta'] * designArgs['dcyl'] - lRad

            dc = DomeConical(rCyl, designArgs['polarOpeningRadius'], designArgs['delta1'], rSmall, lCone, lRad, designArgs['xPosApex'], designArgs['yPosApex'], designArgs['volume'], lDome2, 'tank')
            designArgs['lcyl'] = dc.getCylLength()
            designArgs['domeContour'] = dc.getContour(designArgs['nodeNumber'])

    if 'verbose' in designArgs and designArgs['verbose']:
        log.setLevel(logging.DEBUG)
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