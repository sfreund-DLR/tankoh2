"""
doc

"""


import json as json
import os
import numpy as np
from scipy.optimize import curve_fit

from tankoh2 import programDir, log
from tankoh2.settings import myCrOSettings as settings
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


from scipy.optimize import minimize_scalar
from scipy.optimize import minimize


def winding_helical_layer(friction, args):
    vessel, wendekreisradius = args
    log.info('--------------------')
    log.info(f'use friction {friction}')
    vessel.setLayerFriction(layerindex, abs(friction), True)
    log.info(f'set friction {friction}')

    try:
        vessel.runWindingSimulation(layerindex + 1)  #
        log.info(f'apply layer {layerindex}')
        wk = vessel.getPolarOpeningR(layerindex, True)
        log.info(wk)
    except (IOError, ValueError, IOError, ZeroDivisionError):
        log.info('I have to pass')

    # log.info('this helical layer shoud end at', wendekreisradius[layerindex], 'mm but is at', wk, 'mm so there is a
    # deviation of', wendekreisradius[layerindex]-wk, 'mm') if abs(wendekreisradius[layerindex]-wk) < 2.:
    # arr_fric.append(abs(friction)) arr_wk.append(wk)

    return abs(wk - wendekreisradius[layerindex])


def optimze_winding_parameters_friction(vessel, wendekreisradius):
    # popt, pcov = curve_fit(winding_helical_layer, layerindex, wk_goal, bounds=([0.], [1.]))

    popt = minimize_scalar(winding_helical_layer, tol=0.00001, method='Golden', args=[vessel, wendekreisradius],
                           options={"maxiter": 1000, 'disp': True})
    # popt  = minimize(winding_helical_layer, x0 = (1.), method = 'BFGS', args=[vessel, wendekreisradius],
    #                   options={'gtol': 1e-6, 'disp': True})

    friction = popt.x
    log.info(popt.success)

    return friction, winding_helical_layer(friction, [vessel, wendekreisradius])


def winding_hoop_layer(shift, args):
    vessel, krempenradius, layerindex = args
    vessel.setHoopLayerShift(layerindex, shift, True)
    vessel.runWindingSimulation(layerindex + 1)
    wk = vessel.getPolarOpeningR(layerindex, True)

    # log.info('this hoop layer shoud end at', krempenradius[layerindex], 'mm but is at', wk, 'mm so there is a
    # deviation of', krempenradius[layerindex]-wk, 'mm')

    return abs(wk - krempenradius[layerindex])


def optimze_winding_parameters_shift(vessel, krempenradius, layerindex):
    popt = minimize_scalar(winding_hoop_layer, tol=0., args=[vessel, krempenradius, layerindex])

    shift = popt.x

    return shift, winding_hoop_layer(shift, [vessel, krempenradius, layerindex])


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

    # #########################################################################################
    # Create Liner
    # #########################################################################################

    # load contour from file
    Data = np.loadtxt(os.path.join(dataDir, "Dome_contour_" + tankname + ".txt"))
    Xvec = abs(Data[:, 0])
    Xvec = Xvec - Xvec[0]
    rVec = abs(Data[:, 1])

    # reduce data points
    log.info(len(Xvec) - 1)
    index = np.linspace(0, dpoints * int((len(Xvec) / dpoints)), int((len(Xvec) / dpoints)) + 1, dtype=np.int16)

    arr = [len(Xvec) - 1]
    index = np.append(index, arr)

    Xvec = Xvec[index]
    rVec = rVec[index]

    # save liner contour for loading in mikroWind
    with open(os.path.join(dataDir, "Dome_contour_" + tankname + "_modified.dcon"), "w") as contour:
        for i in range(len(Xvec)):
            contour.write(str(Xvec[i]) + ',' + str(rVec[i]) + '\n')

    # build  dome
    dome = pychain.winding.Dome()
    dome.buildDome(dzyl / 2., polarOpening, pychain.winding.DOME_TYPES.ISOTENSOID)
    dome.setPoints(Xvec, rVec)
    log.info(f'Build Dome with dome data {dome}')

    # create a symmetric liner with dome information and cylinder length
    liner = pychain.winding.Liner()
    # spline for winding calculation is left on default of 1.0
    liner.buildFromDome(dome, lzylinder, 1.0)

    # save liner for visualization with µChainWind
    liner.saveToFile(os.path.join(dataDir, tankname + ".liner"))
    log.info('saved liner')

    # change name of liner in file
    with open(tankname + ".liner") as jsonFile:
        data = json.load(jsonFile)
    data["liner"]["name"] = tankname
    with open(os.path.join(dataDir, tankname + ".liner"), "w") as jsonFile:
        json.dump(data, jsonFile)

    # copyfile(tankname+"_.liner", tankname+'_copy.liner')

    # fobj = open(tankname+"_copy.liner")
    # fobj_new = open(tankname+"_.liner", "w")

    # for line in fobj:
    #     if line[9:13]=='name':
    #         print ('change name from '+line+' to '+tankname)
    #         fobj_new.write('\t\t"name": "'+tankname+'", \n')
    #     else:
    #         fobj_new.write(line)
    # fobj.close()
    # fobj_new.close()
    # os.remove(tankname+"_copy.liner")

    # ###########################################
    # Create winding
    # ###########################################

    # create default material
    # t700 = pychain.material.OrthotropMaterial()
    # t700.setDefaultCFRP()

    # load material
    material = pychain.material.OrthotropMaterial()
    material.loadFromFile(os.path.join(dataDir, "CFRP_HyMod.json"))
    mat = pychain.material

    # read winding angles in cylindrical regime
    Data = np.loadtxt(os.path.join(dataDir, "Winding_" + tankname + ".txt"))
    angle_degree = abs(Data[:, 0])
    wendekreisdurchmesser = abs(Data[:, 1])
    wendekreisradius = wendekreisdurchmesser / 2.
    singlePlyThickenss = abs(Data[:, 2])
    krempendruchmesser = abs(Data[:, 3])
    krempenradius = krempendruchmesser / 2.

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
    composite.saveToFile(tankname + ".design")

    # rename design
    with open(os.path.join(dataDir, tankname + ".design")) as jsonFile:
        data = json.load(jsonFile)
    data["designs"]["1"]["name"] = tankname
    with open(os.path.join(dataDir, tankname + ".design"), "w") as jsonFile:
        json.dump(data, jsonFile)

    # create vessel and set liner and composite
    vessel = pychain.winding.Vessel()
    vessel.setLiner(liner)
    vessel.setComposite(composite)

    # #############################################################################
    # run winding simulation
    # #############################################################################

    # vessel.finishWinding()
    global layerindex
    with open(os.path.join(dataDir, tankname + "_realised_winding.txt"), "w") as file:
        file.write("Layer number" + '\t' + "Angle" + '\t' + "Polar opening" + '\n')
        vessel.resetWindingSimulation()
        for i in range(5):  # len(angle_degree)
            log.info('--------------------------------------------------')
            log.info(f'apply layer {i + 1} with angle {angle_degree[i]}')
            layerindex = i
            # wk = winding_layer(i, 0.5)
            if angle_degree[i] == 90.:
                log.info(f'Sollwendekreisradius {krempenradius[i]}')
                shift, err_wk = optimze_winding_parameters_shift(vessel, krempenradius, layerindex)
                log.info(f'optimised shift is {shift} resulting in a polar opening error of {err_wk} '
                         f'as current polar opening is {vessel.getPolarOpeningR(layerindex, True)}')
            else:
                # global arr_fric, arr_wk
                # global arr_fric, arr_wk
                # arr_fric = []
                # arr_wk = []
                log.info(f'Sollwendekreisradius {wendekreisradius[i]}')
                friction, err_wk = optimze_winding_parameters_friction(vessel, wendekreisradius)
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
    
            file.write(
                str(i + 1) + '\t' + str(angle_degree[i]) + '\t' + str(vessel.getPolarOpeningR(layerindex, True)) + '\n')


    # save vessel
    vessel.saveToFile(os.path.join(dataDir, tankname + ".vessel"))  # save vessel

    with open(os.path.join(dataDir, tankname + ".vessel")) as jsonFile:
        data = json.load(jsonFile)
    data["vessel"]["name"] = tankname
    with open(os.path.join(dataDir, tankname + ".vessel"), "w") as jsonFile:
        json.dump(data, jsonFile)

    # rename vessel

    # save winding results
    windingResults = pychain.winding.VesselWindingResults()
    windingResults.buildFromVessel(vessel)
    windingResults.saveToFile(os.path.join(dataDir, tankname + ".wresults"))

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
    plt.show()

    log.info('FINISHED')


if __name__ == '__main__':
    main()
