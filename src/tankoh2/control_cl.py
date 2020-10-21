"""control a tank optimization"""

import os
import numpy as np
from scipy.optimize import curve_fit

from tankoh2 import programDir, log, pychain
from tankoh2.service import indent, getRunDir
from tankoh2.settings import myCrOSettings as settings
from tankoh2.utilities import updateName, getRadiusByShiftOnMandrel
from tankoh2.contour import getLiner, getDome, getReducedDomePoints #, getLengthContourPath
from tankoh2.material import getMaterial, getComposite, readLayupData
from tankoh2.optimize import optimizeFriction, optimizeHoopShift, optimizeFrictionGlobal_differential_evolution, optimizeHoopShiftForPolarOpeningX,\
    optimizeNegativeFrictionGlobal_differential_evolution

def main():
    # #########################################################################################
    # SET Parameters of vessel
    # #########################################################################################
    layersToWind = 48
    optimizeWindingHelical = True
    optimizeWindingHoop = False
    
    tankname = 'NGT-BIT-2020-09-16'
    dataDir = os.path.join(programDir, 'data')
    dzyl = 400.  # mm
    polarOpening = 48./2.  # mm
    lzylinder = 500.  # mm
    dpoints = 4  # data points for liner contour
    defaultLayerthickness = 0.125
    hoopLayerThickness = 0.125
    helixLayerThickenss = 0.129
    rovingWidth = 3.175
    numberOfRovings = 1
    bandWidth = rovingWidth * numberOfRovings
    log.info(f'winding using {numberOfRovings} robings with {rovingWidth}mm resulting in bandwith of {bandWidth}')
    tex = 446  # g / km
    rho = 1.78  # g / cm^3
    sectionAreaFibre = tex / (1000. * rho)

    # input files
    layupDataFilename = os.path.join(dataDir, "Winding_" + tankname + ".txt")
    materialFilename = os.path.join(dataDir, "CFRP_HyMod.json")
    domeContourFilename = os.path.join(dataDir, "Dome_contour_" + tankname + "_48mm.txt")
    # output files
    runDir = getRunDir()
    fileNameReducedDomeContour = os.path.join(runDir, f"Dome_contour_{tankname}_reduced.dcon")
    linerFilename = os.path.join(runDir, tankname + ".liner")
    designFilename = os.path.join(runDir, tankname + ".design")
    windingFile = os.path.join(runDir, tankname + "_realised_winding.txt")
    vesselFilename = os.path.join(runDir, tankname + ".vessel")
    windingResultFilename = os.path.join(runDir, tankname + ".wresults")
    
    #print(getLengthContourPath(domeContourFilename, 24., 51.175/2., 1))

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
    log.info(f'get material')
    material = getMaterial(materialFilename)

    

    angles, thicknesses, wendekreisradien, krempenradien = readLayupData(layupDataFilename)
    log.info(f'{angles[0:layersToWind]}')
    composite = getComposite(material, angles[0:layersToWind], thicknesses[0:layersToWind], hoopLayerThickness, helixLayerThickenss,
                             sectionAreaFibre, rovingWidth, numberOfRovings, tex,
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
    anzHoop = 0.
    anzHelix = 0.
    for i, angle, krempenradius, wendekreisradius in zip(range(layersToWind), angles, krempenradien,
                                                         wendekreisradien):  # len(angle_degree)
        log.info('--------------------------------------------------')
        layerindex = i
        # Hoop Layer
        if abs(angle - 90.) < 1e-8:
            #po_goal = krempenradius
            po_goal = lzylinder/2. - anzHoop*rovingWidth
            anzHoop = anzHoop+1
            #po_goal = wendekreisradius
            log.info(f'apply layer {i+1} with angle {angle}, Sollwendekreisradius {po_goal}')
            if optimizeWindingHoop:                
                
                shift, err_wk, iterations = optimizeHoopShiftForPolarOpeningX(vessel, po_goal, layerindex)
                log.info(f'{iterations} iterations. Shift is {shift} resulting in a polar opening error of {err_wk} '
                     f'as current polar opening is {vessel.getPolarOpeningR(layerindex, True)}')                
            else:
                # winding without optimization, but direct correction of shift
                vessel.setHoopLayerShift(layerindex, 0., True)
                vessel.runWindingSimulation(layerindex + 1)     
                coor = po_goal - vessel.getPolarOpeningX(layerindex, True)
                vessel.setHoopLayerShift(layerindex, coor, True)
                vessel.runWindingSimulation(layerindex + 1)     

        # Helix layer
        else:
            anzHelix = anzHelix+1
            # global arr_fric, arr_wk
            # global arr_fric, arr_wk
            # arr_fric = []
            # arr_wk = []
            po_goal = wendekreisradius
            log.info(f'apply layer {i+1} with band mid path at polar opening of {po_goal}')
            po_goal = getRadiusByShiftOnMandrel(vessel.getVesselLayer(layerindex - 1).getOuterMandrel1(), wendekreisradius, bandWidth)
            log.info(f'apply layer {i+1} with angle {angle} with band outer path at polar opening {po_goal}')
            log.info(f'radius difference is {po_goal-wendekreisradius}, {bandWidth}')
            
            # firts estimation with no frcition
            vessel.setLayerFriction(layerindex, 0., True)
            vessel.runWindingSimulation(layerindex + 1)
            log.info(f' polar opening with no friction is {vessel.getPolarOpeningR(layerindex, True)}')
            diff = vessel.getPolarOpeningR(layerindex, True)-po_goal
                        
            if optimizeWindingHelical and abs(diff) > 0.:    
                log.info(f'using optimizeFriction')    
                #friction, err_wk, iterations = optimizeFriction(vessel, wendekreisradius, layerindex, verbose=False)
                #log.info(f'{iterations} iterations. Friction is {friction} resulting in a polar opening error of {err_wk} '
                #     f'as current polar opening is {vessel.getPolarOpeningR(layerindex, True)}')                
                #po_local = vessel.getPolarOpeningR(layerindex, True)         
   
                
                if diff > 0:
                    log.info(f' current polar opening is too large, frcition musst be negative')
                    log.info(f'using optimizeFrictionGlobal_differential_evolution')
                    friction, err_wk, iterations = optimizeNegativeFrictionGlobal_differential_evolution(vessel, po_goal, layerindex, verbose=False)
                
                if diff < 0:
                    log.info(f' current polar opening is too small, frcition musst be positive')
                    log.info(f'using optimizeFrictionGlobal_differential_evolution')
                    
                    friction, err_wk, iterations = optimizeFrictionGlobal_differential_evolution(vessel, po_goal, layerindex, verbose=False)
                
                
                log.info(f'{iterations} iterations. Friction is {friction} resulting in a polar opening error of {err_wk} '
                     f'as current polar opening is {vessel.getPolarOpeningR(layerindex, True)}')
                if err_wk > 1.:
                    log.info(f'!!!!! ERROR FOR POLAR OPEING IS LARGER THAN 1mm !!!')
       


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
        outArr.append([i+1, angle, po, po*2, po_goal, abs(po-po_goal)])
        with open(windingFile, "a") as file:
            file.write('\t'.join([str(s) for s in outArr[-1]]) + '\n')

    with open(windingFile, "w") as file:
        file.write(indent([["Layer \#", "Angle", "Polar opening", "Polar opening diameter",  "Target Polar opening"]] + outArr))

    # save vessel
    vessel.saveToFile(vesselFilename)  # save vessel
    updateName(vesselFilename, tankname, ['vessel'])

    # save winding results
    windingResults = pychain.winding.VesselWindingResults()
    windingResults.buildFromVessel(vessel)
    windingResults.saveToFile(windingResultFilename)

    # #############################################################################
    # run internal calculation
    # #############################################################################

#    build shell model for internal calculation
    converter = pychain.mycrofem.VesselConverter()
    shellModel = converter.buildAxShellModell(vessel, 10)

#    run linear solver
    linerSolver = pychain.mycrofem.LinearSolver(shellModel)
    linerSolver.run(True)

#    get stresses in the fiber COS
    S11, S22, S12 = shellModel.calculateLayerStressesBottom()
#    get  x coordinates (element middle)
    xCoords = shellModel.getElementCoordsX()

    # #############################################################################
    # run ABAQUS
    # #############################################################################


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


