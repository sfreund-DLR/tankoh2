"""control a tank optimization"""



import os
import numpy as np
from scipy.optimize import curve_fit
from scipy.optimize import minimize_scalar
from scipy.optimize import minimize

from tankoh2 import programDir, log
from tankoh2.service import indent
from tankoh2.settings import myCrOSettings as settings
from tankoh2.utilities import updateName
from tankoh2.contour import getLiner, getDome, getReducedDomePoints
from tankoh2.material import getMaterial, getComposite, readLayupData
import mycropychain as pychain


# #########################################################################################
# DEFINE SUBROUTINES
# #########################################################################################

def linear(x, m, n):
    return m * x + n


def fitting_linear(x, y):
    popt, pcov = curve_fit(linear, x, y, bounds=([-np.inf, -np.inf], [np.inf, np.inf]))

    m = popt[0]
    n = popt[1]

    return m, n




def getPolarOpeningDiffHelical(friction, args):
    vessel, wendekreisradius, layerindex = args
    log.info('--------------------')
    vessel.setLayerFriction(layerindex, abs(friction), True)
    log.info(f'set friction {friction}')

    try:
        vessel.runWindingSimulation(layerindex + 1)
        log.info(f'apply layer {layerindex}')
        wk = vessel.getPolarOpeningR(layerindex, True)
        log.info(wk)
    except (IOError, ValueError, IOError, ZeroDivisionError):
        log.info('I have to pass')

    # log.info('this helical layer shoud end at', wendekreisradius[layerindex], 'mm but is at', wk, 'mm so there is a
    # deviation of', wendekreisradius[layerindex]-wk, 'mm') if abs(wendekreisradius[layerindex]-wk) < 2.:
    # arr_fric.append(abs(friction)) arr_wk.append(wk)

    return abs(wk - wendekreisradius[layerindex])


def optimizeFriction(vessel, wendekreisradius, layerindex):
    # popt, pcov = curve_fit(getPolarOpeningDiff, layerindex, wk_goal, bounds=([0.], [1.]))

    popt = minimize_scalar(getPolarOpeningDiffHelical, tol=0.00001, method='Golden', args=[vessel, wendekreisradius, layerindex],
                           options={"maxiter": 1000})
    # popt  = minimize(getPolarOpeningDiff, x0 = (1.), method = 'BFGS', args=[vessel, wendekreisradius],
    #                   options={'gtol': 1e-6, 'disp': True})
    friction = popt.x
    log.info(popt.success)
    return friction, popt.fun


def getPolarOpeningDiffHoop(shift, args):
    vessel, krempenradius, layerindex = args
    vessel.setHoopLayerShift(layerindex, shift, True)
    vessel.runWindingSimulation(layerindex + 1)
    wk = vessel.getPolarOpeningR(layerindex, True)

    # log.info('this hoop layer shoud end at', krempenradius[layerindex], 'mm but is at', wk, 'mm so there is a
    # deviation of', krempenradius[layerindex]-wk, 'mm')

    return abs(wk - krempenradius[layerindex])


def optimizeHoopShift(vessel, krempenradius, layerindex):
    popt = minimize_scalar(getPolarOpeningDiffHoop, tol=0., args=[vessel, krempenradius, layerindex])
    shift = popt.x
    return shift, popt.fun


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
    layersToWind = 4

    fileNameReducedDomeContour = os.path.join(dataDir, "Dome_contour_" + tankname + "_modified.dcon")
    linerFilename = os.path.join(dataDir, tankname + ".liner")
    designFilename = os.path.join(dataDir, tankname + ".design")
    layupDataFilename = os.path.join(dataDir, "Winding_" + tankname + ".txt")
    windingFile = os.path.join(dataDir, tankname + "_realised_winding.txt")
    vesselFilename = os.path.join(dataDir, tankname + ".vessel")


    # #########################################################################################
    # Create Liner
    # #########################################################################################
    x,r = getReducedDomePoints(os.path.join(dataDir, "Dome_contour_" + tankname + ".txt"),
                               dpoints, fileNameReducedDomeContour)
    dome = getDome(dzyl / 2., polarOpening, pychain.winding.DOME_TYPES.ISOTENSOID,
                   x,r)
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
        file.write('\t'.join(["Layer number", "Angle", "Polar opening"])+'\n')
    outArr = []
    vessel.resetWindingSimulation()
    for i, angle, krempenradius, wendekreisradius in zip(range(layersToWind), angles, krempenradien, wendekreisradien):  # len(angle_degree)
        log.info('--------------------------------------------------')
        log.info(f'apply layer {i} with angle {angle}')
        layerindex = i
        # wk = winding_layer(i, 0.5)
        if abs(angle - 90.) < 1e-8:
            log.info(f'Sollwendekreisradius {krempenradius}')
            shift, err_wk = optimizeHoopShift(vessel, krempenradien, layerindex)
            log.info(f'optimised shift is {shift} resulting in a polar opening error of {err_wk} '
                     f'as current polar opening is {vessel.getPolarOpeningR(layerindex, True)}')
        else:
            # global arr_fric, arr_wk
            # global arr_fric, arr_wk
            # arr_fric = []
            # arr_wk = []
            log.info(f'Sollwendekreisradius {wendekreisradius}')
            friction, err_wk = optimizeFriction(vessel, wendekreisradien, layerindex)
            log.info(f'optimised friction is {friction} resulting in a polar opening error of {err_wk}'
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

        outArr.append([i, angle, vessel.getPolarOpeningR(layerindex, True)])
        with open(windingFile, "a") as file:
            file.write('\t'.join([str(s) for s in outArr[-1]]) + '\n')

    with open(windingFile, "w") as file:
        file.write(indent([["Layer number", "Angle", "Polar opening"]] + outArr))

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
    #plt.show()

    log.info('FINISHED')


if __name__ == '__main__':
    main()



