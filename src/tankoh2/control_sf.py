"""control a tank optimization"""

import os

from tankoh2 import programDir, log, pychain
from tankoh2.service import indent, getRunDir
from tankoh2.settings import myCrOSettings as settings
from tankoh2.utilities import updateName, copyAsJson
from tankoh2.contour import getLiner, getDome, getReducedDomePoints
from tankoh2.material import getMaterial, getComposite, readLayupData
from tankoh2.optimize import optimizeFriction, optimizeHoopShift


def main():
    # #########################################################################################
    # SET Parameters of vessel
    # #########################################################################################
    layersToWind = 5
    tankname = 'NGT-BIT-2020-09-16'
    dataDir = os.path.join(programDir, 'data')
    dzyl = 400.  # mm
    polarOpening = 20.  # mm
    lzylinder = 500.  # mm
    dpoints = 4  # data points for liner contour
    defaultLayerthickness = 0.125
    hoopLayerThickness = 0.125
    helixLayerThickenss = 0.129
    bandWidthMult = 4
    bandWidth = 3.175 * bandWidthMult
    numberOfRovings = 1
    rovingWidth = bandWidth / numberOfRovings
    tex = 446  # g / km
    rho = 1.78  # g / cm^3
    sectionAreaFibre = tex / (1000. * rho)

    # input files
    layupDataFilename = os.path.join(dataDir, "Winding_" + tankname + ".txt")
    materialFilename = os.path.join(dataDir, "CFRP_HyMod.json")
    domeContourFilename = os.path.join(dataDir, "Dome_contour_" + tankname + ".txt")
    # output files
    runDir = getRunDir()
    fileNameReducedDomeContour = os.path.join(runDir, f"Dome_contour_{tankname}_reduced.dcon")
    linerFilename = os.path.join(runDir, tankname + ".liner")
    designFilename = os.path.join(runDir, tankname + ".design")
    windingFile = os.path.join(runDir, tankname + "_realised_winding.txt")
    vesselFilename = os.path.join(runDir, tankname + ".vessel")
    windingResultFilename = os.path.join(runDir, tankname + ".wresults")

    # #########################################################################################
    # Create Liner
    # #########################################################################################
    x, r = getReducedDomePoints(domeContourFilename,
                                dpoints, fileNameReducedDomeContour)
    dome = getDome(dzyl / 2., polarOpening, pychain.winding.DOME_TYPES.ISOTENSOID,
                   x, r)
    liner = getLiner(dome, lzylinder, linerFilename, tankname)

    # ###########################################
    # Create material
    # ###########################################
    material = getMaterial(materialFilename)

    angles, thicknesses, wendekreisradien, krempenradien = readLayupData(layupDataFilename)[:,:layersToWind]
    angles[2] = 40.
    composite = getComposite(material, angles, thicknesses, hoopLayerThickness, helixLayerThickenss,
                             sectionAreaFibre, bandWidth, rovingWidth, numberOfRovings, tex,
                             designFilename, tankname)

    # create vessel and set liner and composite
    vessel = pychain.winding.Vessel()
    vessel.setLiner(liner)
    vessel.setComposite(composite)

    # #############################################################################
    # run winding simulation
    # #############################################################################

    # vessel.finishWinding()
    with open(windingFile, "w") as file:
        file.write('\t'.join(["Layer number", "Angle", "Polar opening"]) + '\n')
    outArr = []
    vessel.resetWindingSimulation()
    for i, angle, krempenradius, wendekreisradius in zip(range(layersToWind), angles, krempenradien,
                                                         wendekreisradien):  # len(angle_degree)
        log.info('--------------------------------------------------')
        layerindex = i
        # wk = winding_layer(i, 0.5)
        if abs(angle - 90.) < 1e-8:
            log.info(f'apply layer {i} with angle {angle}, Sollwendekreisradius {krempenradius}')
            shift, err_wk, iterations = optimizeHoopShift(vessel, krempenradius, layerindex)
            log.info(f'{iterations} iterations. Shift is {shift} resulting in a polar opening error of {err_wk} '
                     f'as current polar opening is {vessel.getPolarOpeningR(layerindex, True)}')
        else:
            log.info(f'apply layer {i} with angle {angle}, Sollwendekreisradius {wendekreisradius}')
            friction, err_wk, iterations = optimizeFriction(vessel, wendekreisradius, layerindex, verbose=False)
            log.info(f'{iterations} iterations. Friction is {friction} resulting in a polar opening error of {err_wk} '
                     f'as current polar opening is {vessel.getPolarOpeningR(layerindex, True)}')

        po = vessel.getPolarOpeningR(layerindex, True)
        outArr.append([i, angle, po, po*2])
        with open(windingFile, "a") as file:
            file.write('\t'.join([str(s) for s in outArr[-1]]) + '\n')

    with open(windingFile, "w") as file:
        file.write(indent([["Layer \#", "Angle", "Polar opening", "Polar opening diameter"]] + outArr))

    # save vessel
    vessel.saveToFile(vesselFilename)  # save vessel
    updateName(vesselFilename, tankname, ['vessel'])
    copyAsJson(vesselFilename, 'vessel')

    # save winding results
    windingResults = pychain.winding.VesselWindingResults()
    windingResults.buildFromVessel(vessel)
    windingResults.saveToFile(windingResultFilename)
    copyAsJson(windingResultFilename, 'wresults')

    # #############################################################################
    # run Abaqus
    # #############################################################################

    # build shell model for internal calculation
    converter = pychain.mycrofem.VesselConverter()
    shellModel = converter.buildAxShellModell(vessel, 10)

    # run linear solver
    linerSolver = pychain.mycrofem.LinearSolver(shellModel)
    linerSolver.run(True)

    # get stresses in the fiber COS
    S11, S22, S12 = shellModel.calculateLayerStressesBottom()
    # get  x coordinates (element middle)
    xCoords = shellModel.getElementCoordsX()

    # create model options for abaqus calculation
    modelOptions = pychain.mycrofem.VesselFEMModelOptions()
    modelOptions.modelName = tankname + "_Vessel"
    modelOptions.jobName = tankname + "_Job"
    modelOptions.windingResultsFileName = tankname
    modelOptions.useMaterialPhi = False
    modelOptions.fittingContactWinding = pychain.mycrofem.CONTACT_TYPE.PENALTY
    modelOptions.globalMeshSize = 0.25
    modelOptions.pressureInBar = 300.0

    # write abaqus scripts
    scriptGenerator = pychain.abaqus.AbaqusVesselScriptGenerator()
    scriptGenerator.writeVesselAxSolidBuildScript(os.path.join(runDir, tankname + "_Build.py"), settings, modelOptions)
    scriptGenerator.writeVesselAxSolidBuildScript(os.path.join(runDir, tankname + "_Eval.py"), settings, modelOptions)

    import matplotlib.pylab as plt

    fig = plt.figure()
    ax = fig.gca()
    ax.plot(S11[:, 0])
    ax.plot(S11[:, 1])
    ax.plot(S11[:, 2])
    # plt.show()

    log.info('FINISHED')


if __name__ == '__main__':
    main()


