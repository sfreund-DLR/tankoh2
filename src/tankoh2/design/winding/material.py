"""define material and composite"""

import numpy as np

from tankoh2 import pychain
from tankoh2.design.winding.windingutils import copyAsJson, updateName


def getMaterial(materialFilename=None):
    """Creates a pychain material object"""
    material = pychain.material.OrthotropMaterial()
    if materialFilename:
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


def getComposite(angles, thicknesses, material,
                 sectionAreaFibre, rovingWidth, numberOfRovingsHelical, numberOfRovingsHoop, tex, designFilename=None, designName=None):
    # create composite with layers
    composite = pychain.material.Composite()

    for i, angle, plyThickness in zip(range(len(angles)), angles, thicknesses):  #
        composite.appendLayer(angle, plyThickness, material, pychain.material.LAYER_TYPES.BAP)
        fvg = sectionAreaFibre / (rovingWidth * plyThickness)
        layer = composite.getOrthotropLayer(i)
        layer.phi = fvg
        layer.windingProperties.rovingWidth = rovingWidth        
        layer.windingProperties.texNumber = tex
        layer.windingProperties.coverage = 1.
        if angle == 90.:
            layer.windingProperties.isHoop = True
            layer.windingProperties.cylinderThickness = plyThickness
            layer.windingProperties.numberOfRovings = numberOfRovingsHoop
        else:
            layer.windingProperties.cylinderThickness = plyThickness
            layer.windingProperties.numberOfRovings = numberOfRovingsHelical

    saveComposite(composite, designFilename, designName)
    composite = pychain.material.Composite()
    composite.loadFromFile(designFilename)

    return composite

def saveComposite(composite, designFilename, designName):
    composite.updateThicknessFromWindingProperties()
    composite.saveToFile(designFilename)
    updateName(designFilename, designName, ["designs", "1"])
    copyAsJson(designFilename, 'design')