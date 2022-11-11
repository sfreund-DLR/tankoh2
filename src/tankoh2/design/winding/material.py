"""define material and composite"""

import numpy as np
import os

from tankoh2 import pychain, log
from tankoh2.design.winding.windingutils import copyAsJson, updateName
from tankoh2.service.exception import Tankoh2Error


def getMaterial(materialFilename=None):
    """Creates a pychain material object"""
    material = pychain.material.OrthotropMaterial()
    if materialFilename:
        if not os.path.exists(materialFilename):
            raise Tankoh2Error(f'File not found: "{materialFilename}"')
        material.loadFromFile(materialFilename)
    else:
        material.setDefaultCFRP()
    return material


def readLayupData(filename):
    """Reads layup data from a file.

    The data is a space separated matrix. Order of columns
    - angle
    - wendekreisdruchmesser
    - single ply thickness
    - krempendurchmesser

    :param filename: name of the file
    :return:
    """
    data = np.abs(np.loadtxt(filename))
    angle_degree, wendekreisdurchmesser, singlePlyThickenss, krempendruchmesser, hoopShift = data.T
    wendekreisradien = wendekreisdurchmesser / 2.
    krempenradien = krempendruchmesser / 2.
    return np.array([angle_degree, singlePlyThickenss, wendekreisradien, krempenradien, hoopShift])


def getFibreVolumeContent(sectionAreaFibre, rovingWidth, plyThickness):
    """Calculates the fibre volume content"""
    fvg = sectionAreaFibre / (rovingWidth * plyThickness)
    if not (.5 < fvg < .7):
        log.warning(f'Calculated fibre volume content of {fvg} which seems too {"high" if fvg > 70 else "low"}. '
                    f'sectionAreaFibre, rovingWidth, plyThickness: {sectionAreaFibre, rovingWidth, plyThickness}')
    return fvg


def checkFibreVolumeContent(layerThkHoop, layerThkHelical, sectionAreaFibre,
                            rovingWidthHoop, rovingWidthHelical, tex):
    """Compares the fibre volume content between helical and hoop layers"""
    fvgHoop = getFibreVolumeContent(sectionAreaFibre, rovingWidthHoop, layerThkHoop)
    fvgHelical = getFibreVolumeContent(sectionAreaFibre, rovingWidthHelical, layerThkHelical)
    log.info(f'fibre volume content hoop {fvgHoop} and helical {fvgHelical}')
    if abs(fvgHoop - fvgHelical) > 0.05:
        log.warning('The fibre volume contents of hoop and helical layers differ by more than 5%')


def getComposite(angles, layerThkHoop, layerThkHelical, material, sectionAreaFibre,
                 rovingWidthHoop, rovingWidthHelical, numberOfRovingsHelical, numberOfRovingsHoop, tex,
                 designFilename=None, designName=None):
    thicknesses, rovingWidths, numberOfRovings = [], [], []
    for angle in angles:
        if angle > 88:
            thicknesses.append(layerThkHoop)
            rovingWidths.append(rovingWidthHoop)
            numberOfRovings.append(numberOfRovingsHoop)
        else:
            thicknesses.append(layerThkHelical)
            rovingWidths.append(rovingWidthHelical)
            numberOfRovings.append(numberOfRovingsHelical)

    return getCompositeByLists(angles, thicknesses, rovingWidths, numberOfRovings,
                               material, sectionAreaFibre, tex, designFilename, designName)


def getCompositeByLists(angles, thicknesses, rovingWidths, numberOfRovingsList, material, sectionAreaFibre,
                        tex, designFilename=None, designName=None):
    # create composite with layers
    composite = pychain.material.Composite()

    for i, (angle, plyThickness, rovingWidth, numberOfRovings) in \
            enumerate(zip(angles, thicknesses, rovingWidths, numberOfRovingsList)):  #
        composite.appendLayer(angle, plyThickness, material, pychain.material.LAYER_TYPES.BAP)
        layer = composite.getOrthotropLayer(i)
        layer.phi = getFibreVolumeContent(sectionAreaFibre, rovingWidth, plyThickness)
        layer.windingProperties.texNumber = tex
        layer.windingProperties.coverage = 1.
        layer.windingProperties.rovingWidth = rovingWidth
        layer.windingProperties.cylinderThickness = plyThickness
        layer.windingProperties.numberOfRovings = numberOfRovings
        if angle > 88.:
            layer.windingProperties.isHoop = True

    saveComposite(composite, designFilename, designName)
    composite = pychain.material.Composite()
    composite.loadFromFile(designFilename)

    return composite

def saveComposite(composite, designFilename, designName):
    composite.updateThicknessFromWindingProperties()
    composite.saveToFile(designFilename)
    updateName(designFilename, designName, ["designs", "1"])
    copyAsJson(designFilename, 'design')