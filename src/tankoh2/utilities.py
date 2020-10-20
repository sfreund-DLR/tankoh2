"""utility methods"""

import json
import shutil
import pandas as pd
import numpy as np

from tankoh2.exception import Tankoh2Error


def getRadiusByShiftOnMandrel(mandrel, startRadius, shift):
    """Calculates a shift along the mandrel surface in the dome section

    :param mandrel: mandrel obj
    :param startRadius: radius on mandrel where the shift should be applied
    :param shift: (Scalar or Vector) Shift along the surface. Positive values shift in fitting direction
    :return: x-coordinate, radius
    """
    # x-coordinate, radius, length on mandrel
    coords = pd.DataFrame(np.array([  # mandrel.getXArray(),
                                    mandrel.getRArray(),
                                    mandrel.getLArray()]).T,
                          columns=[  # 'x',
                                   'r', 'l'])

    # cut section of above 0.9*maxRadius
    maxR = coords['r'].max()
    coords = coords[coords['r'] < 0.9 * maxR]

    # invert index order
    coordsRev = coords.iloc[::-1]

    # get initial length and perform shift
    startLength = np.interp(startRadius, coordsRev['r'], coordsRev['l'])
    targetLength = startLength + shift

    # get target radius
    targetRadius = np.interp(targetLength, coords['l'], coords['r'])
    return targetRadius


def getLayerThicknesses(vessel):
    """returns a dataframe with thicknesses of each layer along the whole vessel"""
    thicknesses = []
    for layerNumber in range(vessel.getNumberOfLayers()):
        vesselLayer = vessel.getVesselLayer(layerNumber)
        mandrelOuter2 = vesselLayer.getOuterMandrel2()
        numberOfElements = mandrelOuter2.numberOfNodes - 1
        layerThicknesses = []
        for elementNumber in range(numberOfElements):
            layerElement = vesselLayer.getVesselLayerElement(elementNumber, False)
            layerThicknesses.append(layerElement.elementThickness)
        thicknesses.append(layerThicknesses)
    thicknesses = pd.DataFrame(thicknesses)
    # thicknesses.T.plot()
    return thicknesses


def getElementThicknesses(vessel):
    """returns a vector with thicknesses of each element along the whole vessel"""
    thicknesses = getLayerThicknesses(vessel)
    return thicknesses.sum()


def copyAsJson(filename, typename):
    """copy a file creating a .json file

    Files in mycrowind have specific file types although they are json files.
    This method creates an additional json file besides the original file."""
    if filename.endswith(f'.{typename}'):
        # also save as json for syntax highlighting
        shutil.copy2(filename, filename + '.json')


def updateName(jsonFilename, name, objsName):
    """updates the name of an item in a json file.

    The given json file will be updated in place

    :param jsonFilename: name of json file
    :param name: name that should be updated
    :param objsName: name of the object which name tag should be updated
    """
    with open(jsonFilename) as jsonFile:
        data = json.load(jsonFile)
    item = data
    for objName in objsName:
        try:
            item = item[objName]
        except KeyError:
            raise Tankoh2Error(f'Tree of "{objsName}" not included in "{jsonFilename}"')
    item["name"] = name
    with open(jsonFilename, "w") as jsonFile:
        json.dump(data, jsonFile, indent=4)
