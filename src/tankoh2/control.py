"""control a tank optimization"""

import os
import numpy as np
from scipy.optimize import curve_fit

from tankoh2 import programDir, log, pychain
from tankoh2.service import indent
from tankoh2.settings import myCrOSettings as settings
from tankoh2.utilities import updateName
from tankoh2.contour import getLiner, getDome, getReducedDomePoints
from tankoh2.material import getMaterial, getComposite, readLayupData
from tankoh2.optimize import optimizeFriction, optimizeHoopShift


def linear(x, m, n):
    return m * x + n


def fitting_linear(x, y):
    popt, pcov = curve_fit(linear, x, y, bounds=([-np.inf, -np.inf], [np.inf, np.inf]))
    m, n = popt[:2]
    return m, n


def main():
    # #########################################################################################
    # SET Parameters of vessel
    # #########################################################################################
    tankname = 'NGT-BIT-2020-09-16'
    dataDir = os.path.join(programDir, 'data')
    dzyl = 400.  # mm
    polarOpening = 20.  # mm
    lzylinder = 500.  # mm
    dpoints = 4  # data points for liner contour
    defaultLayerthickness = 0.125
    hoopLayerThickness = 0.125
    helixLayerThickenss = 0.129
    bandWidth = 3.175
    numberOfRovings = 1
    rovingWidth = bandWidth / numberOfRovings
    tex = 446  # g / km
    rho = 1.78  # g / cm^3
    sectionAreaFibre = tex / (1000. * rho)
    layersToWind = 50

    fileNameReducedDomeContour = os.path.join(dataDir, "Dome_contour_" + tankname + "_modified.dcon")
    linerFilename = os.path.join(dataDir, tankname + ".liner")
    designFilename = os.path.join(dataDir, tankname + ".design")
    layupDataFilename = os.path.join(dataDir, "Winding_" + tankname + ".txt")
    windingFile = os.path.join(dataDir, tankname + "_realised_winding.txt")
    vesselFilename = os.path.join(dataDir, tankname + ".vessel")

    # #########################################################################################
    # Create Liner
    # #########################################################################################
    x, r = getReducedDomePoints(os.path.join(dataDir, "Dome_contour_" + tankname + ".txt"),
                                dpoints, fileNameReducedDomeContour)
    dome = getDome(dzyl / 2., polarOpening, pychain.winding.DOME_TYPES.ISOTENSOID,
                   x, r)
    liner = getLiner(dome, lzylinder, linerFilename, tankname)

    # ###########################################
    # Create material
    # ###########################################
    material = getMaterial(os.path.join(dataDir, "CFRP_HyMod.json"))

    angles, thicknesses, wendekreisradien, krempenradien = readLayupData(layupDataFilename)
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
            # global arr_fric, arr_wk
            # global arr_fric, arr_wk
            # arr_fric = []
            # arr_wk = []
            log.info(f'apply layer {i} with angle {angle}, Sollwendekreisradius {wendekreisradius}')
            friction, err_wk, iterations = optimizeFriction(vessel, wendekreisradius, layerindex, verbose=False)
            log.info(f'{iterations} iterations. Friction is {friction} resulting in a polar opening error of {err_wk} '
                     f'as current polar opening is {vessel.getPolarOpeningR(layerindex, True)}')
            # file = open("data.txt", "w")
            # for j in range(len(arr_fric)):
            #    file.write(str(arr_fric[j])+'\t'+str(arr_wk[j])+'\n')
            # file.close()
            # plt.plot(arr_fric, arr_wk, marker = 'o', linewidth = 0.)
            # m, n = fitting_linear(arr_fric,arr_wk)
            # log.info(m,n)
            # friction_corr = (wendekreisradius[i] - n) / m
            # vessel.setLayerFriction(layerindex, friction_corr, True)
            # vessel.runWindingSimulation(layerindex+1)
            # wk_korr = vessel.getPolarOpeningR(layerindex, True)
            # print (friction_corr, wk_korr)
            # y = linear(arr_fric, np.ones(len(arr_fric))*m, np.ones(len(arr_fric))*n)
            # plt.plot(arr_fric, y,'k--', lw = 1.)
            # plt.plot(friction_corr, wk_korr, 'ro')
            # plt.xlim((0., 0.0001))
            # plt.ylim((25., 27.))
            # plt.show()

        po = vessel.getPolarOpeningR(layerindex, True)
        outArr.append([i, angle, po, po*2])
        with open(windingFile, "a") as file:
            file.write('\t'.join([str(s) for s in outArr[-1]]) + '\n')

    with open(windingFile, "w") as file:
        file.write(indent([["Layer \#", "Angle", "Polar opening", "Polar opening diameter"]] + outArr))

    # save vessel
    vessel.saveToFile(vesselFilename)  # save vessel
    updateName(vesselFilename, tankname, ['vessel'])

    # save winding results
    windingResults = pychain.winding.VesselWindingResults()
    windingResults.buildFromVessel(vessel)
    windingResults.saveToFile(os.path.join(dataDir, tankname + ".wresults"))

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
    scriptGenerator.writeVesselAxSolidBuildScript(os.path.join(dataDir, tankname + "_Build.py"), settings, modelOptions)
    scriptGenerator.writeVesselAxSolidBuildScript(os.path.join(dataDir, tankname + "_Eval.py"), settings, modelOptions)

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
