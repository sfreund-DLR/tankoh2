"""control a tank optimization"""

import sys
from tankoh2.design.existingdesigns import kautextDesign

#from builtins import True, False
#from builtins import

sys.path.append('C:/MikroWind/MyCrOChain_Version_0_95_4_x64/MyCrOChain_Version_0_95_4_x64/abaqus_interface_0_95_4')

import os

from tankoh2 import programDir, log, pychain
from tankoh2.service.utilities import indent, getRunDir
from tankoh2.design.designwinding.windingutils import getRadiusByShiftOnMandrel, updateName, \
    changeSimulationOptions
from tankoh2.design.designwinding.contour import getLiner, getDome, getReducedDomePoints #, getLengthContourPath
from tankoh2.design.designwinding.material import getMaterial, getComposite, readLayupData
from tankoh2.design.designwinding.optimize import optimizeFrictionGlobal_differential_evolution, optimizeHoopShiftForPolarOpeningX,\
    optimizeNegativeFrictionGlobal_differential_evolution
from tankoh2.control.control_sf import createWindingDesign
import tankoh2.design.existingdesigns
#import mymodels.myvesselAxSolid as vesselAxSolid    
#from builtins import True

def builtVesselAsBuilt(symmetricTank, servicepressure, saftyFactor, layersToWind, optimizeWindingHelical, optimizeWindingHoop, tankname, 
                           dataDir, dzyl, polarOpening, lzylinder, dpoints, defaultLayerthickness, hoopLayerThickness, helixLayerThickenss, rovingWidth, numberOfRovingsHelical, 
                           numberOfRovingsHoop, tex, rho, hoopStart, hoopRisePerBandwidth, minThicknessValue, hoopLayerCompressionStart, domeContourFilename):
    # #########################################################################################
    # SET Parameters of vessel
    # #########################################################################################


    log.info(f'built tank with polar opening of {polarOpening}')
    
    bandWidthHelical = rovingWidth * numberOfRovingsHelical
    bandWidthHoop = rovingWidth * numberOfRovingsHoop
    log.info(f'for helical winding using {numberOfRovingsHelical} rovings with {rovingWidth}mm resulting in bandwith of {bandWidthHelical}')
    log.info(f'for hoop winding using {numberOfRovingsHoop} rovings with {rovingWidth}mm resulting in bandwith of {bandWidthHoop}')    
    sectionAreaFibre = tex / (1000. * rho)
    print(sectionAreaFibre)
    log.info(f'section fibre area within roving is {sectionAreaFibre}')

    # input files
    layupDataFilename = os.path.join(dataDir, "Winding_" + tankname + ".txt")
    #materialFilename = os.path.join(dataDir, "CFRP_T700SC_LY556.json")
    materialFilename = os.path.join(dataDir, "CFRP_T700SC_LY556.json")    
    if symmetricTank == False:
        dome2ContourFilename = os.path.join(dataDir, "Dome2_contour_" + tankname + "_48mm.txt")
    # output files
    runDir = getRunDir()
    fileNameReducedDomeContour = os.path.join(runDir, f"Dome_contour_{tankname}_reduced.dcon")
    if symmetricTank == False:
        fileNameReducedDome2Contour = os.path.join(runDir, f"Dome2_contour_{tankname}_reduced.dcon")
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
    dome2 = None
    if symmetricTank == False:
        x, r = getReducedDomePoints(dome2ContourFilename,
                                dpoints, fileNameReducedDome2Contour)
        dome2 = getDome(dzyl / 2., polarOpening, pychain.winding.DOME_TYPES.ISOTENSOID,
                   x, r)
    liner = getLiner(dome, lzylinder, linerFilename, tankname, dome2=dome2)

    # ###########################################
    # Create material
    # ###########################################
    log.info(f'get material')
    material = getMaterial(materialFilename)

    

    angles, thicknesses, wendekreisradien, krempenradien = readLayupData(layupDataFilename)
    log.info(f'{angles[0:layersToWind]}')
    composite = getComposite(angles[0:layersToWind], thicknesses[0:layersToWind], hoopLayerThickness,
                             helixLayerThickenss, material, sectionAreaFibre, rovingWidth, numberOfRovingsHelical, numberOfRovingsHoop,
                             tex, designFilename, tankname)

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
            po_goal = hoopStart + lzylinder/2. - anzHoop*hoopRisePerBandwidth*bandWidthHoop
            anzHoop = anzHoop+1
            #po_goal = wendekreisradius
            log.info(f'apply layer {i+1} with angle {angle}, and hoop position {po_goal}')
            if optimizeWindingHoop:                
                
                shift, err_wk, iterations = optimizeHoopShiftForPolarOpeningX(vessel, po_goal, layerindex)
                log.info(f'{iterations} iterations. Shift is {shift} resulting in a hoop position error {err_wk} '
                     f'as current polar opening is {vessel.getPolarOpeningR(layerindex, True)}')                
            else:
                # winding without optimization, but direct correction of shift
                vessel.setHoopLayerShift(layerindex, 0., True)
                vessel.runWindingSimulation(layerindex + 1)     
                coor = po_goal - vessel.getPolarOpeningX(layerindex, True)
                vessel.setHoopLayerShift(layerindex, coor, True)
                if symmetricTank == False:
                    vessel.setHoopLayerShift(layerindex, -coor, False) # shift in opposite direction on opposite dome/mandrel
                vessel.runWindingSimulation(layerindex + 1)     

        # Helix layer
        else:
            anzHelix = anzHelix+1
            # global arr_fric, arr_wk
            # global arr_fric, arr_wk
            # arr_fric = []
            # arr_wk = []
            po_goal = max(wendekreisradius, polarOpening) # prevent bandmiddle path corssing polar opening
            log.info(f'apply layer {i+1} with band mid path at polar opening of {po_goal}')
            po = getRadiusByShiftOnMandrel(vessel.getVesselLayer(layerindex - 1).getOuterMandrel1(), wendekreisradius, bandWidthHelical)
            log.info(f'applied layer {i+1} with angle {angle} without friction with band outer path at polar opening {po}')
            log.info(f'radius difference is {po-wendekreisradius} with bandwith {bandWidthHelical}')
            
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
    
    
    # manipulate .vessel-file and run winding simulation again 
    changeSimulationOptions(vesselFilename, layersToWind, minThicknessValue, hoopLayerCompressionStart)

    # re-run winding simulation with modified simulation options
    vessel.loadFromFile(vesselFilename)
    vessel.finishWinding()
    

    # save winding results
    windingResults = pychain.winding.VesselWindingResults()
    windingResults.buildFromVessel(vessel)
    
    statistics = vessel.calculateVesselStatistics()
    #print("working pressure", statistics.burstPressure)
    #import inspect
    #print("statistics", inspect.getmembers(statistics))
    windingResults.saveToFile(windingResultFilename)

    # #############################################################################
    # run internal calculation
    # #############################################################################

#    build shell model for internal calculation
    #converter = pychain.mycrofem.VesselConverter()
    #shellModel = converter.buildAxShellModell(vessel, 10)

#    run linear solver
    #linerSolver = pychain.mycrofem.LinearSolver(shellModel)
    #linerSolver.run(True)

#    get stresses in the fiber COS
    #S11, S22, S12 = shellModel.calculateLayerStressesBottom()
#    get  x coordinates (element middle)
    #xCoords = shellModel.getElementCoordsX()

    # #############################################################################
    # run ABAQUS
    # #############################################################################


    # create model options for abaqus calculation
    #modelOptions = pychain.mycrofem.VesselFEMModelOptions()
    #modelOptions.modelName = tankname + "_Vessel"
    #modelOptions.jobName = tankname + "_Job"
    #modelOptions.windingResultsFileName = tankname
    #modelOptions.useMaterialPhi = False # false uses micromechanical estimations of fvg effect an porperties
    #modelOptions.fittingContactWinding = pychain.mycrofem.CONTACT_TYPE.PENALTY
    #modelOptions.frictionFitting = 0.3
    #modelOptions.globalMeshSize = 2.0
    #modelOptions.pressureInBar = servicepressure
    #modelOptions.saveCAE = True
    #modelOptions.buildMandrel1 = True
    #modelOptions.buildMandrel2 = False
    
    

    # write abaqus scripts
    #scriptGenerator = pychain.abaqus.AbaqusVesselScriptGenerator()
    #scriptGenerator.writeVesselAxSolidBuildScript(os.path.join(runDir, tankname + "_Build.py"), settings, modelOptions)
    #scriptGenerator.writeVesselAxSolidBuildScript(os.path.join(runDir, tankname + "_Eval.py"), settings, modelOptions)

    # create vessel model according to version 95_2 documentation 'Axis-Symmetric Vessel Model'
    
    #create vessel model
    #vesselAxSolid = mymodels.myvesselAxSolidContacts  
    #model = vesselAxSolid.MyVesselAxSolid(modelName = tankname + "_Vessel", umat = True, buildFitting = True, saveCAE = True, useMaterialPhi = False, buildLiner = True)
    #load winding results
    #model.loadData(tankname)
    #build mandrel 1
    #model.buildOnlyMandrel1(servicepressure, 1, friction = 0.3, fittingContactWinding = pychain.mycrofem.CONTACT_TYPE.PENALT)
    #mesh model
    #model.mesh(2.0)
    #export inp file
    #model.exportInp(tankname + "_Job")


#    fig = plt.figure()
 #   ax = fig.gca()
 #   ax.plot(S11[:, 0])
 #   ax.plot(S11[:, 1])
 #   ax.plot(S11[:, 2])
    # plt.show()
    
def builtVesselByOptimizedDesign(design, domeContourFilename):
    
    
    tankname = design.get('tankname')
    
    # create liner x,r data
    dpoints = 4
    runDir = getRunDir()
    if domeContourFilename == None:
        createWindingDesign(**design)
    else:
        fileNameReducedDomeContour = os.path.join(runDir, f"Dome_contour_{tankname}_reduced.dcon")
        x, r = getReducedDomePoints(domeContourFilename,
                                dpoints, fileNameReducedDomeContour)
        # start design optimization with specified design and given (x,r)-liner contour data
        createWindingDesign(**design, domeContour = (x,r), runDir=runDir)

def main():

#
#    What do you want to do?
#
# - As-Built of existing vessel    
    AsBuilt = False
    
    
    # --- Parameters for As-Built
    symmetricTank = True
    servicepressure = 700. #bar
    saftyFactor = 1.
    layersToWind = 48 #48
    
    optimizeWindingHelical = True #False
    optimizeWindingHoop = False
        
    tankname = 'NGT-BIT-2020-09-16'
    dataDir = os.path.join(programDir, 'data')
    dzyl = 400.  # mm
    polarOpening = 46./2.  # mm
    lzylinder = 500.  # mm    
    dpoints = 4  # data points for liner contour
    defaultLayerthickness = 0.125
    hoopLayerThickness = 0.125
    helixLayerThickenss = 0.129  
    
    
    rovingWidth = 3.175
    numberOfRovingsHelical = 18
    numberOfRovingsHoop = 18
    
    tex = 446  # g / km
    rho = 1.78  # g / cm^3
    
    hoopStart = 5.*rovingWidth # start position axial direction for first hoop layer
    hoopRisePerBandwidth = 1./12. # shift of hoopRisePerBandwidth*bandwidthhoop per hoop layer
    
    # Set thickness solver options
    # default minThicknessValue  = 0.01 / hoopLayerCompressionStart = 0.5   
    minThicknessValue = 0.2
    hoopLayerCompressionStart = 0.5 
    
    domeContourFilename = os.path.join(dataDir, "Dome_contour_" + tankname + ".txt")


# - Optimized Design regarding sepcific parameters
    createDesign = True
    #design = tankoh2.existingdesigns.NGTBITDesign
    design = tankoh2.design.existingdesigns.NGTBITDesign_small
    tankname = design.get('tankname')    
    dataDir = os.path.join(programDir, 'data')
    domeContourFilename = os.path.join(dataDir, "Dome_contour_" + tankname + ".txt")
    #domeContourFilename = None    
    


    if AsBuilt: 
        builtVesselAsBuilt(symmetricTank, servicepressure, saftyFactor, layersToWind, optimizeWindingHelical, optimizeWindingHoop, tankname, 
                           dataDir, dzyl, polarOpening, lzylinder, dpoints, defaultLayerthickness, hoopLayerThickness, helixLayerThickenss, rovingWidth, numberOfRovingsHelical, 
                           numberOfRovingsHoop, tex, rho, hoopStart, hoopRisePerBandwidth, minThicknessValue, hoopLayerCompressionStart, domeContourFilename)        
    
    if createDesign:
        builtVesselByOptimizedDesign(design, domeContourFilename)
        

    log.info('FINISHED')


if __name__ == '__main__':
    main()


