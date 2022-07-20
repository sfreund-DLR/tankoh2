import json

import shutil

import numpy as np
import pandas as pd

from tankoh2.service.exception import Tankoh2Error


def getAnglesFromVessel(vessel):
    """returns a list with all angles from the vessel"""
    return [np.rad2deg(vessel.getVesselLayer(layerNumber).getVesselLayerElement(0, True).clairaultAngle) for layerNumber in range(vessel.getNumberOfLayers())]


def getLayerThicknesses(vessel, symmetricContour):
    """returns a dataframe with thicknesses of each layer along the whole vessel"""
    thicknesses = []
    columns = ['lay{}_{:04.1f}'.format(i, angle) for i, angle in enumerate(getAnglesFromVessel(vessel))]
    for layerNumber in range(vessel.getNumberOfLayers()):
        vesselLayer = vessel.getVesselLayer(layerNumber)
        mandrelOuter2 = vesselLayer.getOuterMandrel2()
        numberOfElements = mandrelOuter2.numberOfNodes - 1
        layerThicknesses = []
        for elementNumber in range(numberOfElements):
            layerElement = vesselLayer.getVesselLayerElement(elementNumber, False)
            layerThicknesses.append(layerElement.elementThickness)
        thicknesses.append(layerThicknesses)
    thicknesses = pd.DataFrame(thicknesses).T
    thicknesses.columns = columns
    return thicknesses


def getElementThicknesses(vessel):
    """returns a vector with thicknesses of each element along the whole vessel"""
    thicknesses = getLayerThicknesses(vessel).T
    return thicknesses.sum()


def copyAsJson(filename, typename):
    """copy a file creating a .json file

    Files in mycrowind have specific file types although they are json files.
    This method creates an additional json file besides the original file."""
    if filename.endswith(f'.{typename}'):
        # also save as json for syntax highlighting
        shutil.copy2(filename, filename + '.json')


def updateName(jsonFilename, name, objsName, attrName='name'):
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
    item[attrName] = name
    with open(jsonFilename, "w") as jsonFile:
        json.dump(data, jsonFile, indent=4)


def changeSimulationOptions(vesselFilename, nLayers, minThicknessValue, hoopLayerCompressionStart):
    """changes simulation options for all layers by modifying .vessel (json) file

    The given json file vesselFilename will be updated in place

    :param vesselFilename: name of vessel file (\*.vessel)
    :param nLayers: number of layers to be wind

    """

    with open(vesselFilename) as jsonFile:
        data = json.load(jsonFile)

    for n in range(1, nLayers+1):
        data["vessel"]["simulationOptions"]["thicknessOptions"][str(n)]["minThicknessValue"] = minThicknessValue
        data["vessel"]["simulationOptions"]["thicknessOptions"][str(n)]["hoopLayerCompressionStart"] = hoopLayerCompressionStart

    with open(vesselFilename, "w") as jsonFile:
        json.dump(data, jsonFile, indent=4)