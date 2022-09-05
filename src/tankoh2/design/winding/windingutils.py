"""utility functions for µWind objects"""


import json

import shutil

import numpy as np
import pandas as pd

from tankoh2.service.exception import Tankoh2Error


def getAnglesFromVessel(vessel):
    """returns a list with all angles from the vessel"""
    return [np.rad2deg(vessel.getVesselLayer(layerNumber).getVesselLayerElement(0, True).clairaultAngle) for layerNumber in range(vessel.getNumberOfLayers())]


def getLayerThicknesses(vessel, symmetricContour, layerNumbers=None):
    """returns a dataframe with thicknesses of each layer along the whole vessel
    :param vessel: vessel obj
    :param symmetricContour: flag if symmetric contour is used
    :param layerNumbers: list of layers that should be evaluated. If None, all layers are used
    :return: 
    """
    thicknesses = []
    if layerNumbers is None:
        layerNumbers = range(vessel.getNumberOfLayers())
    angles = getAnglesFromVessel(vessel)
    columns = ['lay{}_{:04.1f}'.format(layNum, angles[layNum]) for layNum in layerNumbers]

    liner = vessel.getLiner()
    numberOfElements1 = liner.getMandrel1().numberOfNodes - 1
    numberOfElements2 = liner.getMandrel2().numberOfNodes - 1
    for layerNumber in layerNumbers:
        vesselLayer = vessel.getVesselLayer(layerNumber)
        layerThicknesses = []
        elemsMandrels =  [(numberOfElements1, True)]
        if not symmetricContour:
            elemsMandrels.append((numberOfElements2, False))
        for numberOfElements, isMandrel1 in elemsMandrels:
            for elementNumber in range(numberOfElements):
                layerElement = vesselLayer.getVesselLayerElement(elementNumber, isMandrel1)
                layerThicknesses.append(layerElement.elementThickness)
            if not symmetricContour and isMandrel1:
                layerThicknesses = layerThicknesses[::-1] # reverse order of mandrel 1
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


def getLinearResultsAsDataFrame(results = None):
    """returns the mechanical results as dataframe

    :param results: tuple with results returned by getLinearResults()
    :return: dataframe with results
    """
    if len(results) == 2:
        puckFF, puckIFF = results
        S11, S22, S12, epsAxialBot, epsAxialTop, epsCircBot, epsCircTop = [[]], [[]], [[]], [], [], [], []
    else:
        S11, S22, S12, epsAxialBot, epsAxialTop, epsCircBot, epsCircTop, puckFF, puckIFF = results
    layers = range(puckFF.shape[1])
    dfList = [puckFF, puckIFF]
    for data, name in zip([S11, S22, S12, epsAxialBot, epsAxialTop, epsCircBot, epsCircTop],
                               ['S11', 'S22', 'S12', 'epsAxBot', 'epsAxTop', 'epsCircBot', 'epsCircTop']):
        if len(data.shape) == 2:
            columns = [f'{name}lay{layerNumber}' for layerNumber in layers]
            dfAdd = pd.DataFrame(data, columns=columns)
        else:
            dfAdd = pd.DataFrame(np.array([data]).T, columns=[name])
        dfList.append(dfAdd)
    df = pd.concat(dfList, join='outer', axis=1)
    return df


def getCriticalElementIdx(puck):
    """Returns the index of the most critical element

    :param puck: 2d array defining puckFF or puckIFF for each element and layer
    """
    # identify critical element
    layermax = puck.max().argmax()
    return puck.idxmax()[layermax], layermax