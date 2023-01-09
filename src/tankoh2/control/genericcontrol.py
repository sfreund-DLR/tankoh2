"""generic methods for tank controls"""

import numpy as np
import os
import logging

from tankoh2 import log, pychain
from tankoh2.service.utilities import createRstTable, getRunDir, indent
from tankoh2.service.exception import Tankoh2Error
from tankoh2.design.existingdesigns import defaultDesign, allArgs, windingOnlyKeywords, metalOnlyKeywords
from tankoh2.geometry.dome import DomeGeneric, getDome
from tankoh2.design.loads import getHydrostaticPressure
from tankoh2.settings import useRstOutput, minCylindricalLength
from tankoh2.design.designutils import getRequiredVolume

resultNamesFrp = ['Output Name', 'shellMass', 'liner mass', 'insulation mass', 'fairing mass', 'total mass', 'volume',
                  'area', 'length axial', 'numberOfLayers', 'reserve factor', 'gravimetric index',
                  'stress ratio', 'hoop helical ratio', 'iterations', 'duration', 'angles', 'hoopLayerShifts']
resultUnitsFrp = ['unit', 'kg', 'kg', 'kg', 'kg', 'kg', 'dm^3', 'm^2', 'mm', '', '', '', '', '', '', 's', '°', 'mm']

resultNamesMetal = ['Output Name', 'metalMass', 'insulation mass', 'fairing mass', 'total mass', 'volume', 'area',
                    'length axial', 'wallThickness', 'duration']
resultUnitsMetal = ['unit', 'kg', 'kg', 'kg', 'kg', 'dm^3', 'm^2', 'mm', 'mm', 's']

indentFunc = createRstTable if useRstOutput else indent


def saveParametersAndResults(inputKwArgs, results=None, createMessage=False):
    """saves all input parameters and results to a file

    :param inputKwArgs: dict with input keys and values
    :param results: list with result values as returned by createDesign() in control_winding and control_metal
    :param createMessage: flag if a log message should be created
    """
    filename = 'all_parameters_and_results.txt'
    runDir = inputKwArgs.get('runDir')
    np.set_printoptions(linewidth=np.inf)  # to put arrays in one line
    outputStr = [
        '\nINPUTS\n\n',
        indentFunc(inputKwArgs.items())
    ]
    if results is not None:
        if len(results) == len(resultNamesFrp) - 1:
            resultNames, resultUnits = resultNamesFrp, resultUnitsFrp
        else:
            resultNames, resultUnits = resultNamesMetal, resultUnitsMetal
        outputStr += ['\n\nOUTPUTS\n\n',
                      indentFunc(zip(resultNames, resultUnits, ['value'] + list(results)))]
    log.info('Parameters' + ('' if results is None else ' and results') + ':' + ''.join(outputStr))

    if results is not None:
        outputStr += ['\n\n' + indentFunc([resultNames, resultUnits, ['value'] + list(results)])]
    outputStr = ''.join(outputStr)
    with open(os.path.join(runDir, filename), 'w') as f:
        f.write(outputStr)
    if createMessage:
        log.info('Inputs, Outputs:\n' + outputStr)
    np.set_printoptions(linewidth=75)  # reset to default


def _parameterNotSet(inputKwArgs, paramKey):
    """A parameter is not set, if it is not present or None"""
    return paramKey not in inputKwArgs or inputKwArgs[paramKey] is None


def parseDesignArgs(inputKwArgs, frpOrMetal='frp'):
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
                                 ('h2Mass', 'burstPressure'),
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

    if _parameterNotSet(designArgs, 'lcyl'):
        designArgs['lcyl'] = designArgs['lcylByR'] * designArgs['dcyl'] / 2
    # width
    if _parameterNotSet(designArgs, 'rovingWidthHoop'):
        designArgs['rovingWidthHoop'] = designArgs['rovingWidth']
    if _parameterNotSet(designArgs, 'rovingWidthHelical'):
        designArgs['rovingWidthHelical'] = designArgs['rovingWidth']
    # thickness
    if _parameterNotSet(designArgs, 'layerThkHoop'):
        designArgs['layerThkHoop'] = designArgs['layerThk']
    if _parameterNotSet(designArgs, 'layerThkHelical'):
        designArgs['layerThkHelical'] = designArgs['layerThk']

    linerThk = designArgs['linerThickness']
    domeVolumes = []
    for domeName in ['dome2', 'dome']:

        if f'{domeName}Type' not in designArgs or designArgs[f'{domeName}Type'] is None:
            # dome not given (especially for dome2)
            designArgs[f'{domeName}'] = None
            continue

        domeType = designArgs[f'{domeName}Type']
        r = designArgs['dcyl'] / 2
        if f'{domeName}Contour' in designArgs \
                and designArgs[f'{domeName}Contour'][0] is not None \
                and designArgs[f'{domeName}Contour'][1] is not None:
            # contour given via coordinates
            dome = DomeGeneric(*designArgs[f'{domeName}Contour'])
        else:
            # contour given by dome type and parameters
            if designArgs[f'{domeName}Type'] == 'ellipse':
                if not designArgs[f'{domeName}LengthByR']:
                    raise Tankoh2Error(f'{domeName}Type == "ellipse" but "{domeName}LengthByR" is not defined')
            elif designArgs[f'{domeName}Type'] == 'conicalElliptical':
                params = ['alpha', 'beta', 'gamma', 'delta1']
                for param in params:
                    if not designArgs[param]:
                        raise Tankoh2Error(f'domeType == "conicalElliptical" but "{param}" is not defined')

            dome = getDome(r, designArgs['polarOpeningRadius'], domeType,
                           designArgs.get(f'{domeName}LengthByR', 0.) * r,
                           designArgs['delta1'], r - designArgs['alpha'] * r,
                           designArgs['beta'] * designArgs['gamma'] * designArgs['dcyl'],
                           designArgs['beta'] * designArgs['dcyl'] - designArgs['beta'] * designArgs['gamma'] *
                           designArgs['dcyl'])

        domeVolumes.append(dome.getDomeResizedByThickness(-linerThk).volume)

        designArgs[f'{domeName}Contour'] = dome.getContour(designArgs['nodeNumber'] // 2)
        designArgs[f'{domeName}'] = dome

    # get h2 Volume from Mass and Pressure
    if not _parameterNotSet(designArgs, 'h2Mass') and not _parameterNotSet(designArgs, 'pressure'):
        designArgs['volume'] = getRequiredVolume(designArgs['h2Mass'], designArgs['pressure'], designArgs['maxFill'],
                                                 temperature=designArgs['temperature'])
    if not _parameterNotSet(designArgs, 'volume'):
        volumeReq = designArgs['volume']
        # use volume in order to scale tank length → resets lcyl
        requiredCylVol = volumeReq * 1e9 - domeVolumes[0] - domeVolumes[-1]
        designArgs['lcyl'] = requiredCylVol / (np.pi * ((designArgs['dcyl'] - 2 * linerThk) / 2) ** 2)

        if designArgs['lcyl'] > minCylindricalLength:
            log.info(f'Due to volume requirement (V={designArgs["volume"]} m^3), the cylindrical length'
                     f' was set to {designArgs["lcyl"]}.')
        else:
            if not hasattr(dome, 'getDomeResizedByRCyl'):
                raise NotImplementedError(f'Adjusting the dome diameter is not supported for the dome of type'
                                          f'{dome.__class__}. Please contact the developer and/or ')
            # if the tank volume given in the designArgs is so low that is already fits into the domes,
            # the tank diameter is scaled down to achieve a minimum of minCylindricalLength
            # cylindrical length needed to run
            # simulation with muWind. The parameters alpha, beta, gamma and delta are kept constant while the
            # cylindrical diameter is changed

            designArgs['lcyl'] = minCylindricalLength

            for step in [10, 1]:
                while True:
                    domeVolumes = []
                    dome = designArgs['dome'].getDomeResizedByRCyl(-step)
                    domeVolumes.append(dome.getDomeResizedByThickness(-linerThk).volume)
                    if not _parameterNotSet(designArgs, 'dome2'):
                            dome2 = designArgs['dome2'].getDomeResizedByRCyl(-step)
                            domeVolumes.append(dome2.getDomeResizedByThickness(-linerThk).volume)
                    if domeVolumes[0] * 1e-9 + domeVolumes[-1] * 1e-9 + np.pi * (dome.rCyl - linerThk) ** 2 * designArgs['lcyl'] * 1e-9 < volumeReq:
                        break
                    designArgs['dome'] = dome
                    designArgs['domeContour'] = dome.getContour(designArgs['nodeNumber'] // 2)
                    if not _parameterNotSet(designArgs, 'dome2'):
                        designArgs['dome2'] = dome2
                        designArgs['dome2Contour'] = dome2.getContour(designArgs['nodeNumber'] // 2)
                    designArgs['dcyl'] = 2 * dome.rCyl

            log.warning(f'Due to volume requirement (V={designArgs["volume"]} m^3) and high cylindrical diameter, '
                        f'the cylindrical length was reduced to {designArgs["lcyl"]} and '
                        f'the cylindrical diameter was reduced to {designArgs["dcyl"]}.')

    dome, dome2 = designArgs['dome'], designArgs['dome2']
    dome2 = designArgs['dome2'] if 'dome2' in designArgs else None
    designArgs['tankLength'] = designArgs['lcyl'] + dome.domeLength + \
                               (dome.domeLength if dome2 is None else dome2.domeLength)

    # Define burstPressure if only pressure is given
    if 'burstPressure' not in designArgs:
        designArgs['burstPressure'] = getBurstPressure(designArgs, designArgs['tankLength'])

    if 'verbose' in designArgs and designArgs['verbose']:
        log.setLevel(logging.DEBUG)
        for handler in log.handlers:
            handler.setLevel(logging.DEBUG)
    designArgs.pop('help', None)
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


def saveLayerBook(runDir, vesselName):
    """Writes a text file with layer information for manufacturing"""
    vessel = pychain.winding.Vessel()
    filename = runDir + "//" + vesselName + ".vessel"
    log.info(f' load vessel from {filename}')
    vessel.loadFromFile(filename)
    vessel.finishWinding()

    # get composite design of vessel
    composite = pychain.material.Composite()
    filename = runDir + "//" + vesselName + ".design"
    composite.loadFromFile(filename)

    linerOuterDiameter = 2. * vessel.getLiner().cylinderRadius

    outputFileName = runDir + "//" + vesselName + "LayupBook.txt"

    outArr = []
    vesselDiameter = linerOuterDiameter
    for layerNo in range(vessel.getNumberOfLayers()):
        woundedPlyThickness = composite.getLayerThicknessFromWindingProps(layerNo) #composite.getOrthotropLayer(layerNo).thickness
        vesselDiameter = vesselDiameter + 2.*woundedPlyThickness
        outArr.append([layerNo+1, composite.getAngle(layerNo), vessel.getHoopLayerShift(layerNo, True), vessel.getHoopLayerShift(layerNo, True), woundedPlyThickness/2.,woundedPlyThickness,vessel.getPolarOpeningR(layerNo, True), vesselDiameter])

    layerBookMsg = indent([["No. Layer", "Angle in cylinder", "HoopLayerShift left", "HoopLayerShift right",
                            "single ply thickness", "wounded layer thickness", "Polar Opening Radius",
                            "vessel cylinder thickness"]] + outArr)
    log.debug(layerBookMsg)

    with open(outputFileName, "w") as file:
        file.write(layerBookMsg)
