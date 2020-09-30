"""define material and composite"""

import numpy as np

from tankoh2 import pychain
from tankoh2.utilities import updateName, copyAsJson


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
    angle_degree, wendekreisdurchmesser, singlePlyThickenss, krempendruchmesser = data.T
    wendekreisradien = wendekreisdurchmesser / 2.
    krempenradien = krempendruchmesser / 2.
    return np.array([angle_degree, singlePlyThickenss, wendekreisradien, krempenradien])


def getComposite(material, angle_degree, singlePlyThickenss, hoopLayerThickness, helixLayerThickenss,
                 sectionAreaFibre, bandWidth, rovingWidth, numberOfRovings, tex,
                 designFilename=None, designName=None):
    # create composite with layers
    composite = pychain.material.Composite()

    for i in range(len(angle_degree)):  #
        angle = angle_degree[i]
        composite.appendLayer(angle, singlePlyThickenss[i], material, pychain.material.LAYER_TYPES.BAP)
        fvg = sectionAreaFibre / (bandWidth * singlePlyThickenss[i])
        composite.getOrthotropLayer(i).phi = fvg

        if angle == 90.:
            # change winding properties
            composite.getOrthotropLayer(i).windingProperties.rovingWidth = rovingWidth
            composite.getOrthotropLayer(i).windingProperties.numberOfRovings = numberOfRovings
            composite.getOrthotropLayer(i).windingProperties.texNumber = tex
            composite.getOrthotropLayer(i).windingProperties.coverage = 1.
            composite.getOrthotropLayer(i).windingProperties.isHoop = True
            composite.getOrthotropLayer(i).windingProperties.cylinderThickness = hoopLayerThickness

        else:
            # change winding properties
            composite.getOrthotropLayer(i).windingProperties.rovingWidth = rovingWidth
            composite.getOrthotropLayer(i).windingProperties.numberOfRovings = numberOfRovings
            composite.getOrthotropLayer(i).windingProperties.texNumber = tex
            composite.getOrthotropLayer(i).windingProperties.coverage = 1.
            composite.getOrthotropLayer(i).windingProperties.cylinderThickness = helixLayerThickenss

    composite.updateThicknessFromWindingProperties()
    composite.saveToFile(designFilename)
    updateName(designFilename, designName, ["designs", "1"])
    copyAsJson(designFilename, 'design')
    composite = pychain.material.Composite()
    composite.loadFromFile(designFilename, 1)
    return composite
