"""control a tank optimization"""

import os, sys
#print('path')
#print('\n'.join(os.environ['PATH'].split(';')))
#print('pythonpath')
#print('\n'.join(sys.path))

import numpy as np
import pandas

from tankoh2 import programDir, log, pychain
from tankoh2.service import indent, getRunDir, plotStressEpsPuck
from tankoh2.utilities import updateName, copyAsJson
from tankoh2.contour import getLiner, getDome
from tankoh2.material import getMaterial, getComposite, readLayupData
from tankoh2.winding import windLayer
from tankoh2.optimize import optimizeAngle, maximizeInitialAngleToFitting
from tankoh2.solver import getLinearResults

def main():
    # #########################################################################################
    # SET Parameters of vessel
    # #########################################################################################
    layersToWind = 7
    tankname = 'NGT-BIT-2020-09-16'
    dataDir = os.path.join(programDir, 'data')
    dzyl = 400.  # mm
    lzylinder = 500.  # mm
    hoopLayerThickness = 0.125
    helixLayerThickenss = 0.129
    rovingWidth = 3.175
    numberOfRovings = 4
    bandWidth = rovingWidth * numberOfRovings
    tex = 446  # g / km
    rho = 1.78  # g / cm^3
    sectionAreaFibre = tex / (1000. * rho)
    safetyFactor = 2.5

    # design constants AND not recognized issues
    minPolarOpening = 20 #mm
    # band pattern not recognized


    # input files
    layupDataFilename = os.path.join(dataDir, "Winding_" + tankname + ".txt")
    materialFilename = os.path.join(dataDir, "CFRP_HyMod.json")
    # output files
    runDir = getRunDir()
    linerFilename = os.path.join(runDir, tankname + ".liner")
    designFilename = os.path.join(runDir, tankname + ".design")
    windingFile = os.path.join(runDir, tankname + "_realised_winding.txt")
    vesselFilename = os.path.join(runDir, tankname + ".vessel")
    windingResultFilename = os.path.join(runDir, tankname + ".wresults")

    # #########################################################################################
    # Create Liner
    # #########################################################################################
    dome = getDome(dzyl / 2., minPolarOpening, pychain.winding.DOME_TYPES.ISOTENSOID)
    liner = getLiner(dome, lzylinder, linerFilename, tankname)

    # ###########################################
    # Create material
    # ###########################################
    material = getMaterial(materialFilename)
    puckProperties = material.puckProperties

    angles, thicknesses, wendekreisradien, krempenradien = readLayupData(layupDataFilename)[:,:layersToWind]
    try:
        angles[2] = 40.
        angles[5] = 90.
        angles[6] = 90.
    except:pass
    composite = getComposite(material, angles, thicknesses, hoopLayerThickness, helixLayerThickenss,
                             sectionAreaFibre, rovingWidth, numberOfRovings, tex,
                             designFilename, tankname)
    composite.info()
    # create vessel and set liner and composite
    vessel = pychain.winding.Vessel()
    vessel.setLiner(liner)
    vessel.setComposite(composite)

    # #############################################################################
    # run winding simulation
    # #############################################################################

    with open(windingFile, "w") as file:
        file.write('\t'.join(["Layer number", "Angle", "Polar opening"]) + '\n')
    outArr = []
    vessel.resetWindingSimulation()

    #start with hoop layer
    polarOpening = windLayer(vessel, 0, 90)

    #introduce layer up to the fitting. Optimize required angle
    layerNumber = 1
    angle, _, _ = maximizeInitialAngleToFitting(vessel, minPolarOpening, layerNumber, True)
    vessel.setLayerAngle(layerNumber, angle)
    vessel.runWindingSimulation(layerNumber + 1)

    # create other layers
    layerNumber = 2
    results = getLinearResults(vessel, puckProperties, 2)
    plotStressEpsPuck(True,None, *results)
    puckFF, puckIFF = results[7:9]
    # only observe one cylinder element and dome elements starting at ...
    dropIndicies = range(1,320)
    puckFF.drop(dropIndicies, inplace=True)
    puckIFF.drop(dropIndicies, inplace=True)
    layermax = puckFF.max().argmax()
    idxmax = puckFF.idxmax()[layermax]

    radii = pandas.DataFrame([vessel.getVesselLayer(layerNumber-1).getOuterMandrel1().getRArray()],
                             columns=['radius'])
    radiusmax = radii[idxmax]

    vessel.finishWinding()
    # save vessel
    vessel.saveToFile(vesselFilename)  # save vessel
    updateName(vesselFilename, tankname, ['vessel'])
    copyAsJson(vesselFilename, 'vessel')

    # save winding results
    windingResults = pychain.winding.VesselWindingResults()
    windingResults.buildFromVessel(vessel)
    windingResults.saveToFile(windingResultFilename)
    copyAsJson(windingResultFilename, 'wresults')


    from tankoh2.utilities import getElementThicknesses
    t = getElementThicknesses(vessel)



    # #############################################################################
    # run Evaluation
    # #############################################################################
    results = getLinearResults(vessel, puckProperties, layersToWind)
    plotStressEpsPuck(True,None, *results)


    log.info('FINISHED')


if __name__ == '__main__':
    main()


